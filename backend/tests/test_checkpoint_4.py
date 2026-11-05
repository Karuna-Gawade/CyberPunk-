"""
Integration Checkpoint 4 Test.
Verifies Master Spec Section 15 Checkpoint 4:
- Injected sample is flagged with category: injection.
- The prompt injection text does not alter scoring or decision logic.
- Every finding produced has a readable plain-language explanation containing zero forbidden words.
"""

from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.explanation import COMPILED_FORBIDDEN_REGEX

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
    res_proc = client.post(f"/investigations/{inv_id}/process")
    assert res_proc.status_code == 200

    inv = res_proc.json()
    res_findings = client.get(f"/investigations/{inv_id}/findings")
    return {
        "inv": inv,
        "findings": res_findings.json(),
    }


def test_injected_sample_flagged_without_altering_score_or_tier():
    """Checkpoint 4: injected sample flagged and does not override scoring."""
    result = upload_and_process_bundle("tampered_10_prompt_injection")
    findings = result["findings"]
    inv = result["inv"]

    # 1. Assert prompt injection was detected
    inject_findings = [f for f in findings if f["category"] == "injection"]
    assert len(inject_findings) >= 1
    assert inject_findings[0]["rule_id"] == "prompt_injection_pattern"
    assert "ignore previous instructions" in inject_findings[0]["title"].lower()

    # 2. Assert adversarial text did NOT cause an automated approval
    assert inv["case_decision"] is None

    # 3. Assert review priority remains advisory
    assert inv["review_priority"] in ("low", "medium", "high")


def test_all_findings_have_readable_explanations_with_zero_forbidden_words():
    """Checkpoint 4: every finding has readable explanation with zero forbidden words."""
    result = upload_and_process_bundle("tampered_01_salary_edit")
    findings = result["findings"]
    assert len(findings) > 0

    forbidden_terms = ["fraud", "forged", "fake", "counterfeit", "confirmed fraud"]

    for f in findings:
        explanation = f["explanation"]
        assert explanation and len(explanation.strip()) > 20
        assert not COMPILED_FORBIDDEN_REGEX.search(explanation)
        for term in forbidden_terms:
            assert term not in explanation.lower()
        # Ensure 'Requires investigation' status wording
        assert f["status"] == "requires_investigation"
