"""
Unit and integration tests for universal OCR text line and unsupported document field extraction.
Validates:
1. OCR extracts text lines from every document (supported and unsupported).
2. Unsupported documents (like receipts, transaction slips) extract both generic key-value fields and all OCR text lines.
3. Extracted fields have valid bounding boxes, confidences, and sources.
4. Extracted fields persist to SQLite storage and can be retrieved via the API.
"""

from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.contracts import DocumentType, FieldSource
from backend.app.services.extraction.field_parser import (
    extract_all_text_lines,
    extract_generic_key_values,
    parse_document_fields,
)

client = TestClient(app)


def test_extract_all_text_lines_from_pages_data():
    sample_pages_data = [
        {
            "page": 1,
            "full_text": "State Bank of India\nBranch : Main Branch\nAmount : 5000",
            "words": [
                {"text": "State", "bbox": [100, 50, 150, 70], "confidence": 0.95, "source": "ocr"},
                {"text": "Bank", "bbox": [160, 50, 200, 70], "confidence": 0.96, "source": "ocr"},
                {"text": "of", "bbox": [205, 50, 220, 70], "confidence": 0.94, "source": "ocr"},
                {"text": "India", "bbox": [225, 50, 270, 70], "confidence": 0.98, "source": "ocr"},
                {"text": "Branch", "bbox": [50, 100, 110, 120], "confidence": 0.92, "source": "ocr"},
                {"text": ":", "bbox": [115, 100, 120, 120], "confidence": 0.90, "source": "ocr"},
                {"text": "Main", "bbox": [125, 100, 160, 120], "confidence": 0.95, "source": "ocr"},
                {"text": "Branch", "bbox": [165, 100, 210, 120], "confidence": 0.94, "source": "ocr"},
                {"text": "Amount", "bbox": [50, 150, 110, 170], "confidence": 0.93, "source": "ocr"},
                {"text": ":", "bbox": [115, 150, 120, 170], "confidence": 0.91, "source": "ocr"},
                {"text": "5000", "bbox": [125, 150, 165, 170], "confidence": 0.97, "source": "ocr"},
            ],
            "spans": [],
        }
    ]

    lines = extract_all_text_lines("DOC-TEST-1", sample_pages_data)
    assert len(lines) == 3
    assert lines[0].value == "State Bank of India"
    assert lines[0].bbox == [100, 50, 270, 70]
    assert lines[0].source == FieldSource.OCR

    assert lines[1].value == "Branch : Main Branch"
    assert lines[1].bbox == [50, 100, 210, 120]

    assert lines[2].value == "Amount : 5000"
    assert lines[2].bbox == [50, 150, 165, 170]


def test_extract_generic_key_values_from_unsupported():
    sample_pages_data = [
        {
            "page": 1,
            "full_text": "Header Slip\nBranch : 01234 - Main Branch\nDate : 31/10/2026\nTransaction ID : TXN9988\nAmount : 5000.00\nStatus : SUCCESS",
            "words": [
                {"text": "Branch", "bbox": [50, 100, 110, 120], "confidence": 0.92, "source": "ocr"},
                {"text": ":", "bbox": [115, 100, 120, 120], "confidence": 0.90, "source": "ocr"},
                {"text": "01234", "bbox": [125, 100, 170, 120], "confidence": 0.95, "source": "ocr"},
                {"text": "-", "bbox": [175, 100, 185, 120], "confidence": 0.90, "source": "ocr"},
                {"text": "Main", "bbox": [190, 100, 225, 120], "confidence": 0.95, "source": "ocr"},
                {"text": "Branch", "bbox": [230, 100, 280, 120], "confidence": 0.94, "source": "ocr"},
                {"text": "Date", "bbox": [50, 130, 90, 150], "confidence": 0.95, "source": "ocr"},
                {"text": ":", "bbox": [95, 130, 100, 150], "confidence": 0.90, "source": "ocr"},
                {"text": "31/10/2026", "bbox": [105, 130, 180, 150], "confidence": 0.96, "source": "ocr"},
                {"text": "Transaction", "bbox": [50, 160, 130, 180], "confidence": 0.92, "source": "ocr"},
                {"text": "ID", "bbox": [135, 160, 150, 180], "confidence": 0.92, "source": "ocr"},
                {"text": ":", "bbox": [155, 160, 160, 180], "confidence": 0.90, "source": "ocr"},
                {"text": "TXN9988", "bbox": [165, 160, 230, 180], "confidence": 0.95, "source": "ocr"},
            ],
            "spans": [],
        }
    ]

    kv_fields = extract_generic_key_values("DOC-TEST-2", sample_pages_data)
    assert len(kv_fields) >= 3
    kv_dict = {f.name: f.value for f in kv_fields}
    assert "branch" in kv_dict
    assert "01234 - Main Branch" in kv_dict["branch"]
    assert "date" in kv_dict
    assert kv_dict["date"] == "31/10/2026"
    assert "transaction_id" in kv_dict
    assert kv_dict["transaction_id"] == "TXN9988"


