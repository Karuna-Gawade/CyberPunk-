"""
Verhoeff algorithm pure implementation for Indian 12-digit Aadhaar checksum verification.
"""

from typing import List
from backend.app.models.contracts import RuleResult, RuleStatus, FindingTier, FindingStrength, EvidenceItem

D_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

P_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

INV_TABLE = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def compute_verhoeff_checksum(num_str: str) -> int:
    """Computes the Verhoeff check digit for an input string of digits."""
    c = 0
    for i, item in enumerate(reversed(num_str)):
        c = D_TABLE[c][P_TABLE[(i + 1) % 8][int(item)]]
    return INV_TABLE[c]


def validate_verhoeff(num_str: str) -> bool:
    """Validates a complete string of digits against Verhoeff checksum."""
    if not num_str.isdigit():
        return False
    c = 0
    for i, item in enumerate(reversed(num_str)):
        c = D_TABLE[c][P_TABLE[i % 8][int(item)]]
    return c == 0


def validate_aadhaar_number(
    aadhaar_number: str,
    field_id: str = "F-AADHAAR",
    doc_id: str = "DOC-001",
    page: int = 1,
    bbox: List[int] = None,
) -> RuleResult:
    """
    Pure validation function for Aadhaar 12-digit number + Verhoeff checksum.
    Never throws on missing or malformed data.
    """
    bbox = bbox or [0, 0, 0, 0]

    if not aadhaar_number:
        return RuleResult(
            rule_id="aadhaar_verhoeff",
            result=RuleStatus.NOT_APPLICABLE,
            field_ids_used=[field_id],
            detail="Aadhaar number field is missing or empty.",
        )

    # Strip formatting spaces/hyphens
    clean_num = aadhaar_number.replace(" ", "").replace("-", "")

    # Check for masked Aadhaar (e.g. XXXX XXXX 1234)
    if "X" in clean_num.upper() or len(clean_num) != 12 or not clean_num.isdigit():
        if len(clean_num) == 12 and clean_num[:8].upper() == "XXXXXXXX" and clean_num[8:].isdigit():
            # Masked Aadhaar is a valid privacy format; checksum cannot be validated on masked digits
            return RuleResult(
                rule_id="aadhaar_verhoeff",
                result=RuleStatus.PASS,
                field_ids_used=[field_id],
                detail="Aadhaar is in standard masked format (XXXX XXXX ****).",
            )
        return RuleResult(
            rule_id="aadhaar_verhoeff",
            result=RuleStatus.FAIL,
            field_ids_used=[field_id],
            detail=f"Aadhaar number format invalid: expected 12 digits, got {len(clean_num)} characters.",
            tier=FindingTier.INCONSISTENCY,
            strength=FindingStrength.STRONG,
            title="Invalid Aadhaar number length/format",
            evidence=[EvidenceItem(doc_id=doc_id, field_id=field_id, page=page, bbox=bbox)],
            signals=["aadhaar_format_invalid"],
        )

    if not validate_verhoeff(clean_num):
        return RuleResult(
            rule_id="aadhaar_verhoeff",
            result=RuleStatus.FAIL,
            field_ids_used=[field_id],
            detail="Aadhaar number failed Verhoeff checksum verification.",
            tier=FindingTier.INCONSISTENCY,
            strength=FindingStrength.STRONG,
            title="Aadhaar Verhoeff checksum mismatch",
            evidence=[EvidenceItem(doc_id=doc_id, field_id=field_id, page=page, bbox=bbox)],
            signals=["aadhaar_verhoeff_fail"],
        )

    return RuleResult(
        rule_id="aadhaar_verhoeff",
        result=RuleStatus.PASS,
        field_ids_used=[field_id],
        detail="Aadhaar number passed Verhoeff checksum verification.",
    )
