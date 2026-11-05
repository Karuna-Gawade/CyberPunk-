"""
Integration Checkpoint 3 Test.
Verifies Master Spec Section 15 Checkpoint 3:
- Font-edited and overlay samples are flagged at the correct region.
- Genuine samples yield no moderate or strong forensic observations.
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
    client.post(f"/investigations/{inv_id}/documents", files=files)
    client.post(f"/investigations/{inv_id}/process")

    res_findings = client.get(f"/investigations/{inv_id}/findings")
    return {
        "inv_id": inv_id,
        "findings": res_findings.json(),
    }


def test_font_edited_sample_flagged_at_correct_region():
    """Checkpoint 3: font-edited sample flagged at correct region."""
    result = upload_and_process_bundle("tampered_07_font_edit")
    findings = result["findings"]
    font_findings = [f for f in findings if f["rule_id"] in ("font_anomaly", "font_size_anomaly")]

    assert len(font_findings) >= 1
    target = font_findings[0]
    assert len(target["evidence"]) >= 1
    ev = target["evidence"][0]
    # Check region coordinates are non-empty
    assert ev["bbox"][2] > ev["bbox"][0]
    assert ev["bbox"][3] > ev["bbox"][1]


def test_overlay_sample_flagged_with_metadata_and_eof():
    """Checkpoint 3: overlay / incremental re-save flagged."""
    result = upload_and_process_bundle("tampered_08_text_overlay")
    findings = result["findings"]
    rule_ids = [f["rule_id"] for f in findings]

    assert "producer_editing_tool" in rule_ids or "incremental_updates_flag" in rule_ids


def test_genuine_samples_yield_no_moderate_or_strong_forensic_observations():
    """Checkpoint 3: genuine samples yield no moderate/strong observations."""
    result = upload_and_process_bundle("genuine_01")
    findings = result["findings"]

    forensic_findings = [
        f for f in findings
        if f["category"] == "forensic" and f["strength"] in ("moderate", "strong")
    ]
    assert len(forensic_findings) == 0, f"Unexpected moderate/strong forensic observations on clean bundle: {forensic_findings}"