def test_parse_document_fields_returns_both_kv_and_all_lines():
    sample_pages_data = [
        {
            "page": 1,
            "full_text": "Slip\nBranch : Main Branch\nAmount : 5000",
            "words": [
                {"text": "Slip", "bbox": [50, 20, 100, 40], "confidence": 0.95, "source": "ocr"},
                {"text": "Branch", "bbox": [50, 60, 100, 80], "confidence": 0.92, "source": "ocr"},
                {"text": ":", "bbox": [105, 60, 110, 80], "confidence": 0.90, "source": "ocr"},
                {"text": "Main", "bbox": [115, 60, 150, 80], "confidence": 0.95, "source": "ocr"},
                {"text": "Branch", "bbox": [155, 60, 200, 80], "confidence": 0.94, "source": "ocr"},
                {"text": "Amount", "bbox": [50, 100, 100, 120], "confidence": 0.93, "source": "ocr"},
                {"text": ":", "bbox": [105, 100, 110, 120], "confidence": 0.90, "source": "ocr"},
                {"text": "5000", "bbox": [115, 100, 150, 120], "confidence": 0.97, "source": "ocr"},
            ],
            "spans": [],
        }
    ]

    # For an unsupported document
    fields = parse_document_fields("DOC-UNSUP", DocumentType.UNSUPPORTED, sample_pages_data)
    assert len(fields) > 0

    field_names = [f.name for f in fields]
    # Contains key-values
    assert "branch" in field_names
    assert "amount" in field_names
    # Contains universal text lines
    assert any(name.startswith("line_") for name in field_names)


def test_sbi_transaction_slip_end_to_end_upload_and_fields():
    """Validates real end-to-end extraction on DOC-BF5A6B_SBI Transaction Slip.png"""
    sample_path = Path("data/originals/DOC-BF5A6B_SBI Transaction Slip.png")
    if not sample_path.exists():
        return

    # 1. Create investigation
    res_inv = client.post("/investigations")
    assert res_inv.status_code == 200
    inv_id = res_inv.json()["investigation_id"]

    # 2. Upload the real SBI Transaction Slip
    with open(sample_path, "rb") as f:
        res_upload = client.post(
            f"/investigations/{inv_id}/documents",
            files=[("files", ("SBI_Slip.png", f, "image/png"))],
        )
    assert res_upload.status_code == 200
    docs = res_upload.json()
    assert len(docs) == 1
    doc_id = docs[0]["doc_id"]

    # 3. Process the investigation
    res_proc = client.post(f"/investigations/{inv_id}/process")
    assert res_proc.status_code == 200

    # 4. Fetch fields
    res_fields = client.get(f"/documents/{doc_id}/fields")
    assert res_fields.status_code == 200
    fields = res_fields.json()

    # Must NOT have 0 fields
    assert len(fields) >= 10, f"Expected at least 10 extracted fields, got {len(fields)}"

    # Check presence of OCR text lines
    line_fields = [f for f in fields if f["name"].startswith("line_")]
    assert len(line_fields) >= 8, f"Expected at least 8 text lines, got {len(line_fields)}"

    # Check all fields have valid bboxes
    for f in fields:
        assert "bbox" in f
        assert len(f["bbox"]) == 4
        assert f["bbox"][2] >= f["bbox"][0]
        assert f["bbox"][3] >= f["bbox"][1]


def test_ingestion_fallback_when_tesseract_unavailable(monkeypatch, tmp_path):
    from backend.app.models.contracts import DocumentStatus, Investigation
    from backend.app.services.ingestion import IngestionService
    from backend.app.db.storage import StorageManager
    from backend.app.services.audit import AuditService
    import cv2
    import numpy as np

    # Mock find_tesseract_binary to return None (simulating Netlify serverless / Lambda)
    monkeypatch.setattr("backend.app.services.ingestion.find_tesseract_binary", lambda: None)

    storage = StorageManager(tmp_path / "app.db", tmp_path / "data")
    audit = AuditService(tmp_path / "app.db")
    service = IngestionService(storage, audit)

    # Ingest a test image
    fake_img = np.ones((400, 600, 3), dtype=np.uint8) * 255
    cv2.putText(fake_img, "SBI Transaction Slip", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    img_path = tmp_path / "SBI_Transaction_Slip.png"
    cv2.imwrite(str(img_path), fake_img)

    inv = Investigation(investigation_id="INV-TEST-FALLBACK", created_at="2026-11-07T14:18:00")
    storage.create_investigation(inv)
    doc_rec = service.ingest_file("INV-TEST-FALLBACK", "DOC-FALLBACK-1", img_path, "SBI_Transaction_Slip.png")

    # Process without Tesseract
    processed_doc = service.process_document("INV-TEST-FALLBACK", "DOC-FALLBACK-1")

    # Assert it did NOT fail with OCR_FAILED!
    assert processed_doc.status != DocumentStatus.OCR_FAILED
    assert processed_doc.status in (DocumentStatus.PROCESSED, DocumentStatus.UNSUPPORTED)
    assert len(processed_doc.fields) > 0

