"""
Unit tests for Aadhaar secure QR vs printed text comparison rule.
"""

from backend.app.models.contracts import FindingTier, RuleStatus
from backend.app.services.rules.aadhaar_qr_match import validate_aadhaar_qr_against_printed


def test_aadhaar_qr_match_valid():
    qr_payload = {
        "name": "Rajesh Sharma",
        "dob": "14/05/1988",
        "gender": "Male",
    }
    printed_fields = {
        "name": "Rajesh Sharma",
        "dob": "14/05/1988",
        "gender": "Male",
    }
    res = validate_aadhaar_qr_against_printed(qr_payload, printed_fields)
    assert res.result == RuleStatus.PASS
    assert "perfectly match" in res.detail


def test_aadhaar_qr_dob_tampering_mismatch():
    qr_payload = {
        "name": "Rajesh Sharma",
        "dob": "14/05/1988",
        "gender": "Male",
    }
    # Tampered printed DOB on document face
    printed_fields = {
        "name": "Rajesh Sharma",
        "dob": "14/05/1995",
        "gender": "Male",
    }
    res = validate_aadhaar_qr_against_printed(qr_payload, printed_fields)
    assert res.result == RuleStatus.FAIL
    assert res.tier == FindingTier.INCONSISTENCY
    assert "Date of Birth in QR" in res.detail


def test_aadhaar_qr_undecodable_unable_to_assess():
    # If QR payload is missing/None -> must NOT pass silently
    res = validate_aadhaar_qr_against_printed(None, {"name": "Rajesh Sharma"})
    assert res.result == RuleStatus.NOT_APPLICABLE
    assert "Unable to assess" in res.detail
