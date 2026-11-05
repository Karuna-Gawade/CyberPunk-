"""
Pure validation rule for Indian Permanent Account Number (PAN).
1. Structural regex: ^[A-Z]{5}[0-9]{4}[A-Z]$
2. 4th character entity holder decoding (P=Individual, C=Company, etc.)
3. 5th character surname initial validation for individuals
"""

import re
from typing import List, Optional
from backend.app.models.contracts import (
    EvidenceItem,
    FindingStrength,
    FindingTier,
    RuleResult,
    RuleStatus,
    BBox,
)

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

ENTITY_HOLDER_TYPES = {
    "P": "Individual",
    "C": "Company",
    "H": "Hindu Undivided Family (HUF)",
    "F": "Partnership Firm",
    "A": "Association of Persons (AOP)",
    "T": "Trust",
    "B": "Body of Individuals (BOI)",
    "L": "Local Authority",
    "J": "Artificial Juridical Person",
    "G": "Government Agency",
}


def validate_pan_structure(
    pan_number: str,
    holder_name: Optional[str] = None,
    field_id: str = "F-PAN",
    doc_id: str = "DOC-PAN",
    page: int = 1,
    bbox: Optional[BBox] = None,
) -> RuleResult:
    """
    Pure validation function for PAN structure and surname initial matching.
    Never throws on missing data.
    """
    bbox = bbox or [0, 0, 0, 0]

    if not pan_number:
        return RuleResult(
            rule_id="pan_structure",
            result=RuleStatus.NOT_APPLICABLE,
            field_ids_used=[field_id],
            detail="PAN number is missing or empty.",
        )

    clean_pan = pan_number.strip().upper()

    # 1. Structural regex check
    if not PAN_REGEX.match(clean_pan):
        return RuleResult(
            rule_id="pan_structure",
            result=RuleStatus.FAIL,
            field_ids_used=[field_id],
            detail=f"PAN '{clean_pan}' does not match standard 10-character alphanumeric structure (5 letters, 4 digits, 1 letter).",
            tier=FindingTier.INCONSISTENCY,
            strength=FindingStrength.STRONG,
            title="Invalid PAN format structure",
            evidence=[EvidenceItem(doc_id=doc_id, field_id=field_id, page=page, bbox=bbox)],
            signals=["pan_regex_invalid"],
        )

    fourth_char = clean_pan[3]
    entity_type = ENTITY_HOLDER_TYPES.get(fourth_char, "Unknown Entity Type")

    # 2. Check 4th character validity
    if fourth_char not in ENTITY_HOLDER_TYPES:
        return RuleResult(
            rule_id="pan_structure",
            result=RuleStatus.FAIL,
            field_ids_used=[field_id],
            detail=f"PAN 4th character '{fourth_char}' is not a recognized Income Tax entity type code.",
            tier=FindingTier.INCONSISTENCY,
            strength=FindingStrength.STRONG,
            title="Unrecognized PAN entity type code",
            evidence=[EvidenceItem(doc_id=doc_id, field_id=field_id, page=page, bbox=bbox)],
            signals=["pan_entity_type_invalid"],
        )

    # 3. For individuals (P), verify 5th character matches first letter of surname / last name
    if fourth_char == "P" and holder_name:
        name_parts = [p.strip() for p in re.split(r"[\s,.-]+", holder_name.strip()) if p.strip()]
        if name_parts:
            # Last token is typically surname
            surname = name_parts[-1].upper()
            fifth_char = clean_pan[4]
            if surname and surname[0] != fifth_char:
                return RuleResult(
                    rule_id="pan_structure",
                    result=RuleStatus.FAIL,
                    field_ids_used=[field_id],
                    detail=f"PAN 5th character '{fifth_char}' does not match surname initial '{surname[0]}' from holder name '{holder_name}'.",
                    tier=FindingTier.INCONSISTENCY,
                    strength=FindingStrength.STRONG,
                    title="PAN 5th character surname mismatch",
                    evidence=[EvidenceItem(doc_id=doc_id, field_id=field_id, page=page, bbox=bbox)],
                    signals=["pan_surname_mismatch"],
                )

    return RuleResult(
        rule_id="pan_structure",
        result=RuleStatus.PASS,
        field_ids_used=[field_id],
        detail=f"PAN passed structure check. Entity Type: {entity_type}.",
    )
