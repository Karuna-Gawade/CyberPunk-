"""
Deterministic document classification service.
Uses configurable keyword weights, regular expressions, and layout markers.
Falls back safely to 'unsupported' if below threshold.
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
import joblib
from backend.app.models.contracts import DocumentType

CONFIG_PATH = Path(__file__).resolve().parent / "classification_config.json"
MODEL_PATH = Path(__file__).resolve().parent / "xgb_classifier.pkl"


def load_classification_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _heuristic_classify(text: str) -> Tuple[DocumentType, float]:
    """
    Heuristic rule-based fallback classification.
    Uses configurable keyword weights, regular expressions, and layout markers.
    """
    if not text or len(text.strip()) < 10:
        return DocumentType.UNSUPPORTED, 0.0

    config = load_classification_config()
    text_lower = text.lower()
    scores: Dict[str, float] = {doc_type: 0.0 for doc_type in config.keys()}

    for doc_type, rules in config.items():
        # Keyword matches (10 points each)
        for kw in rules.get("keywords", []):
            if kw in text_lower:
                scores[doc_type] += 10.0

        # Regex matches (20 points each)
        for pattern in rules.get("regex", []):
            if re.search(pattern, text, re.IGNORECASE):
                scores[doc_type] += 20.0

    best_type, best_score = max(scores.items(), key=lambda item: item[1])
    min_required = config.get(best_type, {}).get("min_score", 25.0)

    if best_score < min_required:
        return DocumentType.UNSUPPORTED, 0.0

    # Normalize confidence between 0.50 and 0.99
    confidence = min(0.99, max(0.50, round(best_score / (best_score + 15.0), 2)))
    try:
        return DocumentType(best_type), confidence
    except ValueError:
        return DocumentType.UNSUPPORTED, 0.0


def classify_with_xgb(text: str) -> Optional[Tuple[DocumentType, float]]:
    """
    Classifies text using pre-trained TF-IDF + XGBoost model if available.
    Returns (DocumentType, confidence) or None if model unavailable or low confidence.
    """
    if not MODEL_PATH.exists() or not text or len(text.strip()) < 15:
        return None

    try:
        artifact = joblib.load(MODEL_PATH)
        vec = artifact["vectorizer"]
        clf = artifact["model"]
        label_names = artifact["label_names"]

        X = vec.transform([text])
        proba = clf.predict_proba(X)[0]
        best_idx = int(proba.argmax())
        confidence = float(proba[best_idx])

        # Defer to heuristic if model confidence is low (< 0.60)
        if confidence < 0.60:
            return None

        best_label = label_names[best_idx]
        return DocumentType(best_label), round(confidence, 2)
    except Exception:
        return None


def classify_document_text(text: str) -> Tuple[DocumentType, float]:
    """
    Two-stage document classifier:
    1. Supervised XGBoost ML classifier (if model artifact exists and confidence >= 0.60).
    2. Deterministic heuristic & regex rules engine (robust offline fallback).
    """
    xgb_result = classify_with_xgb(text)
    if xgb_result is not None:
        return xgb_result

    return _heuristic_classify(text)
