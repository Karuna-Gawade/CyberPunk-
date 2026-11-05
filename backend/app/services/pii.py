"""
PII Masking and Controlled Reveal Service.
Protects sensitive Indian identity data (Aadhaar, PAN) by default.
Unmasking operations are logged in the immutable audit trail.
"""

import re
from typing import Optional


def mask_aadhaar_number(val: str) -> str:
    """Masks Aadhaar number showing only the last 4 digits: XXXX XXXX 1234."""
    if not val:
        return ""
    clean = re.sub(r"[^\dA-Za-z]", "", val)
    if len(clean) >= 4:
        last4 = clean[-4:]
        return f"XXXX XXXX {last4}"
    return "XXXX XXXX XXXX"


def mask_pan_number(val: str) -> str:
    """Masks PAN number showing only the last 4 characters: XXXXX1234F."""
    if not val:
        return ""
    clean = re.sub(r"[^\dA-Za-z]", "", val)
    if len(clean) >= 4:
        last4 = clean[-4:]
        return f"XXXXXX{last4}"
    return "XXXXXXXXXX"


def mask_field_value(field_name: str, value: str) -> str:
    """Applies contextual masking based on field entity type."""
    if not isinstance(value, str):
        value = str(value)

    if field_name in ("aadhaar_number", "aadhaar_num"):
        return mask_aadhaar_number(value)
    elif field_name in ("pan_number", "pan"):
        return mask_pan_number(value)
    return value
