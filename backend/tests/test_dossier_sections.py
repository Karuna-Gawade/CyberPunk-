"""
Unit & Integration test for PS-2 Section 7 Dossier Structure:
Verifies that the generated investigation dossier strictly includes:
- 7.1 Document Overview
- 7.2 Extracted Information (with PII masking)
- 7.3 Contextual Analysis
- 7.4 Visual Forensic Findings
- 7.5 Evidence and Traceability
- 7.6 Investigation Summary
"""

from pathlib import Path
from fastapi.testclient import TestClient
import pymupdf

from backend.app.main import app

client = TestClient(app)
BUNDLES_ROOT = Path("samples/bundles")


def test_dossier_sections_and_pii_masking():
    bundle_name = "tampered_11_income_inflate"
    b_dir = BUNDLES_ROOT / bundle_name

    res_inv = client.post("/investigations")
    assert res_inv.status_code == 200
    inv_id = res_inv.json()["investigation_id"]

    # Upload documents from tampered_11
    files = []
    file_handles = []
    for f in b_dir.glob("*.pdf"):
        fh = open(f, "rb")
        file_handles.append(fh)
        files.append(("files", (f.name, fh, "application/pdf")))

    try:
        res_upload = client.post(f"/investigations/{inv_id}/documents", files=files)
        assert res_upload.status_code == 200
    finally:
        for fh in file_handles:
            fh.close()

    res_proc = client.post(f"/investigations/{inv_id}/process")
    assert res_proc.status_code == 200

    # Record human decision so it's a completed dossier
    decision_payload = {
        "decision": "partially_rely",
        "outcome_note": "Income discrepancy identified between loan app and payslip.",
        "decided_by": "OFFICER-7",
    }
    res_dec = client.post(f"/investigations/{inv_id}/decision", json=decision_payload)
    assert res_dec.status_code == 200

    # Fetch generated dossier PDF
    res_dossier = client.get(f"/investigations/{inv_id}/dossier")
    assert res_dossier.status_code == 200
    assert res_dossier.headers.get("content-type") == "application/pdf"

    # Open PDF with PyMuPDF and extract all text across pages
    doc = pymupdf.open(stream=res_dossier.content, filetype="pdf")
    all_text = ""
    for page in doc:
        all_text += page.get_text("text") + "\n"
    doc.close()

    # Verify all PS-2 Section 7 section titles are present
    assert "7.1 Document Overview" in all_text
    assert "7.2 Extracted Information" in all_text
    assert "7.3 Contextual Analysis" in all_text
    assert "7.4 Visual Forensic Findings" in all_text
    assert "7.5 Evidence and Traceability" in all_text
    assert "7.6 Investigation Summary" in all_text

    # Verify PII masking in section 7.2 table
    # Aadhaar should be masked with XXXX or similar
    if "aadhaar_number" in all_text.lower():
        # Confirm masked representation exists
        assert "XXXX" in all_text or "xxxx" in all_text.lower()
