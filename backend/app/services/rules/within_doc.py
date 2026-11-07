"""
Within-document structural layout and completeness validation rules.
Checks:
1. Missing mandatory domain fields per DocumentType
2. Duplicated or conflicting field definitions within the same document
3. Misplaced fields (e.g. header fields located below tables or outside expected bounds)
"""

from typing import Dict, List, Set
from backend.app.models.contracts import (
    DocumentType,
    ExtractedField,
    FindingStrength,
    FindingTier,
    RuleResult,
    RuleStatus,
    EvidenceItem,
)

# Mandatory fields per document type
MANDATORY_FIELDS = {
    DocumentType.AADHAAR: ["aadhaar_number", "name", "dob"],
    DocumentType.PAN: ["pan_number", "name", "dob"],
    DocumentType.SALARY_SLIP: ["employee_name", "net_pay", "gross"],
    DocumentType.BANK_STATEMENT: ["account_holder", "account_number", "period"],
    DocumentType.LOAN_APPLICATION: ["name", "declared_monthly_income", "loan_amount"],
    DocumentType.DECLARATION_15G: ["name", "pan_number", "estimated_annual_income"],
    DocumentType.PAYMENT_INSTRUCTION: ["name", "amount", "beneficiary_name"],
}


def validate_within_document_structure(
    doc_id: str,
    doc_type: DocumentType,
    fields: List[ExtractedField],
) -> List[RuleResult]:
    """
    Validates completeness, duplication, and placement within a single document.
    """
    results: List[RuleResult] = []
    if doc_type == DocumentType.UNSUPPORTED:
        return results

    field_names = [f.name for f in fields]
    field_name_set = set(field_names)

    # 1. Missing mandatory fields check
    mandatory = MANDATORY_FIELDS.get(doc_type, [])
    missing = [m for m in mandatory if m not in field_name_set]

    if missing:
        results.append(
            RuleResult(
                rule_id="missing_mandatory_field",
                result=RuleStatus.FAIL,
                field_ids_used=[],
                detail=f"Document is missing mandatory domain field(s): {', '.join(missing)}.",
                tier=FindingTier.OBSERVATION,
                strength=FindingStrength.MODERATE,
                title=f"Missing mandatory field ({', '.join(missing)}) in {doc_type.value}",
                evidence=[EvidenceItem(doc_id=doc_id, page=1, bbox=[0, 0, 100, 100])],
                signals=["missing_field"],
            )
        )

    # 2. Duplicate field check (e.g., multiple different values for same field name)
    seen_names: Dict[str, List[ExtractedField]] = {}
    for f in fields:
        seen_names.setdefault(f.name, []).append(f)

    for name, occurrences in seen_names.items():
        if len(occurrences) > 1 and name not in ("transactions", "salary_credits"):
            # Check if values conflict
            unique_vals = {str(o.value) for o in occurrences}
            if len(unique_vals) > 1:
                results.append(
                    RuleResult(
                        rule_id="duplicate_conflicting_field",
                        result=RuleStatus.FAIL,
                        field_ids_used=[o.field_id for o in occurrences],
                        detail=f"Field '{name}' appears multiple times with conflicting values: {', '.join(unique_vals)}.",
                        tier=FindingTier.INCONSISTENCY,
                        strength=FindingStrength.STRONG,
                        title=f"Conflicting duplicate field '{name}' detected",
                        evidence=[
                            EvidenceItem(doc_id=doc_id, field_id=o.field_id, page=o.page, bbox=o.bbox)
                            for o in occurrences
                        ],
                        signals=["duplicate_field_conflict"],
                    )
                )

    # 3. Misplaced field checks (e.g., header fields located below coordinate y=700 on standard 150 DPI A4 ~ 1240px)
    for f in fields:
        if f.name in ("aadhaar_number", "pan_number") and f.bbox[1] > 900:
            results.append(
                RuleResult(
                    rule_id="misplaced_document_field",
                    result=RuleStatus.FAIL,
                    field_ids_used=[f.field_id],
                    detail=f"Field '{f.name}' is abnormally positioned near bottom of page (y={f.bbox[1]}).",
                    tier=FindingTier.OBSERVATION,
                    strength=FindingStrength.WEAK,
                    title=f"Misplaced layout position for '{f.name}'",
                    evidence=[EvidenceItem(doc_id=doc_id, field_id=f.field_id, page=f.page, bbox=f.bbox)],
                    signals=["misplaced_field_layout"],
                )
            )

    # 4. Numeric validity checks for loan and payment instructions
    if doc_type == DocumentType.LOAN_APPLICATION:
        la_field = next((f for f in fields if f.name == "loan_amount"), None)
        if la_field and (la_field.value is None or float(la_field.value or 0) <= 0):
            results.append(
                RuleResult(
                    rule_id="loan_amount_invalid",
                    result=RuleStatus.FAIL,
                    field_ids_used=[la_field.field_id],
                    detail=f"Loan amount must be a positive non-zero value, but found '{la_field.value}'.",
                    tier=FindingTier.OBSERVATION,
                    strength=FindingStrength.WEAK,
                    title="Loan amount missing or non-positive",
                    evidence=[EvidenceItem(doc_id=doc_id, field_id=la_field.field_id, page=la_field.page, bbox=la_field.bbox)],
                    signals=["invalid_loan_amount"],
                )
            )

    if doc_type == DocumentType.PAYMENT_INSTRUCTION:
        amt_field = next((f for f in fields if f.name == "amount"), None)
        if amt_field and (amt_field.value is None or float(amt_field.value or 0) <= 0):
            results.append(
                RuleResult(
                    rule_id="payment_amount_invalid",
                    result=RuleStatus.FAIL,
                    field_ids_used=[amt_field.field_id],
                    detail=f"Payment transfer amount must be a positive non-zero value, but found '{amt_field.value}'.",
                    tier=FindingTier.OBSERVATION,
                    strength=FindingStrength.WEAK,
                    title="Payment instruction amount missing or non-positive",
                    evidence=[EvidenceItem(doc_id=doc_id, field_id=amt_field.field_id, page=amt_field.page, bbox=amt_field.bbox)],
                    signals=["invalid_payment_amount"],
                )
            )

    return results
