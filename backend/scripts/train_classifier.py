"""
XGBoost Document Classifier Trainer for PS-2 AI Document Forensics System.
Supervised training over TF-IDF n-gram text representations.
Artifacts saved to backend/app/services/xgb_classifier.pkl.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import joblib
import fitz  # PyMuPDF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedKFold, cross_val_score
import xgboost as xgb
import numpy as np

DATA_ORIGINALS = Path("data/originals")
BUNDLES_DIR = Path("samples/bundles")
OUTPUT_MODEL_PATH = Path("backend/app/services/xgb_classifier.pkl")

# Mapping from filename patterns to canonical DocumentType values
LABEL_MAPPINGS = {
    "aadhaar": "aadhaar",
    "pan": "pan",
    "salary_slip": "salary_slip",
    "slip": "salary_slip",
    "bank_statement": "bank_statement",
    "statement": "bank_statement",
    "loan_application": "loan_application",
    "declaration_15g": "declaration_15g",
    "payment_instruction": "payment_instruction",
}


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extracts raw text layer from PDF using PyMuPDF."""
    text_chunks = []
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            t = page.get_text()
            if t:
                text_chunks.append(t)
        doc.close()
    except Exception as e:
        pass
    return "\n".join(text_chunks).strip()


def infer_label_from_filename(filename: str) -> str:
    lower_name = filename.lower()
    for pattern, canonical in LABEL_MAPPINGS.items():
        if pattern in lower_name:
            return canonical
    return None


def collect_training_samples() -> Tuple[List[str], List[str]]:
    texts = []
    labels = []

    # 1. Collect from data/originals/
    if DATA_ORIGINALS.exists():
        for pdf_path in DATA_ORIGINALS.glob("*.pdf"):
            label = infer_label_from_filename(pdf_path.name)
            if not label:
                continue
            text = extract_text_from_pdf(pdf_path)
            if len(text) > 20:
                texts.append(text)
                labels.append(label)

    # 2. Collect from samples/bundles/ to ensure all 7 classes (including loan, 15g, payment) are represented
    if BUNDLES_DIR.exists():
        for pdf_path in BUNDLES_DIR.rglob("*.pdf"):
            label = infer_label_from_filename(pdf_path.name)
            if not label:
                continue
            text = extract_text_from_pdf(pdf_path)
            if len(text) > 20:
                texts.append(text)
                labels.append(label)

    # 3. Oversample minority classes (< 50 samples) to balance training distribution
    from collections import Counter
    counts = Counter(labels)
    target_min = 60
    aug_texts = list(texts)
    aug_labels = list(labels)

    for cls, count in counts.items():
        if count < target_min:
            multiplier = int(np.ceil(target_min / count))
            cls_texts = [t for t, l in zip(texts, labels) if l == cls]
            for _ in range(multiplier - 1):
                aug_texts.extend(cls_texts)
                aug_labels.extend([cls] * len(cls_texts))

    return aug_texts, aug_labels


def train_classifier():
    print("Collecting training samples...")
    texts, raw_labels = collect_training_samples()
    print(f"Collected {len(texts)} training documents across classes.")

    unique_classes, counts = np.unique(raw_labels, return_counts=True)
    for cls, cnt in zip(unique_classes, counts):
        print(f"  - {cls}: {cnt} samples")

    label_to_idx = {cls: idx for idx, cls in enumerate(sorted(unique_classes))}
    idx_to_label = [cls for cls, idx in sorted(label_to_idx.items(), key=lambda x: x[1])]
    y = np.array([label_to_idx[l] for l in raw_labels])

    print("\nVectorizing text with TF-IDF...")
    vectorizer = TfidfVectorizer(
        max_features=2500,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=2,
        token_pattern=r"(?u)\b\w+\b",
    )
    X = vectorizer.fit_transform(texts)

    print("Fitting XGBoost Classifier...")
    classifier = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.1,
        objective="multi:softprob",
        eval_metric="mlogloss",
        random_state=42,
    )

    # Cross-validation validation
    min_samples = min(counts)
    n_splits = min(5, min_samples)
    if n_splits >= 2:
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        scores = cross_val_score(classifier, X, y, cv=cv, scoring="accuracy")
        print(f"Stratified {n_splits}-fold CV Accuracy: {scores.mean():.2%} (+/- {scores.std():.2%})")

    classifier.fit(X, y)

    OUTPUT_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "vectorizer": vectorizer,
        "model": classifier,
        "label_names": idx_to_label,
        "classes": unique_classes.tolist(),
    }
    joblib.dump(artifact, OUTPUT_MODEL_PATH)
    print(f"[SUCCESS] Model artifact saved to {OUTPUT_MODEL_PATH}")


if __name__ == "__main__":
    train_classifier()
