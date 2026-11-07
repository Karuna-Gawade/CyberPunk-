"""
Unit tests for new cross-document correlation rules:
- Loan declared income vs salary slip gross
- Form 15G PAN vs PAN card
- Form 15G estimated annual income vs salary slip annualized gross
- Payment instruction account number vs bank statement
- Payment instruction debit amount vs bank statement transactions
"""

from backend.app.models.contracts import (
    DocumentRecord,
    DocumentStatus,
    DocumentType,
    ExtractedField,
    FieldSource,
    FindingTier,
)
from backend.app.services.correlation.cross_doc import CrossDocEngine


def _make_doc(doc_id: str, doc_type: DocumentType, fields: list) -> DocumentRecord:
    return DocumentRecord(
        doc_id=doc_id,
        filename=f"{doc_id}.pdf",
        sha256="0" * 64,
        type=doc_type,
        status=DocumentStatus.PROCESSED,
        pages=1,
        fields=fields,
    )


def test_loan_income_vs_salary_pass_and_fail():
    engine = CrossDocEngine()

    # Case 1: Loan declared income matches salary slip gross within tolerance
    loan_doc = _make_doc(
        "DOC_LOAN",
        DocumentType.LOAN_APPLICATION,
        [
            ExtractedField(field_id="L1", doc_id="DOC_LOAN", name="name", value="Rajesh Sharma", raw_text="Rajesh Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="L2", doc_id="DOC_LOAN", name="declared_monthly_income", value=85000.0, raw_text="85000", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
        ],
    )
    slip_doc = _make_doc(
        "DOC_SLIP",
        DocumentType.SALARY_SLIP,
        [
            ExtractedField(field_id="S1", doc_id="DOC_SLIP", name="employee_name", value="Rajesh Sharma", raw_text="Rajesh Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="S2", doc_id="DOC_SLIP", name="gross", value=85200.0, raw_text="85200", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
        ],
    )

    findings, matrix = engine.correlate_investigation("INV1", [loan_doc, slip_doc])
    assert not any(f.rule_id == "loan_income_vs_salary" for f in findings)

    # Case 2: Inflated declared income
    loan_doc_inflated = _make_doc(
        "DOC_LOAN",
        DocumentType.LOAN_APPLICATION,
        [
            ExtractedField(field_id="L1", doc_id="DOC_LOAN", name="name", value="Rajesh Sharma", raw_text="Rajesh Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="L2", doc_id="DOC_LOAN", name="declared_monthly_income", value=185000.0, raw_text="185000", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
        ],
    )
    findings, matrix = engine.correlate_investigation("INV1", [loan_doc_inflated, slip_doc])
    finding = next((f for f in findings if f.rule_id == "loan_income_vs_salary"), None)
    assert finding is not None
    assert finding.tier == FindingTier.INCONSISTENCY
    assert len(finding.evidence) == 2


def test_form_15g_checks_pan_and_income():
    engine = CrossDocEngine()

    pan_doc = _make_doc(
        "DOC_PAN",
        DocumentType.PAN,
        [
            ExtractedField(field_id="P1", doc_id="DOC_PAN", name="name", value="Rajesh Sharma", raw_text="Rajesh Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="P2", doc_id="DOC_PAN", name="pan_number", value="BCDPS1234E", raw_text="BCDPS1234E", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
        ],
    )
    slip_doc = _make_doc(
        "DOC_SLIP",
        DocumentType.SALARY_SLIP,
        [
            ExtractedField(field_id="S1", doc_id="DOC_SLIP", name="employee_name", value="Rajesh Sharma", raw_text="Rajesh Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="S2", doc_id="DOC_SLIP", name="gross", value=100000.0, raw_text="100000", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
        ],
    )

    # 15G with matching PAN and reasonable income
    g15_doc_valid = _make_doc(
        "DOC_15G",
        DocumentType.DECLARATION_15G,
        [
            ExtractedField(field_id="G1", doc_id="DOC_15G", name="name", value="Rajesh Sharma", raw_text="Rajesh Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="G2", doc_id="DOC_15G", name="pan_number", value="BCDPS1234E", raw_text="BCDPS1234E", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="G3", doc_id="DOC_15G", name="estimated_annual_income", value=1200000.0, raw_text="1200000", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
        ],
    )
    findings, _ = engine.correlate_investigation("INV1", [pan_doc, slip_doc, g15_doc_valid])
    assert not any(f.rule_id in ("g15_pan_mismatch", "g15_income_vs_salary") for f in findings)

    # 15G with mismatched PAN and suppressed income
    g15_doc_invalid = _make_doc(
        "DOC_15G",
        DocumentType.DECLARATION_15G,
        [
            ExtractedField(field_id="G1", doc_id="DOC_15G", name="name", value="Rajesh Sharma", raw_text="Rajesh Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="G2", doc_id="DOC_15G", name="pan_number", value="XYZPS9999K", raw_text="XYZPS9999K", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="G3", doc_id="DOC_15G", name="estimated_annual_income", value=200000.0, raw_text="200000", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
        ],
    )
    findings, _ = engine.correlate_investigation("INV1", [pan_doc, slip_doc, g15_doc_invalid])
    pan_finding = next((f for f in findings if f.rule_id == "g15_pan_mismatch"), None)
    inc_finding = next((f for f in findings if f.rule_id == "g15_income_vs_salary"), None)
    assert pan_finding is not None
    assert inc_finding is not None
    assert pan_finding.tier == FindingTier.INCONSISTENCY
    assert inc_finding.tier == FindingTier.INCONSISTENCY


def test_payment_instruction_checks_account_and_debit():
    engine = CrossDocEngine()

    bank_doc = _make_doc(
        "DOC_BANK",
        DocumentType.BANK_STATEMENT,
        [
            ExtractedField(field_id="B1", doc_id="DOC_BANK", name="account_holder", value="Rajesh Sharma", raw_text="Rajesh Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="B2", doc_id="DOC_BANK", name="account_number", value="912010045678912", raw_text="912010045678912", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(
                field_id="B3",
                doc_id="DOC_BANK",
                name="transactions",
                value=[
                    {"date": "05/10/2026", "description": "ATM WDL", "debit": 5000.0, "credit": 0.0, "balance": 95000.0},
                    {"date": "12/10/2026", "description": "NEFT TXN", "debit": 50000.0, "credit": 0.0, "balance": 45000.0},
                ],
                raw_text="tx",
                confidence=0.95,
                source=FieldSource.TEXT_LAYER,
                page=1,
                bbox=[0, 0, 10, 10],
            ),
        ],
    )

    # Valid matching payment instruction
    pmt_valid = _make_doc(
        "DOC_PMT",
        DocumentType.PAYMENT_INSTRUCTION,
        [
            ExtractedField(field_id="P1", doc_id="DOC_PMT", name="name", value="Rajesh Sharma", raw_text="Rajesh Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="P2", doc_id="DOC_PMT", name="account_number", value="912010045678912", raw_text="912010045678912", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="P3", doc_id="DOC_PMT", name="amount", value=50000.0, raw_text="50000", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
        ],
    )
    findings, _ = engine.correlate_investigation("INV1", [bank_doc, pmt_valid])
    assert not any(f.rule_id in ("payment_account_mismatch", "payment_amount_not_in_bank") for f in findings)

    # Payment instruction with wrong account and unrecorded debit amount
    pmt_invalid = _make_doc(
        "DOC_PMT",
        DocumentType.PAYMENT_INSTRUCTION,
        [
            ExtractedField(field_id="P1", doc_id="DOC_PMT", name="name", value="Rajesh Sharma", raw_text="Rajesh Sharma", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="P2", doc_id="DOC_PMT", name="account_number", value="111122223333444", raw_text="111122223333444", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
            ExtractedField(field_id="P3", doc_id="DOC_PMT", name="amount", value=75000.0, raw_text="75000", confidence=0.95, source=FieldSource.TEXT_LAYER, page=1, bbox=[0, 0, 10, 10]),
        ],
    )
    findings, _ = engine.correlate_investigation("INV1", [bank_doc, pmt_invalid])
    acc_finding = next((f for f in findings if f.rule_id == "payment_account_mismatch"), None)
    amt_finding = next((f for f in findings if f.rule_id == "payment_amount_not_in_bank"), None)
    assert acc_finding is not None
    assert amt_finding is not None
