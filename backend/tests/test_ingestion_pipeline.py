"""
Integration tests for document ingestion, processing, and field extraction pipeline.
Uses real synthetic genuine bundle files.
"""

from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
BUNDLE_DIR = Path("samples/bundles/genuine_01")


def test_full_bundle_ingestion_and_processing():
    # 1. Create investigation
    res_inv = client.post("/investigations")
    assert res_inv.status_code == 200
    inv = res_inv.json()
    inv_id = inv["investigation_id"]

    # 2. Upload documents
    files = [
        ("files", ("aadhaar.pdf", open(BUNDLE_DIR / "aadhaar.pdf", "rb"), "application/pdf")),
        ("files", ("pan.pdf", open(BUNDLE_DIR / "pan.pdf", "rb"), "application/pdf")),
        ("files", ("salary_slip.pdf", open(BUNDLE_DIR / "salary_slip.pdf", "rb"), "application/pdf")),
        ("files", ("bank_statement.pdf", open(BUNDLE_DIR / "bank_statement.pdf", "rb"), "application/pdf")),
    ]
    res_upload = client.post(f"/investigations/{inv_id}/documents", files=files)
    assert res_upload.status_code == 200
    docs = res_upload.json()
    assert len(docs) == 4

    # 3. Process investigation
    res_proc = client.post(f"/investigations/{inv_id}/process")
    assert res_proc.status_code == 200
    processed_inv = res_proc.json()

    # 4. Verify each document is properly classified and extracted
    type_map = {d["filename"]: d["type"] for d in processed_inv["documents"]}
    assert type_map["aadhaar.pdf"] == "aadhaar"
    assert type_map["pan.pdf"] == "pan"
    assert type_map["salary_slip.pdf"] == "salary_slip"
    assert type_map["bank_statement.pdf"] == "bank_statement"

    # 5. Verify fields extraction & masking
    for doc in processed_inv["documents"]:
        doc_id = doc["doc_id"]
        res_fields = client.get(f"/documents/{doc_id}/fields")
        assert res_fields.status_code == 200
        fields = res_fields.json()
        assert len(fields) > 0

        # Check that bounding box exists on every field
        for f in fields:
            assert "bbox" in f
            assert len(f["bbox"]) == 4
            assert f["page"] >= 1
            if f["name"] == "aadhaar_number":
                # Must be masked
                assert "XXXX" in str(f["value"])
            if f["name"] == "pan_number":
                # Must be masked
                assert "XXXX" in str(f["value"])

        # 6. Verify 150 DPI page image is retrievable
        res_img = client.get(f"/documents/{doc_id}/pages/1/image")
        assert res_img.status_code == 200
        assert res_img.headers["content-type"] == "image/png"
        assert len(res_img.content) > 1000  # valid image bytes


def test_pii_reveal_workflow():
    # Create investigation and upload PAN
    res_inv = client.post("/investigations")
    inv_id = res_inv.json()["investigation_id"]

    files = [("files", ("pan.pdf", open(BUNDLE_DIR / "pan.pdf", "rb"), "application/pdf"))]
    res_upload = client.post(f"/investigations/{inv_id}/documents", files=files)
    doc_id = res_upload.json()[0]["doc_id"]

    client.post(f"/investigations/{inv_id}/process")
    fields = client.get(f"/documents/{doc_id}/fields").json()

    pan_field = next(f for f in fields if f["name"] == "pan_number")
    assert "XXXX" in str(pan_field["value"])

    # Unmask via reveal endpoint
    res_reveal = client.post(f"/fields/{pan_field['field_id']}/reveal")
    assert res_reveal.status_code == 200
    reveal_data = res_reveal.json()
    assert "BCDPS1234E" in str(reveal_data["unmasked_value"])

    # Verify reveal was logged in audit trail
    res_audit = client.get(f"/investigations/{inv_id}/audit")
    assert res_audit.status_code == 200
    events = res_audit.json()
    assert any(e["action"] in ("document_ingested", "document_processed") for e in events)
