"""
Unit tests for bank running balance ledger continuity.
"""

from backend.app.models.contracts import FindingTier, RuleStatus
from backend.app.services.rules.bank import validate_bank_running_balance


def test_bank_running_balance_continuous():
    transactions = [
        {"date": "01/10/2026", "description": "ATM", "debit": 5000.0, "credit": 0.0, "balance": 95000.0},
        {"date": "10/10/2026", "description": "UPI", "debit": 2000.0, "credit": 0.0, "balance": 93000.0},
        {"date": "31/10/2026", "description": "SALARY", "debit": 0.0, "credit": 50000.0, "balance": 143000.0},
    ]
    res = validate_bank_running_balance(transactions, opening_balance=100000.0, closing_balance=143000.0)
    assert res.result == RuleStatus.PASS
    assert "maintain continuous ledger" in res.detail


def test_bank_running_balance_broken_row_pinpointing():
    transactions = [
        {"date": "01/10/2026", "description": "ATM", "debit": 5000.0, "credit": 0.0, "balance": 95000.0},
        # Row 2 math breaks: 95000 - 2000 should be 93000, reported is 99000
        {"date": "10/10/2026", "description": "TAMPERED", "debit": 2000.0, "credit": 0.0, "balance": 99000.0},
        {"date": "31/10/2026", "description": "SALARY", "debit": 0.0, "credit": 50000.0, "balance": 149000.0},
    ]
    res = validate_bank_running_balance(transactions, opening_balance=100000.0)
    assert res.result == RuleStatus.FAIL
    assert res.tier == FindingTier.INCONSISTENCY
    assert "row 2" in res.title
    assert "row 2" in res.detail
    assert "expected balance 93,000.00, but statement reports 99,000.00" in res.detail


def test_bank_missing_data_safe():
    res = validate_bank_running_balance([])
    assert res.result == RuleStatus.NOT_APPLICABLE
