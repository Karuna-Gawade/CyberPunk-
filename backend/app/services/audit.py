"""
Audit trail service with cryptographic SHA-256 hash chaining.
Aligned with ISO/IEC 27037 digital evidence handling principles.
"""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from backend.app.models.contracts import AuditEvent


class AuditService:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    investigation_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    details TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    entry_hash TEXT NOT NULL
                )
            """)
            conn.commit()

    @staticmethod
    def canonical_json(data: Dict[str, Any]) -> str:
        """Produces canonical JSON: sorted keys, no whitespace."""
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def get_latest_hash(self, investigation_id: str) -> str:
        """Returns the entry_hash of the latest record for an investigation, or 64 zeros if empty."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT entry_hash FROM audit_log WHERE investigation_id = ? ORDER BY seq DESC LIMIT 1",
                (investigation_id,),
            )
            row = cursor.fetchone()
            if row:
                return row[0]
        return "0" * 64

    def log_event(
        self,
        investigation_id: str,
        actor: str,
        action: str,
        object_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Appends a new event to the audit trail with SHA-256 hash chaining."""
        details = details or {}
        now_iso = datetime.now(timezone.utc).isoformat()
        prev_hash = self.get_latest_hash(investigation_id)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Get next seq
            cursor.execute("SELECT MAX(seq) FROM audit_log")
            max_seq = cursor.fetchone()[0] or 0
            seq = max_seq + 1

            entry_dict = {
                "seq": seq,
                "timestamp": now_iso,
                "investigation_id": investigation_id,
                "actor": actor,
                "action": action,
                "object_id": object_id,
                "details": details,
                "prev_hash": prev_hash,
            }
            canonical_str = self.canonical_json(entry_dict)
            entry_hash = hashlib.sha256((prev_hash + canonical_str).encode("utf-8")).hexdigest()

            cursor.execute(
                """
                INSERT INTO audit_log (seq, timestamp, investigation_id, actor, action, object_id, details, prev_hash, entry_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    seq,
                    now_iso,
                    investigation_id,
                    actor,
                    action,
                    object_id,
                    json.dumps(details),
                    prev_hash,
                    entry_hash,
                ),
            )
            conn.commit()

            return AuditEvent(
                seq=seq,
                timestamp=now_iso,
                investigation_id=investigation_id,
                actor=actor,
                action=action,
                object_id=object_id,
                details=details,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )

    def get_events(self, investigation_id: str) -> List[AuditEvent]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT seq, timestamp, investigation_id, actor, action, object_id, details, prev_hash, entry_hash FROM audit_log WHERE investigation_id = ? ORDER BY seq ASC",
                (investigation_id,),
            )
            rows = cursor.fetchall()
            return [
                AuditEvent(
                    seq=row[0],
                    timestamp=row[1],
                    investigation_id=row[2],
                    actor=row[3],
                    action=row[4],
                    object_id=row[5],
                    details=json.loads(row[6]),
                    prev_hash=row[7],
                    entry_hash=row[8],
                )
                for row in rows
            ]

    def verify_chain(self, investigation_id: str) -> Tuple[bool, Optional[int]]:
        """
        Verifies the SHA-256 chain integrity for an investigation.
        Returns (is_valid, broken_seq_number).
        """
        events = self.get_events(investigation_id)
        if not events:
            return True, None

        expected_prev = "0" * 64
        for event in events:
            if event.prev_hash != expected_prev:
                return False, event.seq

            entry_dict = {
                "seq": event.seq,
                "timestamp": event.timestamp,
                "investigation_id": event.investigation_id,
                "actor": event.actor,
                "action": event.action,
                "object_id": event.object_id,
                "details": event.details,
                "prev_hash": event.prev_hash,
            }
            canonical_str = self.canonical_json(entry_dict)
            computed_hash = hashlib.sha256((event.prev_hash + canonical_str).encode("utf-8")).hexdigest()

            if computed_hash != event.entry_hash:
                return False, event.seq

            expected_prev = event.entry_hash

        return True, None
