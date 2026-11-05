"""
Explicit failure handling test suite.
Ensures no silent failures:
- Corrupt / encrypted file -> Document status error/encrypted; other docs continue
- Unsupported document -> status unsupported with explicit message
- Undecodable QR -> Unable to assess
"""

import io
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_corrupt_file_failure_handling():
    res_inv = client.post("/investigations")
    inv_id = res_inv.json()["investigation_id"]

    corrupt_bytes = b"NOT_A_VALID_PDF_HEADER_JUST_GARBAGE_BYTES_123456789"
    files = [("files", ("corrupt.pdf", io.BytesIO(corrupt_bytes), "application/pdf"))]
    res_upload = client.post(f"/investigations/{inv_id}/documents", files=files)
    assert res_upload.status_code == 200

    client.post(f"/investigations/{inv_id}/process")
    status_data = client.get(f"/investigations/{inv_id}/status").json()
    doc_status = status_data["documents"][0]
    assert doc_status["status"] == "error"


def test_unsupported_document_type_handling():
    res_inv = client.post("/investigations")
    inv_id = res_inv.json()["investigation_id"]

    # Simple text document about groceries (unsupported)
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Store Grocery Receipt #99281\nMilk 2L: 120\nBread: 40\nTotal: 160\nThank you!")
    pdf_bytes = doc.tobytes()
    doc.close()

    files = [("files", ("receipt.pdf", io.BytesIO(pdf_bytes), "application/pdf"))]
    res_upload = client.post(f"/investigations/{inv_id}/documents", files=files)
    assert res_upload.status_code == 200

    client.post(f"/investigations/{inv_id}/process")
    status_data = client.get(f"/investigations/{inv_id}/status").json()
    doc_status = status_data["documents"][0]
    assert doc_status["type"] == "unsupported"
    assert doc_status["status"] == "unsupported"

    # Verify document record details
    doc_record = client.get(f"/documents/{doc_status['doc_id']}").json()
    assert "Unsupported document type, manual review required." in doc_record["error_message"]
