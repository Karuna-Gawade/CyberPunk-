"""
Pure validation rules for monthly salary slip payroll arithmetic.
Checks:
1. Gross pay minus total deductions equals net pay: Gross - Deductions == Net Pay
2. Earnings components sum to Gross pay: Basic + HRA + Allowances == Gross
3. PF contribution ~ 12% of basic (reported as Observation only, due to statutory wage ceilings)
"""

from typing import Dict, List, Optional
from backend.app.models.contracts import (
    EvidenceItem,
    FindingStrength,
    FindingTier,
    RuleResult,
    RuleStatus,
    BBox,
)

TOLERANCE_INR = 2.0  # Allow up to 2 INR rounding discrepancy


def validate_salary_arithmetic(
    fields_dict: Dict[str, any],
    field_records_map: Optional[Dict[str, any]] = None,
    doc_id: str = "DOC-SLIP",
    page: int = 1,
) -> List[RuleResult]:
    """
    Validates arithmetic integrity of salary slip fields.
    Returns list of RuleResult objects.
    """
    results: List[RuleResult] = []
    field_records_map = field_records_map or {}

    gross = fields_dict.get("gross")
    total_deductions = fields_dict.get("total_deductions")
    net_pay = fields_dict.get("net_pay")
    basic = fields_dict.get("basic")
    hra = fields_dict.get("hra")
    allowances = fields_dict.get("allowances")
    pf = fields_dict.get("pf")

    # Helper to get field ID and bbox
    def get_evidence(field_name: str) -> EvidenceItem:
        rec = field_records_map.get(field_name)
        f_id = rec.field_id if rec else f"F-{doc_id}-{field_name}"
        bbox = rec.bbox if rec else [0, 0, 0, 0]
        p = rec.page if rec else page
        return EvidenceItem(doc_id=doc_id, field_id=f_id, page=p, bbox=bbox, label=field_name)

    # 1. Gross - Deductions == Net Pay
    if gross is not None and total_deductions is not None and net_pay is not None:
        expected_net = gross - total_deductions
        diff = abs(expected_net - net_pay)
        used_ids = [get_evidence("gross").field_id, get_evidence("total_deductions").field_id, get_evidence("net_pay").field_id]

        if diff > TOLERANCE_INR:
            results.append(
                RuleResult(
                    rule_id="salary_net_pay_calc",
                    result=RuleStatus.FAIL,
                    field_ids_used=used_ids,
                    detail=f"Payroll arithmetic contradiction: Gross ({gross:,.2f}) minus Deductions ({total_deductions:,.2f}) equals {expected_net:,.2f}, but declared Net Pay is {net_pay:,.2f} (discrepancy of {diff:,.2f} INR).",
                    tier=FindingTier.INCONSISTENCY,
                    strength=FindingStrength.STRONG,
                    title="Salary slip net pay arithmetic mismatch",
                    evidence=[get_evidence("net_pay"), get_evidence("gross"), get_evidence("total_deductions")],
                    signals=["salary_arithmetic_mismatch"],
                )
            )
        else:
            results.append(
                RuleResult(
                    rule_id="salary_net_pay_calc",
                    result=RuleStatus.PASS,
                    field_ids_used=used_ids,
                    detail="Gross pay minus deductions equals declared net pay.",
                )
            )

    # 2. Earnings components sum to Gross: Basic + HRA + Allowances == Gross
    if gross is not None and basic is not None and hra is not None and allowances is not None:
        component_sum = basic + hra + allowances
        diff = abs(component_sum - gross)
        used_ids = [get_evidence("basic").field_id, get_evidence("hra").field_id, get_evidence("allowances").field_id, get_evidence("gross").field_id]

        if diff > TOLERANCE_INR:
            results.append(
                RuleResult(
                    rule_id="salary_components_sum",
                    result=RuleStatus.FAIL,
                    field_ids_used=used_ids,
                    detail=f"Earnings components sum: Basic ({basic:,.2f}) + HRA ({hra:,.2f}) + Allowances ({allowances:,.2f}) = {component_sum:,.2f}, which does not match declared Gross of {gross:,.2f}.",
                    tier=FindingTier.INCONSISTENCY,
                    strength=FindingStrength.MODERATE,
                    title="Earnings components sum differs from gross pay",
                    evidence=[get_evidence("gross"), get_evidence("basic")],
                    signals=["salary_components_mismatch"],
                )
            )

    # 3. PF ~ 12% of basic (Observation only)
    if basic is not None and pf is not None:
        expected_pf = basic * 0.12
        pf_diff = abs(expected_pf - pf)
        used_ids = [get_evidence("basic").field_id, get_evidence("pf").field_id]

        # Statutory wage ceiling can cap PF at 1800 INR (12% of 15000), so we only report as Observation if discrepancy is notable
        if pf_diff > 50.0 and abs(pf - 1800.0) > 5.0:
            results.append(
                RuleResult(
                    rule_id="salary_pf_ratio",
                    result=RuleStatus.FAIL,
                    field_ids_used=used_ids,
                    detail=f"Provident Fund contribution ({pf:,.2f}) deviates from standard 12% of basic salary ({expected_pf:,.2f}). Note: statutory wage ceilings may apply.",
                    tier=FindingTier.OBSERVATION,
                    strength=FindingStrength.WEAK,
                    title="PF deduction differs from standard 12% of basic",
                    evidence=[get_evidence("pf"), get_evidence("basic")],
                    signals=["pf_ratio_variance"],
                )
            )

    return results
