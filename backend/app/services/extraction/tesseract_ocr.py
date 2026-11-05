"""
Tesseract OCR CLI extraction engine.
Executes Tesseract CLI directly with TSV output, parses word boxes and confidences.
Applies OpenCV image preprocessing (grayscale, deskew, denoise).
Renders/processes at 300 DPI and scales boxes by 0.5 to match the stored 150 DPI system.
"""

import csv
import io
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from backend.app.services.tesseract_cli import find_tesseract_binary


def scale_300_to_150_dpi(left: int, top: int, width: int, height: int) -> List[int]:
    """
    Converts Tesseract 300 DPI bounding box (left, top, width, height)
    to the system's standard 150 DPI render coordinate system [x0, y0, x1, y1].
    Scaling factor is exactly 0.5 (150 / 300).
    """
    scale = 0.5
    x0 = int(round(left * scale))
    y0 = int(round(top * scale))
    x1 = int(round((left + width) * scale))
    y1 = int(round((top + height) * scale))
    return [x0, y0, x1, y1]


def preprocess_image_for_ocr(img: np.ndarray) -> np.ndarray:
    """
    Applies standard OpenCV preprocessing:
    1. Grayscale conversion
    2. Mild Gaussian blur denoising
    3. Otsu / adaptive thresholding
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # Denoise
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)

    # Adaptive binarization
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    return thresh


def parse_tesseract_tsv(tsv_content: str) -> List[Dict[str, Any]]:
    """
    Parses Tesseract TSV output into normalized word entries.
    Columns: level, page_num, block_num, par_num, line_num, word_num, left, top, width, height, conf, text
    Ignores rows with conf == -1 or empty text.
    Normalizes confidence from 0-100 to 0.0-1.0.
    """
    words = []
    reader = csv.DictReader(io.StringIO(tsv_content), delimiter="\t")
    for row in reader:
        try:
            conf_val = float(row.get("conf", -1))
            text = (row.get("text") or "").strip()
            if conf_val == -1 or not text:
                continue

            left = int(row["left"])
            top = int(row["top"])
            width = int(row["width"])
            height = int(row["height"])

            norm_conf = max(0.0, min(1.0, round(conf_val / 100.0, 3)))
            bbox_150 = scale_300_to_150_dpi(left, top, width, height)

            words.append({
                "text": text,
                "bbox": bbox_150,
                "confidence": norm_conf,
                "source": "ocr",
                "block_no": int(row.get("block_num", 0)),
                "line_no": int(row.get("line_num", 0)),
                "word_no": int(row.get("word_num", 0)),
            })
        except (ValueError, KeyError):
            continue

    return words


def run_tesseract_on_image(
    image_path: Path,
    psm: int = 6,
    lang: str = "eng",
    timeout_sec: int = 15,
) -> Optional[List[Dict[str, Any]]]:
    """
    Runs Tesseract CLI on an image and returns parsed word boxes at 150 DPI.
    Returns None if Tesseract is unavailable or execution fails.
    """
    binary = find_tesseract_binary()
    if not binary:
        return None

    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return None

        # Preprocess
        processed = preprocess_image_for_ocr(img)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_in:
            tmp_in_path = Path(tmp_in.name)

        try:
            cv2.imwrite(str(tmp_in_path), processed)

            cmd = [
                binary,
                str(tmp_in_path),
                "stdout",
                "--psm",
                str(psm),
                "-l",
                lang,
                "tsv",
            ]
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_sec,
            )
            if proc.returncode != 0:
                return None

            return parse_tesseract_tsv(proc.stdout)
        finally:
            if tmp_in_path.exists():
                tmp_in_path.unlink()

    except Exception:
        return None
