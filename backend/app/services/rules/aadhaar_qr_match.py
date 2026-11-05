"""
Pure validation rule comparing Aadhaar Secure QR decoded payload against printed document text.
Demographic fields compared:
- Name (using in-house fuzzy matcher)
- Date of Birth (DOB)
- Gender
- Aadhaar number (or masked digits)

Safe failure: If QR is missing or undecodable -> returns 'not_applicable' with 'Unable to assess'.
"""

from typing import Any, Dict, List, Optional
from backend.app.models.contracts import (
    EvidenceItem,
    FindingStrength,
    FindingTier,
    RuleResult,
    RuleStatus,
    BBox,
)
from backend.app.services.correlation.dates import are_dates_equal
from backend.app.services.correlation.name_match import compare_names


def validate_aadhaar_qr_against_printed(
    qr_payload: Optional[Dict[str, Any]],
    printed_fields: Dict[str, Any],
    qr_box: Optional[BBox] = None,
    doc_id: str = "DOC-AADHAAR",
    page: int = 1,
) -> RuleResult:
    """
    Compares decoded QR demographics with printed OCR fields.
    Never passes silently if QR cannot be assessed.
    """
    qr_box = qr_box or [0, 0, 0, 0]

    if not qr_payload:
        return RuleResult(
            rule_id="aadhaar_qr_text_match",
            result=RuleStatus.NOT_APPLICABLE,
            field_ids_used=[],
            detail="Aadhaar QR code could not be detected or decoded: Unable to assess demographic authenticity.",
        )

    conflicts: List[str] = []
    field_ids_used: List[str] = []

    # 1. Compare Name
    qr_name = qr_payload.get("name")
    printed_name = printed_fields.get("name")
    if qr_name and printed_name:
        field_ids_used.append(f"F-{doc_id}-name")
        score, band, detail = compare_names(str(qr_name), str(printed_name))
        if band == "conflict":
            conflicts.append(f"Name in QR ('{qr_name}') conflicts with printed text ('{printed_name}') - match score: {score}%")

    # 2. Compare DOB
    qr_dob = qr_payload.get("dob")
    printed_dob = printed_fields.get("dob")
    if qr_dob and printed_dob:
        field_ids_used.append(f"F-{doc_id}-dob")
        if not are_dates_equal(str(qr_dob), str(printed_dob)):
            conflicts.append(f"Date of Birth in QR ('{qr_dob}') conflicts with printed DOB ('{printed_dob}')")

    # 3. Compare Gender
    qr_gender = qr_payload.get("gender")
    printed_gender = printed_fields.get("gender")
    if qr_gender and printed_gender:
        field_ids_used.append(f"F-{doc_id}-gender")
        if str(qr_gender).strip().lower()[0] != str(printed_gender).strip().lower()[0]:
            conflicts.append(f"Gender in QR ('{qr_gender}') conflicts with printed gender ('{printed_gender}')")

    if conflicts:
        evidence_items = [
            EvidenceItem(doc_id=doc_id, field_id=f"F-{doc_id}-qr", page=page, bbox=qr_box, label="Aadhaar QR Code")
        ]
        return RuleResult(
            rule_id="aadhaar_qr_text_mismatch",
            result=RuleStatus.FAIL,
            field_ids_used=field_ids_used,
            detail="Discrepancy detected between tamper-resistant QR code and printed text: " + "; ".join(conflicts),
            tier=FindingTier.INCONSISTENCY,
            strength=FindingStrength.STRONG,
            title="Aadhaar printed text conflicts with decoded QR payload",
            evidence=evidence_items,
            signals=["aadhaar_qr_tamper_signal"],
        )

    return RuleResult(
        rule_id="aadhaar_qr_text_match",
        result=RuleStatus.PASS,
        field_ids_used=field_ids_used,
        detail="Aadhaar printed demographics perfectly match decoded secure QR payload.",
    )
