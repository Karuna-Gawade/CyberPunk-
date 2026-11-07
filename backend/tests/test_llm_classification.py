"""
Unit & Integration tests for LLM Document Classification and Persistence across browser refreshes.
"""

from pathlib import Path
from fastapi.testclient import TestClient
import fitz

from backend.app.main import app
from backend.app.models.contracts import DocumentType
from backend.app.services.llm_classification import (
    classify_document_with_llm,
    classify_with_local_llm,
)

client = TestClient(app)
BUNDLES_ROOT = Path("samples/bundles")


def test_llm_classification_all_seven_types():
    bundle_dir = BUNDLES_ROOT / "genuine_06"
    expected = {
        "aadhaar.pdf": DocumentType.AADHAAR,
        "pan.pdf": DocumentType.PAN,
        "salary_slip.pdf": DocumentType.SALARY_SLIP,
        "bank_statement.pdf": DocumentType.BANK_STATEMENT,
        "loan_application.pdf": DocumentType.LOAN_APPLICATION,
        "declaration_15g.pdf": DocumentType.DECLARATION_15G,
        "payment_instruction.pdf": DocumentType.PAYMENT_INSTRUCTION,
    }

    for fname, expected_type in expected.items():
        doc_path = bundle_dir / fname
        assert doc_path.exists(), f"Sample {fname} missing"
        doc = fitz.open(doc_path)
        text = doc[0].get_text()
        doc.close()

        res = classify_document_with_llm(text)
        assert res.classification_type == expected_type, f"Failed for {fname}: got {res.classification_type}"
        assert res.accuracy >= 0.85, f"Accuracy too low for {fname}: {res.accuracy}"
        assert len(res.reasoning) > 20, f"Reasoning empty for {fname}"
        assert len(res.provider) > 0


def test_llm_classification_unsupported_text():
    res = classify_document_with_llm("Shopping list: 2 apples, 1 milk carton, bread and eggs. Have a nice weekend!")
    assert res.classification_type == DocumentType.UNSUPPORTED
    assert res.accuracy == 0.0


def test_document_persistence_and_refresh_workflow():
    """
    Verifies that when documents are uploaded and processed:
    1. They are saved in SQLite with their LLM classification and accuracy.
    2. Listing all investigations returns the investigation.
    3. Simulating a browser refresh (calling GET /investigations/{id}) re-fetches
       the exact saved documents, their LLM type, and LLM accuracy.
    """
    # Create investigation
    res_create = client.post("/investigations")
    assert res_create.status_code == 200
    inv_id = res_create.json()["investigation_id"]

    # Upload two documents
    pan_file = BUNDLES_ROOT / "genuine_06" / "pan.pdf"
    loan_file = BUNDLES_ROOT / "genuine_06" / "loan_application.pdf"

    with open(pan_file, "rb") as f1, open(loan_file, "rb") as f2:
        res_upload = client.post(
            f"/investigations/{inv_id}/documents",
            files=[
                ("files", ("pan.pdf", f1, "application/pdf")),
                ("files", ("loan_application.pdf", f2, "application/pdf")),
            ],
        )
    assert res_upload.status_code == 200

    # Process investigation
    res_proc = client.post(f"/investigations/{inv_id}/process")
    assert res_proc.status_code == 200
    proc_inv = res_proc.json()

    assert len(proc_inv["documents"]) == 2
    for d in proc_inv["documents"]:
        assert d["llm_type"] is not None
        assert d["llm_accuracy"] is not None
        assert d["llm_accuracy"] > 0.80
        assert d["llm_reasoning"] is not None
        assert len(d["llm_reasoning"]) > 10

    # Test GET /investigations (list endpoint)
    res_list = client.get("/investigations")
    assert res_list.status_code == 200
    all_invs = res_list.json()
    assert any(inv["investigation_id"] == inv_id for inv in all_invs)

    # Simulate browser refresh: fetch GET /investigations/{id}
    res_refresh = client.get(f"/investigations/{inv_id}")
    assert res_refresh.status_code == 200
    refreshed_inv = res_refresh.json()

    assert refreshed_inv["investigation_id"] == inv_id
    assert len(refreshed_inv["documents"]) == 2

    # Verify each document's LLM accuracy and classification persisted in DB
    pan_doc = next(d for d in refreshed_inv["documents"] if d["filename"] == "pan.pdf")
    loan_doc = next(d for d in refreshed_inv["documents"] if d["filename"] == "loan_application.pdf")

    assert pan_doc["llm_type"] == "pan"
    assert pan_doc["llm_accuracy"] >= 0.85
    assert "PAN" in pan_doc["llm_reasoning"] or "Income Tax" in pan_doc["llm_reasoning"]

    assert loan_doc["llm_type"] == "loan_application"
    assert loan_doc["llm_accuracy"] >= 0.85
    assert "Loan" in loan_doc["llm_reasoning"]
