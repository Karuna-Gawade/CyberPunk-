"""
Deterministic document classification service.
Uses configurable keyword weights, regular expressions, and layout markers.
Falls back safely to 'unsupported' if below threshold.
"""

import json
import re
from pathlib import Path
from typing import Dict, Tuple
from backend.app.models.contracts import DocumentType

CONFIG_PATH = Path(__file__).resolve().parent / "classification_config.json"


def load_classification_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def classify_document_text(text: str) -> Tuple[DocumentType, float]:
    """
    Classifies extracted text into:
      aadhaar | pan | salary_slip | bank_statement | unsupported
    Returns (DocumentType, confidence 0.0 - 1.0).
    """
    if not text or len(text.strip()) < 10:
        return DocumentType.UNSUPPORTED, 0.0

    config = load_classification_config()
    text_lower = text.lower()
    scores: Dict[str, float] = {
        "aadhaar": 0.0,
        "pan": 0.0,
        "salary_slip": 0.0,
        "bank_statement": 0.0,
    }

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
    return DocumentType(best_type), confidence
