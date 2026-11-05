import pytest
from backend.app.models.contracts import (
    DocumentRecord,
    DocumentType,
    DocumentStatus,
    ExtractedField,
    FieldSource,
    Finding,
    FindingTier,
    FindingCategory,
    FindingStrength,
    FindingStatus,
    EvidenceItem,
    AuditEvent,
    Investigation,
    ReviewPriority,
    CaseDecision,
    CaseDecisionType,
    RuleResult,
    RuleStatus,
)


def test_extracted_field_serialization():
    field = ExtractedField(
        field_id="F-0012",
        doc_id="DOC-003",
        name="net_pay",
        value=80000,
        raw_text="80,000.00",
        confidence=0.91,
        source=FieldSource.OCR,
        page=1,
        bbox=[412, 530, 498, 552],
    )
    data = field.model_dump()
    assert data["field_id"] == "F-0012"
    assert data["value"] == 80000
    assert data["confidence"] == 0.91
    assert data["bbox"] == [412, 530, 498, 552]


def test_finding_spec_schema_conformance():
    """Validates the exact example from Section 6 of the Master Spec."""
    sample_finding = {
        "finding_id": "ANM-001",
        "tier": "inconsistency",
        "category": "cross_document",
        "rule_id": "salary_credit_match",
        "title": "Salary slip net pay differs from bank credits",
        "evidence": [
            {"doc_id": "DOC-003", "field_id": "F-0012", "page": 1, "bbox": [412, 530, 498, 552]},
            {"doc_id": "DOC-004", "field_id": "F-0107", "page": 2, "bbox": [60, 310, 540, 330]}
        ],
        "signals": ["salary_credit_match"],
        "strength": "strong",
        "confidence": 0.88,
        "status": "requires_investigation",
        "explanation": "Salary slip net pay is 80,000.00 but bank credited 65,000.00.",
        "reviewer": {"decision": None, "reason": None, "by": None, "at": None}
    }
    finding = Finding.model_validate(sample_finding)
    assert finding.tier == FindingTier.INCONSISTENCY
    assert len(finding.evidence) == 2
    assert finding.status == FindingStatus.REQUIRES_INVESTIGATION


def test_audit_event_spec_conformance():
    """Validates the AuditEvent contract from Section 6."""
    event_data = {
        "seq": 42,
        "timestamp": "2026-11-05T10:04:11Z",
        "investigation_id": "INV-001",
        "actor": "system",
        "action": "finding_created",
        "object_id": "ANM-001",
        "details": {},
        "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000",
        "entry_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0"
    }
    audit = AuditEvent.model_validate(event_data)
    assert audit.seq == 42
    assert audit.action == "finding_created"


def test_case_decision_contract():
    decision = CaseDecision(
        decision=CaseDecisionType.PARTIALLY_RELY,
        outcome_note="Relying on bank ledger continuity break, disregarding address variance.",
        decided_by="INV-OFFICER-44",
        decided_at="2026-11-05T17:00:00Z",
        findings_reviewed=4
    )
    assert decision.decision == CaseDecisionType.PARTIALLY_RELY
