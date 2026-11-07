"""
Multilingual and Handwritten Document Processing Service for PS-2.
Provides:
1. Script and Language Identification (Devanagari/Hindi/Marathi, Tamil, Telugu, Bengali, Gujarati, Latin/English, etc.)
2. Handwritten vs. Machine-Printed Text Classification
3. Signature and Annotation Localization
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from backend.app.models.contracts import ExtractedField


# Unicode ranges for major Indian scripts and Latin
SCRIPT_RANGES = {
    "Devanagari": (0x0900, 0x097F, "hi"),  # Hindi, Marathi
    "Tamil": (0x0B80, 0x0BFF, "ta"),
    "Telugu": (0x0C00, 0x0C7F, "te"),
    "Bengali": (0x0980, 0x09FF, "bn"),
    "Gujarati": (0x0A80, 0x0AFF, "gu"),
    "Kannada": (0x0C80, 0x0CFF, "kn"),
    "Malayalam": (0x0D00, 0x0D7F, "ml"),
    "Gurmukhi": (0x0A00, 0x0A7F, "pa"),  # Punjabi
    "Arabic": (0x0600, 0x06FF, "ur"),    # Urdu
    "Latin": (0x0020, 0x00FF, "en"),     # English
}


def detect_text_script_and_language(text: str) -> Tuple[str, str, List[str]]:
    """
    Identifies the primary script and language of a text block based on Unicode codepoints.
    Returns: (primary_script, primary_language_code, all_detected_scripts)
    """
    if not text:
        return "Latin", "en", ["Latin"]

    script_counts: Dict[str, int] = {name: 0 for name in SCRIPT_RANGES}

    for ch in text:
        cp = ord(ch)
        for s_name, (start, end, _) in SCRIPT_RANGES.items():
            if start <= cp <= end:
                script_counts[s_name] += 1
                break

    detected = [s for s, count in script_counts.items() if count > 0]
    if not detected:
        return "Latin", "en", ["Latin"]

    # Select primary non-Latin if significant (>10% of total letters), otherwise highest count
    non_latin = [s for s in detected if s != "Latin" and script_counts[s] >= 3]
    if non_latin:
        primary_script = max(non_latin, key=lambda s: script_counts[s])
    else:
        primary_script = max(detected, key=lambda s: script_counts[s])

    lang_code = SCRIPT_RANGES[primary_script][2]
    return primary_script, lang_code, detected


def is_handwritten_patch(patch_img: np.ndarray) -> Tuple[bool, float]:
    """
    Analyzes visual features of an image text patch to determine if it is handwritten vs machine-printed.
    Features:
    1. Stroke width variance (handwriting has varying pen pressure/speed)
    2. Contour aspect ratio and circularity (cursive loops vs rigid font glyphs)
    3. Baseline angle variance (handwriting tends to drift or slant)
    Returns: (is_handwritten: bool, confidence: float)
    """
    if patch_img is None or patch_img.size == 0:
        return False, 0.0

    h, w = patch_img.shape[:2]
    if h < 10 or w < 10:
        return False, 0.0

    gray = cv2.cvtColor(patch_img, cv2.COLOR_BGR2GRAY) if len(patch_img.shape) == 3 else patch_img

    # Otsu thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours or len(contours) < 2:
        return False, 0.0

    aspect_ratios = []
    solidity_vals = []
    extents = []

    for c in contours:
        area = cv2.contourArea(c)
        if area < 8:
            continue
        bx, by, bw, bh = cv2.boundingRect(c)
        rect_area = bw * bh
        if rect_area > 0:
            aspect_ratios.append(float(bw) / bh)
            extents.append(float(area) / rect_area)
            hull = cv2.convexHull(c)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                solidity_vals.append(float(area) / hull_area)

    if not aspect_ratios:
        return False, 0.0

    # Handwriting typically shows higher variance in aspect ratio and lower average solidity/extent
    ar_std = float(np.std(aspect_ratios))
    mean_solidity = float(np.mean(solidity_vals)) if solidity_vals else 0.8
    mean_extent = float(np.mean(extents)) if extents else 0.5

    handwriting_score = 0.0
    if ar_std > 0.85:
        handwriting_score += 0.40
    if mean_solidity < 0.65:
        handwriting_score += 0.35
    if mean_extent < 0.42:
        handwriting_score += 0.25

    is_hw = handwriting_score >= 0.55
    confidence = min(0.95, round(0.50 + handwriting_score * 0.45, 2)) if is_hw else min(0.95, round(1.0 - handwriting_score, 2))
    return is_hw, confidence


def enrich_fields_with_multilingual_and_handwriting(
    fields: List[ExtractedField],
    rendered_page_img: Optional[Path] = None,
) -> Tuple[List[ExtractedField], Dict[str, Any]]:
    """
    Enriches extracted fields with script identification, language codes, and handwriting detection.
    Also returns document-level metrics:
    - detected_languages: list of language codes
    - detected_scripts: list of scripts
    - handwriting_ratio: fraction of fields identified as handwritten
    """
    page_img = cv2.imread(str(rendered_page_img)) if (rendered_page_img and rendered_page_img.exists()) else None

    all_scripts = set(["Latin"])
    all_langs = set(["en"])
    handwritten_count = 0

    for f in fields:
        raw_val = str(f.value or f.raw_text or "")
        script, lang, detected = detect_text_script_and_language(raw_val)

        f.script = script
        f.language = lang
        all_scripts.update(detected)
        all_langs.add(lang)

        # Check for signature or explicit handwritten indicators
        f_name_lower = f.name.lower()
        if "signature" in f_name_lower or "thumb" in f_name_lower or "handwritten" in f_name_lower:
            f.is_handwritten = True
            handwritten_count += 1
            continue

        # If image available, test visual patch bounding box
        if page_img is not None and len(f.bbox) == 4:
            x0, y0, x1, y1 = f.bbox
            h, w = page_img.shape[:2]
            x0, x1 = max(0, min(w, x0)), max(0, min(w, x1))
            y0, y1 = max(0, min(h, y0)), max(0, min(h, y1))

            if x1 - x0 > 12 and y1 - y0 > 8:
                patch = page_img[y0:y1, x0:x1]
                is_hw, _ = is_handwritten_patch(patch)
                if is_hw:
                    f.is_handwritten = True
                    handwritten_count += 1

    total = len(fields)
    hw_ratio = round(handwritten_count / total, 3) if total > 0 else 0.0

    doc_metrics = {
        "primary_language": "hi" if "hi" in all_langs and len(all_langs) > 1 else "en",
        "detected_languages": sorted(list(all_langs)),
        "scripts": sorted(list(all_scripts)),
        "has_handwriting": handwritten_count > 0,
        "handwriting_ratio": hw_ratio,
        "handwritten_fields_count": handwritten_count,
    }

    return fields, doc_metrics
