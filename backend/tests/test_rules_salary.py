"""
Unit tests for salary slip payroll arithmetic validation.
"""

from backend.app.models.contracts import FindingTier, RuleStatus
from backend.app.services.rules.salary import validate_salary_arithmetic


def test_salary_arithmetic_valid():
    fields = {
        "basic": 50000.0,
        "hra": 20000.0,
        "allowances": 15000.0,
        "gross": 85000.0,
        "total_deductions": 6200.0,
        "net_pay": 78800.0,
        "pf": 6000.0,
    }
    results = validate_salary_arithmetic(fields)
    assert len(results) >= 1
    # Check net pay calc passed
    net_rule = next(r for r in results if r.rule_id == "salary_net_pay_calc")
    assert net_rule.result == RuleStatus.PASS


def test_salary_arithmetic_net_pay_discrepancy():
    fields = {
        "gross": 85000.0,
        "total_deductions": 6200.0,
        "net_pay": 90000.0,  # Contradiction: 85000 - 6200 = 78800, not 90000
    }
    results = validate_salary_arithmetic(fields)
    net_rule = next(r for r in results if r.rule_id == "salary_net_pay_calc")
    assert net_rule.result == RuleStatus.FAIL
    assert net_rule.tier == FindingTier.INCONSISTENCY
    assert "discrepancy of 11,200.00 INR" in net_rule.detail


def test_salary_arithmetic_components_mismatch():
    fields = {
        "basic": 40000.0,
        "hra": 10000.0,
        "allowances": 10000.0,
        "gross": 75000.0,  # 40000 + 10000 + 10000 = 60000 != 75000
    }
    results = validate_salary_arithmetic(fields)
    comp_rule = next(r for r in results if r.rule_id == "salary_components_sum")
    assert comp_rule.result == RuleStatus.FAIL
    assert comp_rule.tier == FindingTier.INCONSISTENCY


def test_salary_missing_data_safe():
    results = validate_salary_arithmetic({})
    assert len(results) == 0  # Does not crash, returns empty list
