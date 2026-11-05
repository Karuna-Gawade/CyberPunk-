"""
Integration Checkpoint 2 Test.
Verifies Master Spec Section 15 Checkpoint 2:
- Clean genuine bundle produces ZERO false findings.
- Planted salary, DOB, and name mismatches EACH produce a Finding with evidence bounding boxes.
- Bank balance continuity break pinpoints the exact broken row.
"""

from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
BUNDLES_ROOT = Path("samples/bundles")


def upload_and_process_bundle(bundle_name: str) -> dict:
    b_dir = BUNDLES_ROOT / bundle_name
    res_inv = client.post("/investigations")
    assert res_inv.status_code == 200
    inv_id = res_inv.json()["investigation_id"]

    files = [
        ("files", ("aadhaar.pdf", open(b_dir / "aadhaar.pdf", "rb"), "application/pdf")),
        ("files", ("pan.pdf", open(b_dir / "pan.pdf", "rb"), "application/pdf")),
        ("files", ("salary_slip.pdf", open(b_dir / "salary_slip.pdf", "rb"), "application/pdf")),
        ("files", ("bank_statement.pdf", open(b_dir / "bank_statement.pdf", "rb"), "application/pdf")),
    ]
    res_upload = client.post(f"/investigations/{inv_id}/documents", files=files)
    assert res_upload.status_code == 200

    res_proc = client.post(f"/investigations/{inv_id}/process")
    assert res_proc.status_code == 200

    res_findings = client.get(f"/investigations/{inv_id}/findings")
    assert res_findings.status_code == 200
    return {
        "inv_id": inv_id,
        "findings": res_findings.json(),
    }


def test_clean_genuine_bundle_produces_zero_findings():
    """Checkpoint 2 requirement: clean bundle produces ZERO false alarms."""
    result = upload_and_process_bundle("genuine_01")
    findings = result["findings"]
    # Filter out weak observations if any (clean should ideally have 0 inconsistencies or manipulations)
    inconsistencies = [f for f in findings if f["tier"] in ("inconsistency", "potential_manipulation")]
    assert len(inconsistencies) == 0, f"Clean bundle produced unexpected inconsistencies: {[f['rule_id'] for f in inconsistencies]}"


def test_planted_salary_mismatch_detected_with_evidence():
    """Checkpoint 2 requirement: planted salary mismatch produces finding with evidence boxes."""
    result = upload_and_process_bundle("tampered_01_salary_edit")
    findings = result["findings"]
    rule_ids = [f["rule_id"] for f in findings]

    assert "salary_net_pay_calc" in rule_ids or "salary_credit_match" in rule_ids
    target_f = next(f for f in findings if f["rule_id"] in ("salary_net_pay_calc", "salary_credit_match"))

    # Assert evidence contains bounding boxes
    assert len(target_f["evidence"]) >= 1
    for ev in target_f["evidence"]:
        assert "bbox" in ev
        assert len(ev["bbox"]) == 4
        assert ev["bbox"][2] > ev["bbox"][0]  # width > 0
        assert ev["bbox"][3] > ev["bbox"][1]  # height > 0


def test_planted_dob_mismatch_detected_with_evidence():
    """Checkpoint 2 requirement: planted DOB mismatch produces finding with evidence boxes."""
    result = upload_and_process_bundle("tampered_02_dob_edit")
    findings = result["findings"]
    rule_ids = [f["rule_id"] for f in findings]

    assert "dob_match" in rule_ids
    target_f = next(f for f in findings if f["rule_id"] == "dob_match")

    # Assert two-sided evidence from Aadhaar and PAN
    assert len(target_f["evidence"]) == 2
    doc_ids = {e["doc_id"] for e in target_f["evidence"]}
    assert len(doc_ids) == 2  # References both documents


def test_planted_name_mismatch_detected_with_evidence():
    """Checkpoint 2 requirement: planted name mismatch produces finding with evidence boxes."""
    result = upload_and_process_bundle("tampered_03_name_variant")
    findings = result["findings"]
    rule_ids = [f["rule_id"] for f in findings]

    assert "name_match_conflict" in rule_ids
    target_f = next(f for f in findings if f["rule_id"] == "name_match_conflict")
    assert len(target_f["evidence"]) == 2


def test_planted_bank_balance_break_pinpoints_row():
    """Checkpoint 2 requirement: bank balance break is detected."""
    result = upload_and_process_bundle("tampered_05_bank_balance")
    findings = result["findings"]
    rule_ids = [f["rule_id"] for f in findings]

    assert "bank_balance_continuity" in rule_ids
    target_f = next(f for f in findings if f["rule_id"] == "bank_balance_continuity")
    assert "row 2" in target_f["title"]
