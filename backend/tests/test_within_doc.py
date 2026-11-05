"""
Unit tests for within-document structure, missing mandatory fields, and duplication.
"""

from backend.app.models.contracts import DocumentType, ExtractedField, FieldSource, FindingTier, RuleStatus
from backend.app.services.rules.within_doc import validate_within_document_structure


def test_within_doc_missing_mandatory_field():
    # Aadhaar with name and dob, but missing aadhaar_number
    fields = [
        ExtractedField(field_id="F1", doc_id="DOC1", name="name", value="Rajesh Sharma", raw_text="Rajesh", confidence=0.9, source=FieldSource.TEXT_LAYER, page=1, bbox=[0,0,10,10]),
        ExtractedField(field_id="F2", doc_id="DOC1", name="dob", value="14/05/1988", raw_text="14/05/1988", confidence=0.9, source=FieldSource.TEXT_LAYER, page=1, bbox=[0,0,10,10]),
    ]
    results = validate_within_document_structure("DOC1", DocumentType.AADHAAR, fields)
    missing_rule = next((r for r in results if r.rule_id == "missing_mandatory_field"), None)
    assert missing_rule is not None
    assert missing_rule.result == RuleStatus.FAIL
    assert missing_rule.tier == FindingTier.OBSERVATION
    assert "aadhaar_number" in missing_rule.detail


def test_within_doc_duplicate_conflicting_fields():
    fields = [
        ExtractedField(field_id="F1", doc_id="DOC1", name="net_pay", value=80000.0, raw_text="80000", confidence=0.9, source=FieldSource.TEXT_LAYER, page=1, bbox=[0,0,10,10]),
        ExtractedField(field_id="F2", doc_id="DOC1", name="net_pay", value=65000.0, raw_text="65000", confidence=0.9, source=FieldSource.TEXT_LAYER, page=1, bbox=[0,0,10,10]),
    ]
    results = validate_within_document_structure("DOC1", DocumentType.SALARY_SLIP, fields)
    dup_rule = next((r for r in results if r.rule_id == "duplicate_conflicting_field"), None)
    assert dup_rule is not None
    assert dup_rule.result == RuleStatus.FAIL
    assert dup_rule.tier == FindingTier.INCONSISTENCY
