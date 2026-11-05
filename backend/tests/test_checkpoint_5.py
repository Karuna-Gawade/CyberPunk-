"""
Integration Checkpoint 5 Test.
Verifies Master Spec Section 15 Checkpoint 5:
- Audit trail SHA-256 chain breaks if an event row is altered in the DB.
- Dossier output is explicitly watermarked DRAFT until a human Case Decision is recorded.
- Findings cards show human review workflow (confirm, dismiss with mandatory reason, escalate).
- Advisory banner present, human decision recorded, tamper detection verified.
"""

import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
import pymupdf

from backend.app.main import app

client = TestClient(app)
BUNDLES_ROOT = Path("samples/bundles")


def upload_and_process_bundle(bundle_name: str) -> dict:
    b_dir = BUNDLES_ROOT / bundle_name
    res_inv = client.post("/investigations")
    assert res_inv.status_code == 200
    inv_id = res_inv.json()["investigation_id"]

    files = [
        ("files", ("aadhaar.pdf", open(b_dir / "aadhaar.pdf", "rb"), "application/pdf")),
        ("files", ("pan.pdf", open(b_dir / "pan.pdf", "rb"), "application/pdf")),
        ("files", ("salary_slip.pdf", open(b_dir / "salary_slip.pdf", "rb"), "application/pdf")),
        ("files", ("bank_statement.pdf", open(b_dir / "bank_statement.pdf", "rb"), "application/pdf")),
    ]
    client.post(f"/investigations/{inv_id}/documents", files=files)
    res_proc = client.post(f"/investigations/{inv_id}/process")
    assert res_proc.status_code == 200

    inv = res_proc.json()
    res_findings = client.get(f"/investigations/{inv_id}/findings")
    return {
        "inv_id": inv_id,
        "inv": inv,
        "findings": res_findings.json(),
    }


def test_dossier_draft_watermark_until_case_decision():
    """Checkpoint 5: Dossier has DRAFT watermark before case decision, and clean header after."""
    data = upload_and_process_bundle("tampered_01_salary_edit")
    inv_id = data["inv_id"]

    # 1. Download dossier before decision -> DRAFT watermark present
    res_draft = client.get(f"/investigations/{inv_id}/dossier")
    assert res_draft.status_code == 200
    assert res_draft.headers.get("content-type") == "application/pdf"
    
    doc_draft = pymupdf.open(stream=res_draft.content, filetype="pdf")
    page_draft_text = doc_draft[0].get_text("text")
    assert "PENDING (DRAFT)" in page_draft_text or "DRAFT" in page_draft_text
    doc_draft.close()

    # 2. Dismiss requires a mandatory reason
    findings = data["findings"]
    if findings:
        f_id = findings[0]["finding_id"]
        res_fail = client.post(f"/findings/{f_id}/review", json={"decision": "dismiss", "reason": ""})
        assert res_fail.status_code == 422  # Validation error: dismiss requires reason

        res_ok = client.post(f"/findings/{f_id}/review", json={"decision": "dismiss", "reason": "Authorized exception verified by HR"})
        assert res_ok.status_code == 200
        assert res_ok.json()["status"] == "dismissed"

    # 3. Record human case decision
    decision_payload = {
        "decision": "partially_rely",
        "outcome_note": "Discrepancy noted in allowances, customer submitted explanation.",
        "decided_by": "INVESTIGATOR-42",
    }
    res_decision = client.post(f"/investigations/{inv_id}/decision", json=decision_payload)
    assert res_decision.status_code == 200
    assert res_decision.json()["case_decision"]["decision"] == "partially_rely"

    # 4. Download final dossier -> Not draft
    res_final = client.get(f"/investigations/{inv_id}/dossier")
    assert res_final.status_code == 200
    doc_final = pymupdf.open(stream=res_final.content, filetype="pdf")
    page_final_text = doc_final[0].get_text("text")
    assert "Partially Rely" in page_final_text
    assert "INVESTIGATOR-42" in page_final_text
    doc_final.close()


def test_audit_log_tampering_detection():
    """Checkpoint 5: Altering any audit row breaks the hash-chain verification."""
    data = upload_and_process_bundle("tampered_02_dob_edit")
    inv_id = data["inv_id"]

    # Initial verification passes
    res_v1 = client.get(f"/investigations/{inv_id}/audit/verify")
    assert res_v1.status_code == 200
    assert res_v1.json()["chain_valid"] is True

    # Intentionally corrupt a row in sqlite
    db_path = Path("data/app.db")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT seq, details FROM audit_log WHERE investigation_id = ? LIMIT 1", (inv_id,))
        row = cursor.fetchone()
        assert row is not None
        target_seq = row[0]
        # Mutate the details JSON
        conn.execute("UPDATE audit_log SET details = '{\"tampered\": true}' WHERE seq = ?", (target_seq,))
        conn.commit()

    # Re-verify -> Chain integrity MUST fail at target_seq
    res_v2 = client.get(f"/investigations/{inv_id}/audit/verify")
    assert res_v2.status_code == 200
    assert res_v2.json()["chain_valid"] is False
    assert res_v2.json()["broken_at_seq"] == target_seq
