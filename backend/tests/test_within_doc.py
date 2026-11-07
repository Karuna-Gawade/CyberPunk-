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


def test_within_doc_loan_amount_invalid():
    fields = [
        ExtractedField(field_id="F1", doc_id="DOC_LOAN", name="name", value="Rajesh Sharma", raw_text="Rajesh Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0,0,10,10]),
        ExtractedField(field_id="F2", doc_id="DOC_LOAN", name="declared_monthly_income", value=85000.0, raw_text="85000", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0,0,10,10]),
        ExtractedField(field_id="F3", doc_id="DOC_LOAN", name="loan_amount", value=0.0, raw_text="0", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0,0,10,10]),
    ]
    results = validate_within_document_structure("DOC_LOAN", DocumentType.LOAN_APPLICATION, fields)
    rule = next((r for r in results if r.rule_id == "loan_amount_invalid"), None)
    assert rule is not None
    assert rule.result == RuleStatus.FAIL
    assert rule.tier == FindingTier.OBSERVATION


def test_within_doc_payment_amount_invalid():
    fields = [
        ExtractedField(field_id="F1", doc_id="DOC_PAY", name="name", value="Rajesh Sharma", raw_text="Rajesh Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0,0,10,10]),
        ExtractedField(field_id="F2", doc_id="DOC_PAY", name="beneficiary_name", value="Priya Sharma", raw_text="Priya Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0,0,10,10]),
        ExtractedField(field_id="F3", doc_id="DOC_PAY", name="amount", value=-500.0, raw_text="-500", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0,0,10,10]),
    ]
    results = validate_within_document_structure("DOC_PAY", DocumentType.PAYMENT_INSTRUCTION, fields)
    rule = next((r for r in results if r.rule_id == "payment_amount_invalid"), None)
    assert rule is not None
    assert rule.result == RuleStatus.FAIL
    assert rule.tier == FindingTier.OBSERVATION
