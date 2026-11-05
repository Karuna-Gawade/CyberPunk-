"""
Unit tests for PAN structure and surname initial validation.
"""

from backend.app.models.contracts import RuleStatus
from backend.app.services.rules.pan import validate_pan_structure


def test_pan_valid_individual_matching_surname():
    # Holder: Rajesh Sharma, Surname initial: S, 5th char: S
    res = validate_pan_structure(pan_number="BCDPS1234E", holder_name="Rajesh Sharma")
    assert res.result == RuleStatus.PASS
    assert "Individual" in res.detail


def test_pan_surname_mismatch():
    # Holder: Rajesh Sharma, Surname initial: S, 5th char: K -> Mismatch
    res = validate_pan_structure(pan_number="BCDPK1234E", holder_name="Rajesh Sharma")
    assert res.result == RuleStatus.FAIL
    assert res.signals == ["pan_surname_mismatch"]
    assert "surname initial" in res.detail


def test_pan_company_entity():
    # 4th char: C -> Company
    res = validate_pan_structure(pan_number="AAACB1234F", holder_name="Apex Tech Pvt Ltd")
    assert res.result == RuleStatus.PASS
    assert "Company" in res.detail


def test_pan_invalid_format():
    res = validate_pan_structure(pan_number="INVALID123", holder_name="Rajesh Sharma")
    assert res.result == RuleStatus.FAIL
    assert res.signals == ["pan_regex_invalid"]


def test_pan_missing_data():
    res = validate_pan_structure(pan_number="", holder_name="")
    assert res.result == RuleStatus.NOT_APPLICABLE
