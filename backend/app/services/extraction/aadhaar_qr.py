"""
Aadhaar Secure QR code detector and decoder.
Uses OpenCV QRCodeDetector for bounding box localization, followed by custom
payload parsing (both UIDAI zlib big-integer format and structured format).
Safe failure handling: undecodable QR -> 'Unable to assess', never a silent pass.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
import zlib


def decode_uidai_zlib_payload(raw_bytes: bytes) -> Optional[Dict[str, str]]:
    """
    Attempts zlib decompression of standard UIDAI Secure QR big-integer bytes.
    Extracts demographic fields separated by standard delimiters.
    """
    try:
        decompressed = zlib.decompress(raw_bytes, 16 + zlib.MAX_WBITS)
    except Exception:
        try:
            decompressed = zlib.decompress(raw_bytes)
        except Exception:
            return None

    try:
        # Delimited by 0xFF (255)
        parts = decompressed.split(b"\xff")
        if len(parts) >= 6:
            return {
                "email_mobile_present": parts[0].decode("utf-8", errors="ignore"),
                "reference_id": parts[1].decode("utf-8", errors="ignore"),
                "name": parts[2].decode("utf-8", errors="ignore"),
                "dob": parts[3].decode("utf-8", errors="ignore"),
                "gender": parts[4].decode("utf-8", errors="ignore"),
                "care_of": parts[5].decode("utf-8", errors="ignore") if len(parts) > 5 else "",
                "district": parts[6].decode("utf-8", errors="ignore") if len(parts) > 6 else "",
                "state": parts[7].decode("utf-8", errors="ignore") if len(parts) > 7 else "",
                "pincode": parts[8].decode("utf-8", errors="ignore") if len(parts) > 8 else "",
            }
    except Exception:
        pass
    return None


def parse_qr_text_payload(text: str) -> Optional[Dict[str, str]]:
    """Parses text payloads including standard structured QR formats."""
    text = text.strip()
    if text.startswith("V2:"):
        body = text[3:]
        parts = body.split("|")
        if len(parts) >= 4:
            return {
                "aadhaar_number": parts[0],
                "name": parts[1],
                "dob": parts[2],
                "gender": parts[3],
                "address": parts[4] if len(parts) > 4 else "",
            }
    elif text.startswith("PAN:"):
        body = text[4:]
        parts = body.split("|")
        if len(parts) >= 3:
            return {
                "pan_number": parts[0],
                "name": parts[1],
                "father_name": parts[2],
                "dob": parts[3] if len(parts) > 3 else "",
            }
    return None


def extract_qr_from_image(image_path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[List[int]], bool]:
    """
    Detects and decodes QR codes from rendered page image.
    Returns: (parsed_data_dict, bbox_150_dpi, is_undecodable_flag)
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return None, None, False

    detector = cv2.QRCodeDetector()
    val, points, _ = detector.detectAndDecode(img)

    bbox_150: Optional[List[int]] = None
    if points is not None and len(points) > 0:
        pts = points[0]
        xs = [int(p[0]) for p in pts]
        ys = [int(p[1]) for p in pts]
        bbox_150 = [min(xs), min(ys), max(xs), max(ys)]

    if not val and bbox_150 is not None:
        # Detected QR boundary, but undecodable
        return None, bbox_150, True

    if not val:
        return None, None, False

    # Attempt structured parse
    parsed = parse_qr_text_payload(val)
    if parsed:
        return parsed, bbox_150, False

    # Attempt zlib / byte parse if payload is numeric big-integer string
    if val.isdigit():
        try:
            big_int = int(val)
            byte_len = (big_int.bit_length() + 7) // 8
            raw_bytes = big_int.to_bytes(byte_len, "big")
            zlib_parsed = decode_uidai_zlib_payload(raw_bytes)
            if zlib_parsed:
                return zlib_parsed, bbox_150, False
        except Exception:
            pass

    # Found QR and extracted text, but couldn't parse structured demographic fields
    return {"raw_qr": val}, bbox_150, False
