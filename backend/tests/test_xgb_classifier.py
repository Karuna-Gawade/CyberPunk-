"""
Unit tests for the XGBoost ML document classification model.
"""

from pathlib import Path
import fitz
import joblib
from backend.app.models.contracts import DocumentType
from backend.app.services.classification import MODEL_PATH, classify_with_xgb


def test_xgb_model_artifact_structure():
    assert MODEL_PATH.exists(), f"Model artifact not found at {MODEL_PATH}"
    artifact = joblib.load(MODEL_PATH)
    assert "vectorizer" in artifact
    assert "model" in artifact
    assert "label_names" in artifact

    expected_types = {
        "aadhaar",
        "pan",
        "salary_slip",
        "bank_statement",
        "loan_application",
        "declaration_15g",
        "payment_instruction",
    }
    present_types = set(artifact["label_names"])
    assert expected_types.issubset(present_types)


def test_xgb_classify_samples():
    bundle_dir = Path("samples/bundles/genuine_06")
    file_map = {
        "aadhaar.pdf": DocumentType.AADHAAR,
        "pan.pdf": DocumentType.PAN,
        "salary_slip.pdf": DocumentType.SALARY_SLIP,
        "bank_statement.pdf": DocumentType.BANK_STATEMENT,
        "loan_application.pdf": DocumentType.LOAN_APPLICATION,
        "declaration_15g.pdf": DocumentType.DECLARATION_15G,
        "payment_instruction.pdf": DocumentType.PAYMENT_INSTRUCTION,
    }

    for fname, expected_type in file_map.items():
        doc_path = bundle_dir / fname
        assert doc_path.exists(), f"Sample file {doc_path} missing"
        doc = fitz.open(doc_path)
        text = doc[0].get_text()
        doc.close()

        res = classify_with_xgb(text)
        assert res is not None, f"XGB returned None for {fname}"
        pred_type, conf = res
        assert pred_type == expected_type, f"Expected {expected_type}, got {pred_type} for {fname}"
        assert conf >= 0.70


def test_xgb_classify_unrelated_returns_none_or_defers():
    res = classify_with_xgb("The gentle breeze whispered across the rolling hills of the green countryside.")
    # Unrelated prose must either return None or yield low confidence
    assert res is None or res[1] < 0.70
