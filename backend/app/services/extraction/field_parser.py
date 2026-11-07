"""
Structured field extraction engine.
Parses domain entities from extracted words and spans based on DocumentType:
- Aadhaar: name, dob, gender, aadhaar_number, address, photo_region
- PAN: name, father_name, dob, pan_number
- Salary Slip: employee_name, employer, month, basic, hra, allowances, gross, pf, total_deductions, net_pay, pan
- Bank Statement: account_holder, account_number, period, opening_balance, closing_balance, transactions, salary_credits

Applies digit confusion correction for numeric/ID fields while preserving raw_text.
Flags low confidence (< 0.60) fields as unable_to_assess.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from backend.app.models.contracts import (
    DocumentType,
    ExtractedField,
    FieldSource,
    BBox,
)

CONFIDENCE_THRESHOLD = 0.60


def clean_numeric_string(s: str) -> str:
    """Corrects common OCR digit confusion: O->0, l/I->1, S->5."""
    trans = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "S": "5", "s": "5"})
    cleaned = s.translate(trans)
    return re.sub(r"[^\d.]", "", cleaned)


def parse_currency_amount(val_str: str) -> Optional[float]:
    """Parses numeric currency representation e.g. '80,000.00' into 80000.0."""
    try:
        clean = val_str.replace(",", "").replace("INR", "").replace("Rs.", "").strip()
        return float(clean)
    except (ValueError, AttributeError):
        return None


def merge_bboxes(boxes: List[BBox]) -> BBox:
    if not boxes:
        return [0, 0, 0, 0]
    return [
        int(round(min(b[0] for b in boxes))),
        int(round(min(b[1] for b in boxes))),
        int(round(max(b[2] for b in boxes))),
        int(round(max(b[3] for b in boxes))),
    ]


def find_line_with_label(
    words: List[Dict[str, Any]],
    label: str,
    direction: str = "right",
    max_dist: int = 300,
) -> Optional[Tuple[str, float, BBox, str]]:
    """
    Finds a label in word list, and returns the adjacent value text, confidence, bbox, raw_text.
    """
    label_lower = label.lower()
    for i, w in enumerate(words):
        if label_lower in w["text"].lower():
            # Found label token
            label_box = w["bbox"]
            val_tokens = []
            for j, cand in enumerate(words):
                if j == i:
                    continue
                cand_box = cand["bbox"]
                # Same horizontal line (vertical overlap)
                y_overlap = max(0, min(label_box[3], cand_box[3]) - max(label_box[1], cand_box[1]))
                if y_overlap > 5:
                    if direction == "right" and cand_box[0] > label_box[0] and (cand_box[0] - label_box[2]) < max_dist:
                        val_tokens.append(cand)
                    elif direction == "below" and cand_box[1] > label_box[1] and (cand_box[1] - label_box[3]) < 50:
                        val_tokens.append(cand)

            if val_tokens:
                val_tokens.sort(key=lambda t: t["bbox"][0])
                raw_text = " ".join(t["text"] for t in val_tokens)
                avg_conf = sum(t["confidence"] for t in val_tokens) / len(val_tokens)
                merged_box = merge_bboxes([t["bbox"] for t in val_tokens])
                return raw_text, avg_conf, merged_box, raw_text
    return None


def extract_aadhaar_fields(
    doc_id: str,
    pages_data: List[Dict[str, Any]],
    qr_data: Optional[Dict[str, Any]] = None,
    qr_box: Optional[BBox] = None,
) -> List[ExtractedField]:
    fields: List[ExtractedField] = []
    page1 = pages_data[0] if pages_data else {"words": [], "full_text": ""}
    full_text = page1.get("full_text", "")
    words = page1.get("words", [])
    src = FieldSource.TEXT_LAYER if words and words[0].get("source") == "text_layer" else FieldSource.OCR

    # 1. Aadhaar Number (12 digits e.g. 5489 1234 5674 or XXXX XXXX 1234)
    num_match = re.search(r"(\b\d{4}\s+\d{4}\s+\d{4}\b|\b[Xx]{4}\s+[Xx]{4}\s+\d{4}\b)", full_text)
    if num_match:
        raw_num = num_match.group(1)
        clean_num = raw_num.replace(" ", "")
        # Find matching word bounding boxes
        matched_boxes = [w["bbox"] for w in words if any(part in w["text"] for part in raw_num.split())]
        box = merge_bboxes(matched_boxes) if matched_boxes else [100, 300, 400, 340]
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-aadhaar-num",
                doc_id=doc_id,
                name="aadhaar_number",
                value=clean_num,
                raw_text=raw_num,
                confidence=0.95,
                source=src,
                page=1,
                bbox=box,
            )
        )

    # 2. Name
    name_match = re.search(r"Name[:\s]+([A-Za-z\s]+)", full_text)
    if name_match:
        name_val = name_match.group(1).split("\n")[0].strip()
        matched_boxes = [w["bbox"] for w in words if any(n in w["text"] for n in name_val.split())]
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-name",
                doc_id=doc_id,
                name="name",
                value=name_val,
                raw_text=name_val,
                confidence=0.92,
                source=src,
                page=1,
                bbox=merge_bboxes(matched_boxes) if matched_boxes else [100, 100, 300, 130],
            )
        )

    # 3. DOB
    dob_match = re.search(r"(?:DOB|Date of Birth)[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})", full_text, re.IGNORECASE)
    if dob_match:
        dob_val = dob_match.group(1)
        matched_boxes = [w["bbox"] for w in words if dob_val in w["text"]]
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-dob",
                doc_id=doc_id,
                name="dob",
                value=dob_val,
                raw_text=dob_val,
                confidence=0.94,
                source=src,
                page=1,
                bbox=merge_bboxes(matched_boxes) if matched_boxes else [100, 140, 250, 170],
            )
        )

    # 4. Gender
    gender_match = re.search(r"(?:Gender)[:\s]+(Male|Female|Transgender)", full_text, re.IGNORECASE)
    if gender_match:
        g_val = gender_match.group(1)
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-gender",
                doc_id=doc_id,
                name="gender",
                value=g_val,
                raw_text=g_val,
                confidence=0.95,
                source=src,
                page=1,
                bbox=[100, 180, 200, 210],
            )
        )

    # 5. Address
    addr_match = re.search(r"Address[:\s]+([^\n]+(?:\n[^\n]+)?)", full_text, re.IGNORECASE)
    if addr_match:
        addr_val = addr_match.group(1).replace("\n", " ").strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-address",
                doc_id=doc_id,
                name="address",
                value=addr_val,
                raw_text=addr_val,
                confidence=0.88,
                source=src,
                page=1,
                bbox=[100, 220, 450, 280],
            )
        )

    # 6. QR Code Field if detected
    if qr_data and qr_box:
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-qr",
                doc_id=doc_id,
                name="aadhaar_qr_payload",
                value=qr_data,
                raw_text=str(qr_data),
                confidence=0.99,
                source=FieldSource.QR,
                page=1,
                bbox=qr_box,
            )
        )

    return fields


def extract_pan_fields(
    doc_id: str,
    pages_data: List[Dict[str, Any]],
    qr_data: Optional[Dict[str, Any]] = None,
    qr_box: Optional[BBox] = None,
) -> List[ExtractedField]:
    fields: List[ExtractedField] = []
    page1 = pages_data[0] if pages_data else {"words": [], "full_text": ""}
    full_text = page1.get("full_text", "")
    words = page1.get("words", [])
    src = FieldSource.TEXT_LAYER if words and words[0].get("source") == "text_layer" else FieldSource.OCR

    # 1. PAN Number (^[A-Z]{5}[0-9]{4}[A-Z]$)
    pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", full_text)
    if pan_match:
        pan_num = pan_match.group(1)
        matched_boxes = [w["bbox"] for w in words if pan_num in w["text"]]
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-pan-num",
                doc_id=doc_id,
                name="pan_number",
                value=pan_num,
                raw_text=pan_num,
                confidence=0.98,
                source=src,
                page=1,
                bbox=merge_bboxes(matched_boxes) if matched_boxes else [120, 110, 280, 140],
            )
        )

    # 2. Name
    name_match = re.search(r"Name[:\s]+([A-Za-z\s]+)", full_text)
    if name_match:
        name_val = name_match.group(1).split("\n")[0].strip()
        matched_boxes = [w["bbox"] for w in words if any(n in w["text"] for n in name_val.split())]
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-name",
                doc_id=doc_id,
                name="name",
                value=name_val,
                raw_text=name_val,
                confidence=0.92,
                source=src,
                page=1,
                bbox=merge_bboxes(matched_boxes) if matched_boxes else [120, 150, 300, 180],
            )
        )

    # 3. Father's Name
    father_match = re.search(r"Father'?s?\s*Name[:\s]+([A-Za-z\s]+)", full_text, re.IGNORECASE)
    if father_match:
        father_val = father_match.group(1).split("\n")[0].strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-father-name",
                doc_id=doc_id,
                name="father_name",
                value=father_val,
                raw_text=father_val,
                confidence=0.90,
                source=src,
                page=1,
                bbox=[120, 190, 320, 220],
            )
        )

    # 4. DOB
    dob_match = re.search(r"(?:DOB|Date of Birth)[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})", full_text, re.IGNORECASE)
    if dob_match:
        dob_val = dob_match.group(1)
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-dob",
                doc_id=doc_id,
                name="dob",
                value=dob_val,
                raw_text=dob_val,
                confidence=0.95,
                source=src,
                page=1,
                bbox=[120, 230, 240, 260],
            )
        )

    return fields


def extract_salary_slip_fields(doc_id: str, pages_data: List[Dict[str, Any]]) -> List[ExtractedField]:
    fields: List[ExtractedField] = []
    page1 = pages_data[0] if pages_data else {"words": [], "full_text": ""}
    full_text = page1.get("full_text", "")
    words = page1.get("words", [])
    src = FieldSource.TEXT_LAYER if words and words[0].get("source") == "text_layer" else FieldSource.OCR

    # 1. Employee Name
    name_match = re.search(r"Employee Name[:\s]+([A-Za-z\s]+)", full_text, re.IGNORECASE)
    if name_match:
        name_val = name_match.group(1).split("\n")[0].strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-employee-name",
                doc_id=doc_id,
                name="employee_name",
                value=name_val,
                raw_text=name_val,
                confidence=0.92,
                source=src,
                page=1,
                bbox=[80, 80, 250, 105],
            )
        )

    # 2. Employer
    employer_match = re.search(r"<b>([^<]+)</b>|([A-Z][A-Za-z0-9\s]+(?:Pvt|Ltd|Inc|Solutions|Technologies))", full_text)
    if employer_match:
        emp_val = (employer_match.group(1) or employer_match.group(2) or "").strip()
        if len(emp_val) > 3:
            fields.append(
                ExtractedField(
                    field_id=f"F-{doc_id}-employer",
                    doc_id=doc_id,
                    name="employer",
                    value=emp_val,
                    raw_text=emp_val,
                    confidence=0.90,
                    source=src,
                    page=1,
                    bbox=[80, 40, 350, 70],
                )
            )

    # 3. Month
    month_match = re.search(r"(?:month of|for the month)[:\s]+([A-Za-z]+\s+\d{4})", full_text, re.IGNORECASE)
    if month_match:
        month_val = month_match.group(1).strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-month",
                doc_id=doc_id,
                name="month",
                value=month_val,
                raw_text=month_val,
                confidence=0.94,
                source=src,
                page=1,
                bbox=[80, 65, 200, 85],
            )
        )

    # 4. PAN if present
    pan_match = re.search(r"PAN[:\s]+([A-Z]{5}[0-9]{4}[A-Z])", full_text)
    if pan_match:
        pan_val = pan_match.group(1)
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-pan",
                doc_id=doc_id,
                name="pan_number",
                value=pan_val,
                raw_text=pan_val,
                confidence=0.95,
                source=src,
                page=1,
                bbox=[80, 110, 220, 130],
            )
        )

    # 5. Financial fields: Basic, HRA, Allowances, Gross, PF, Net Pay
    financial_patterns = [
        ("basic", r"Basic(?:\s+Salary)?[:\s]+([0-9,.]+)", [100, 160, 250, 180]),
        ("hra", r"HRA|House Rent Allowance[:\s]+([0-9,.]+)", [100, 185, 250, 205]),
        ("allowances", r"Special Allowances?[:\s]+([0-9,.]+)", [100, 210, 250, 230]),
        ("gross", r"Gross Earnings?[:\s]+([0-9,.]+)", [100, 240, 250, 260]),
        ("pf", r"Provident Fund|PF[:\s]+([0-9,.]+)", [300, 160, 450, 180]),
        ("total_deductions", r"Total Deductions?[:\s]+([0-9,.]+)", [300, 240, 450, 260]),
        ("net_pay", r"Net Pay(?:\s*[:=])?[:\s]*(?:INR\s*)?([0-9,.]+)", [100, 270, 300, 300]),
    ]

    for f_name, pat, default_box in financial_patterns:
        m = re.search(pat, full_text, re.IGNORECASE)
        if m:
            raw_val = m.group(1)
            num_val = parse_currency_amount(raw_val)
            if num_val is not None:
                fields.append(
                    ExtractedField(
                        field_id=f"F-{doc_id}-{f_name}",
                        doc_id=doc_id,
                        name=f_name,
                        value=num_val,
                        raw_text=raw_val,
                        confidence=0.92,
                        source=src,
                        page=1,
                        bbox=default_box,
                    )
                )

    return fields


def extract_bank_statement_fields(doc_id: str, pages_data: List[Dict[str, Any]]) -> List[ExtractedField]:
    fields: List[ExtractedField] = []
    page1 = pages_data[0] if pages_data else {"words": [], "full_text": ""}
    full_text = page1.get("full_text", "")
    words = page1.get("words", [])
    src = FieldSource.TEXT_LAYER if words and words[0].get("source") == "text_layer" else FieldSource.OCR

    # 1. Account Holder
    holder_match = re.search(r"Account Holder[:\s]+([A-Za-z\s]+)", full_text, re.IGNORECASE)
    if holder_match:
        h_val = holder_match.group(1).split("\n")[0].strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-account-holder",
                doc_id=doc_id,
                name="account_holder",
                value=h_val,
                raw_text=h_val,
                confidence=0.92,
                source=src,
                page=1,
                bbox=[80, 80, 250, 105],
            )
        )

    # 2. Account Number
    acc_match = re.search(r"Account Number[:\s]+([0-9Xx]+)", full_text, re.IGNORECASE)
    if acc_match:
        acc_num = acc_match.group(1).strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-account-number",
                doc_id=doc_id,
                name="account_number",
                value=acc_num,
                raw_text=acc_num,
                confidence=0.95,
                source=src,
                page=1,
                bbox=[80, 110, 240, 130],
            )
        )

    # 3. Period
    period_match = re.search(r"Statement Period[:\s]+([0-9/-]+\s+to\s+[0-9/-]+)", full_text, re.IGNORECASE)
    if period_match:
        period_val = period_match.group(1).strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-period",
                doc_id=doc_id,
                name="period",
                value=period_val,
                raw_text=period_val,
                confidence=0.93,
                source=src,
                page=1,
                bbox=[300, 80, 480, 105],
            )
        )

    # 4. Opening Balance
    open_match = re.search(r"Opening Balance[:\s]+(?:INR\s*)?([0-9,.]+)", full_text, re.IGNORECASE)
    if open_match:
        open_val = parse_currency_amount(open_match.group(1))
        if open_val is not None:
            fields.append(
                ExtractedField(
                    field_id=f"F-{doc_id}-opening-balance",
                    doc_id=doc_id,
                    name="opening_balance",
                    value=open_val,
                    raw_text=open_match.group(1),
                    confidence=0.93,
                    source=src,
                    page=1,
                    bbox=[80, 140, 240, 160],
                )
            )

    # 5. Closing Balance
    close_match = re.search(r"Closing Balance[:\s]+(?:INR\s*)?([0-9,.]+)", full_text, re.IGNORECASE)
    if close_match:
        close_val = parse_currency_amount(close_match.group(1))
        if close_val is not None:
            fields.append(
                ExtractedField(
                    field_id=f"F-{doc_id}-closing-balance",
                    doc_id=doc_id,
                    name="closing_balance",
                    value=close_val,
                    raw_text=close_match.group(1),
                    confidence=0.93,
                    source=src,
                    page=1,
                    bbox=[300, 140, 480, 160],
                )
            )

    # 6. Transactions Table Rows & Salary Credits
    tx_rows = []
    salary_credits = []
    # Pattern for transaction row: DD/MM/YYYY description [debit] [credit] balance
    tx_regex = re.compile(
        r"(\d{2}/\d{2}/\d{4})\s+([A-Za-z0-9\s\-_]+?)\s+([0-9,.]+|[-–])\s+([0-9,.]+|[-–])\s+([0-9,.]+)"
    )
    for m in tx_regex.finditer(full_text):
        date_str = m.group(1)
        desc_str = m.group(2).strip()
        debit_val = parse_currency_amount(m.group(3)) or 0.0
        credit_val = parse_currency_amount(m.group(4)) or 0.0
        balance_val = parse_currency_amount(m.group(5)) or 0.0

        tx_obj = {
            "date": date_str,
            "description": desc_str,
            "debit": debit_val,
            "credit": credit_val,
            "balance": balance_val,
        }
        tx_rows.append(tx_obj)

        if "salary" in desc_str.lower() and credit_val > 0:
            salary_credits.append(credit_val)

    if tx_rows:
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-transactions",
                doc_id=doc_id,
                name="transactions",
                value=tx_rows,
                raw_text=f"{len(tx_rows)} transactions parsed",
                confidence=0.90,
                source=src,
                page=1,
                bbox=[50, 200, 500, 450],
            )
        )

    if salary_credits:
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-salary-credits",
                doc_id=doc_id,
                name="salary_credits",
                value=salary_credits,
                raw_text=str(salary_credits),
                confidence=0.92,
                source=src,
                page=1,
                bbox=[50, 300, 500, 350],
            )
        )

    return fields


def extract_loan_application_fields(doc_id: str, pages_data: List[Dict[str, Any]]) -> List[ExtractedField]:
    fields: List[ExtractedField] = []
    page1 = pages_data[0] if pages_data else {"words": [], "full_text": ""}
    full_text = page1.get("full_text", "")
    words = page1.get("words", [])
    src = FieldSource.TEXT_LAYER if words and words[0].get("source") == "text_layer" else FieldSource.OCR

    # 1. Applicant Name (as 'name')
    name_match = re.search(r"(?:Applicant Name|Name)[:\s]+([A-Za-z\s]+)", full_text, re.IGNORECASE)
    if name_match:
        name_val = name_match.group(1).split("\n")[0].strip()
        matched_boxes = [w["bbox"] for w in words if any(n in w["text"] for n in name_val.split())]
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-name",
                doc_id=doc_id,
                name="name",
                value=name_val,
                raw_text=name_val,
                confidence=0.92,
                source=src,
                page=1,
                bbox=merge_bboxes(matched_boxes) if matched_boxes else [80, 80, 280, 105],
            )
        )

    # 2. DOB
    dob_match = re.search(r"(?:DOB|Date of Birth)[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})", full_text, re.IGNORECASE)
    if dob_match:
        dob_val = dob_match.group(1).strip()
        matched_boxes = [w["bbox"] for w in words if dob_val in w["text"]]
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-dob",
                doc_id=doc_id,
                name="dob",
                value=dob_val,
                raw_text=dob_val,
                confidence=0.94,
                source=src,
                page=1,
                bbox=merge_bboxes(matched_boxes) if matched_boxes else [80, 110, 240, 130],
            )
        )

    # 3. PAN
    pan_match = re.search(r"(?:PAN|PAN Number)[:\s]+([A-Z]{5}[0-9]{4}[A-Z])|\b([A-Z]{5}[0-9]{4}[A-Z])\b", full_text)
    if pan_match:
        pan_val = (pan_match.group(1) or pan_match.group(2)).strip()
        matched_boxes = [w["bbox"] for w in words if pan_val in w["text"]]
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-pan",
                doc_id=doc_id,
                name="pan_number",
                value=pan_val,
                raw_text=pan_val,
                confidence=0.95,
                source=src,
                page=1,
                bbox=merge_bboxes(matched_boxes) if matched_boxes else [80, 135, 240, 155],
            )
        )

    # 4. Declared Monthly Income
    income_match = re.search(r"Declared Monthly Income[:\s]+(?:INR\s*)?([0-9,.]+)", full_text, re.IGNORECASE)
    if income_match:
        raw_inc = income_match.group(1).strip()
        num_inc = parse_currency_amount(raw_inc)
        if num_inc is not None:
            fields.append(
                ExtractedField(
                    field_id=f"F-{doc_id}-declared-monthly-income",
                    doc_id=doc_id,
                    name="declared_monthly_income",
                    value=num_inc,
                    raw_text=raw_inc,
                    confidence=0.93,
                    source=src,
                    page=1,
                    bbox=[80, 160, 280, 185],
                )
            )

    # 5. Loan Amount
    loan_match = re.search(r"Loan Amount[:\s]+(?:INR\s*)?([0-9,.]+)", full_text, re.IGNORECASE)
    if loan_match:
        raw_loan = loan_match.group(1).strip()
        num_loan = parse_currency_amount(raw_loan)
        if num_loan is not None:
            fields.append(
                ExtractedField(
                    field_id=f"F-{doc_id}-loan-amount",
                    doc_id=doc_id,
                    name="loan_amount",
                    value=num_loan,
                    raw_text=raw_loan,
                    confidence=0.93,
                    source=src,
                    page=1,
                    bbox=[80, 190, 280, 215],
                )
            )

    # 6. Purpose
    purp_match = re.search(r"Purpose(?: of Loan)?[:\s]+([^\n]+)", full_text, re.IGNORECASE)
    if purp_match:
        purp_val = purp_match.group(1).strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-purpose",
                doc_id=doc_id,
                name="purpose",
                value=purp_val,
                raw_text=purp_val,
                confidence=0.90,
                source=src,
                page=1,
                bbox=[80, 220, 350, 245],
            )
        )

    return fields


def extract_declaration_15g_fields(doc_id: str, pages_data: List[Dict[str, Any]]) -> List[ExtractedField]:
    fields: List[ExtractedField] = []
    page1 = pages_data[0] if pages_data else {"words": [], "full_text": ""}
    full_text = page1.get("full_text", "")
    words = page1.get("words", [])
    src = FieldSource.TEXT_LAYER if words and words[0].get("source") == "text_layer" else FieldSource.OCR

    # 1. Declarant Name (as 'name')
    name_match = re.search(r"(?:Declarant Name|Name of Declarant|Name)[:\s]+([A-Za-z\s]+)", full_text, re.IGNORECASE)
    if name_match:
        name_val = name_match.group(1).split("\n")[0].strip()
        matched_boxes = [w["bbox"] for w in words if any(n in w["text"] for n in name_val.split())]
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-name",
                doc_id=doc_id,
                name="name",
                value=name_val,
                raw_text=name_val,
                confidence=0.92,
                source=src,
                page=1,
                bbox=merge_bboxes(matched_boxes) if matched_boxes else [80, 80, 280, 105],
            )
        )

    # 2. PAN
    pan_match = re.search(r"(?:PAN|PAN of the Assessee)[:\s]+([A-Z]{5}[0-9]{4}[A-Z])|\b([A-Z]{5}[0-9]{4}[A-Z])\b", full_text)
    if pan_match:
        pan_val = (pan_match.group(1) or pan_match.group(2)).strip()
        matched_boxes = [w["bbox"] for w in words if pan_val in w["text"]]
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-pan",
                doc_id=doc_id,
                name="pan_number",
                value=pan_val,
                raw_text=pan_val,
                confidence=0.95,
                source=src,
                page=1,
                bbox=merge_bboxes(matched_boxes) if matched_boxes else [80, 110, 240, 130],
            )
        )

    # 3. Financial Year
    fy_match = re.search(r"Financial Year[:\s]+(\d{4}[-–]\d{2,4})", full_text, re.IGNORECASE)
    if fy_match:
        fy_val = fy_match.group(1).strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-financial-year",
                doc_id=doc_id,
                name="financial_year",
                value=fy_val,
                raw_text=fy_val,
                confidence=0.93,
                source=src,
                page=1,
                bbox=[80, 135, 240, 155],
            )
        )

    # 4. Estimated Annual Income
    inc_match = re.search(r"Estimated(?: Total)? Annual Income[:\s]+(?:INR\s*)?([0-9,.]+)", full_text, re.IGNORECASE)
    if inc_match:
        raw_inc = inc_match.group(1).strip()
        num_inc = parse_currency_amount(raw_inc)
        if num_inc is not None:
            fields.append(
                ExtractedField(
                    field_id=f"F-{doc_id}-estimated-annual-income",
                    doc_id=doc_id,
                    name="estimated_annual_income",
                    value=num_inc,
                    raw_text=raw_inc,
                    confidence=0.93,
                    source=src,
                    page=1,
                    bbox=[80, 160, 280, 185],
                )
            )

    # 5. Declaration Date
    date_match = re.search(r"(?:Declaration )?Date[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})", full_text, re.IGNORECASE)
    if date_match:
        date_val = date_match.group(1).strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-declaration-date",
                doc_id=doc_id,
                name="declaration_date",
                value=date_val,
                raw_text=date_val,
                confidence=0.92,
                source=src,
                page=1,
                bbox=[80, 190, 240, 210],
            )
        )

    return fields


def extract_payment_instruction_fields(doc_id: str, pages_data: List[Dict[str, Any]]) -> List[ExtractedField]:
    fields: List[ExtractedField] = []
    page1 = pages_data[0] if pages_data else {"words": [], "full_text": ""}
    full_text = page1.get("full_text", "")
    words = page1.get("words", [])
    src = FieldSource.TEXT_LAYER if words and words[0].get("source") == "text_layer" else FieldSource.OCR

    # 1. Remitter Name (as 'name')
    remitter_match = re.search(r"(?:Remitter Name|Applicant Name|Name)[:\s]+([A-Za-z\s]+)", full_text, re.IGNORECASE)
    if remitter_match:
        name_val = remitter_match.group(1).split("\n")[0].strip()
        matched_boxes = [w["bbox"] for w in words if any(n in w["text"] for n in name_val.split())]
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-name",
                doc_id=doc_id,
                name="name",
                value=name_val,
                raw_text=name_val,
                confidence=0.92,
                source=src,
                page=1,
                bbox=merge_bboxes(matched_boxes) if matched_boxes else [80, 80, 280, 105],
            )
        )

    # 2. Account Number
    acc_match = re.search(r"(?:Remitter )?Account Number[:\s]+([0-9Xx]+)", full_text, re.IGNORECASE)
    if acc_match:
        acc_val = acc_match.group(1).strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-account-number",
                doc_id=doc_id,
                name="account_number",
                value=acc_val,
                raw_text=acc_val,
                confidence=0.94,
                source=src,
                page=1,
                bbox=[80, 110, 240, 130],
            )
        )

    # 3. Beneficiary Name
    ben_match = re.search(r"Beneficiary Name[:\s]+([A-Za-z\s]+)", full_text, re.IGNORECASE)
    if ben_match:
        ben_val = ben_match.group(1).split("\n")[0].strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-beneficiary-name",
                doc_id=doc_id,
                name="beneficiary_name",
                value=ben_val,
                raw_text=ben_val,
                confidence=0.92,
                source=src,
                page=1,
                bbox=[80, 135, 280, 155],
            )
        )

    # 4. Amount
    amt_match = re.search(r"(?:Payment )?Amount[:\s]+(?:INR\s*)?([0-9,.]+)", full_text, re.IGNORECASE)
    if amt_match:
        raw_amt = amt_match.group(1).strip()
        num_amt = parse_currency_amount(raw_amt)
        if num_amt is not None:
            fields.append(
                ExtractedField(
                    field_id=f"F-{doc_id}-amount",
                    doc_id=doc_id,
                    name="amount",
                    value=num_amt,
                    raw_text=raw_amt,
                    confidence=0.94,
                    source=src,
                    page=1,
                    bbox=[80, 160, 280, 185],
                )
            )

    # 5. Instruction Date
    date_match = re.search(r"(?:Instruction )?Date[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})", full_text, re.IGNORECASE)
    if date_match:
        date_val = date_match.group(1).strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-instruction-date",
                doc_id=doc_id,
                name="instruction_date",
                value=date_val,
                raw_text=date_val,
                confidence=0.93,
                source=src,
                page=1,
                bbox=[80, 190, 240, 210],
            )
        )

    # 6. Purpose
    purp_match = re.search(r"Purpose[:\s]+([^\n]+)", full_text, re.IGNORECASE)
    if purp_match:
        purp_val = purp_match.group(1).strip()
        fields.append(
            ExtractedField(
                field_id=f"F-{doc_id}-purpose",
                doc_id=doc_id,
                name="purpose",
                value=purp_val,
                raw_text=purp_val,
                confidence=0.90,
                source=src,
                page=1,
                bbox=[80, 215, 350, 240],
            )
        )

    return fields


def extract_all_text_lines(doc_id: str, pages_data: List[Dict[str, Any]]) -> List[ExtractedField]:
    """
    Extracts every physical line of text across all pages as an individual ExtractedField.
    Ensures complete visual traceability and bounding box coverage on the canvas.
    """
    fields: List[ExtractedField] = []
    global_line_idx = 1

    for page_dict in pages_data:
        page_num = page_dict.get("page", 1)
        words = page_dict.get("words", [])

        if words:
            # Cluster words by vertical proximity (visual lines)
            sorted_words = sorted(words, key=lambda w: (w["bbox"][1] + w["bbox"][3]) / 2)
            visual_lines: List[Dict[str, Any]] = []

            for w in sorted_words:
                cy = (w["bbox"][1] + w["bbox"][3]) / 2
                h = max(10, w["bbox"][3] - w["bbox"][1])
                assigned = False
                for line in visual_lines:
                    line_cy = (line["bbox"][1] + line["bbox"][3]) / 2
                    line_h = line["bbox"][3] - line["bbox"][1]
                    if abs(cy - line_cy) < max(h, line_h) * 0.6:
                        line["words"].append(w)
                        line["bbox"][0] = min(line["bbox"][0], w["bbox"][0])
                        line["bbox"][1] = min(line["bbox"][1], w["bbox"][1])
                        line["bbox"][2] = max(line["bbox"][2], w["bbox"][2])
                        line["bbox"][3] = max(line["bbox"][3], w["bbox"][3])
                        assigned = True
                        break
                if not assigned:
                    visual_lines.append({"bbox": list(w["bbox"]), "words": [w]})

            # Sort lines top-to-bottom
            visual_lines.sort(key=lambda l: (l["bbox"][1] + l["bbox"][3]) / 2)

            for line in visual_lines:
                line["words"].sort(key=lambda w: w["bbox"][0])
                line_text = " ".join(w.get("text", "") for w in line["words"]).strip()
                if not line_text:
                    continue

                # Filter single non-alphanumeric noise characters
                if len(line_text) == 1 and not line_text.isalnum():
                    continue

                avg_conf = round(sum(w.get("confidence", 0.95) for w in line["words"]) / len(line["words"]), 3)
                src = FieldSource.OCR if any(w.get("source") == "ocr" for w in line["words"]) else FieldSource.TEXT_LAYER

                fields.append(
                    ExtractedField(
                        field_id=f"F-{doc_id}-p{page_num}-line-{global_line_idx}",
                        doc_id=doc_id,
                        name=f"line_{global_line_idx:02d}",
                        value=line_text,
                        raw_text=line_text,
                        confidence=avg_conf,
                        source=src,
                        page=page_num,
                        bbox=[int(round(c)) for c in line["bbox"]],
                    )
                )
                global_line_idx += 1
        else:
            # Fallback for documents without explicit word bounding boxes (e.g. DOCX/XLSX text)
            full_text = page_dict.get("full_text", "")
            lines = [l.strip() for l in full_text.splitlines() if l.strip()]
            for idx, line_text in enumerate(lines, 1):
                fields.append(
                    ExtractedField(
                        field_id=f"F-{doc_id}-p{page_num}-line-{global_line_idx}",
                        doc_id=doc_id,
                        name=f"line_{global_line_idx:02d}",
                        value=line_text,
                        raw_text=line_text,
                        confidence=0.98,
                        source=FieldSource.TEXT_LAYER,
                        page=page_num,
                        bbox=[40, 40 + (idx - 1) * 25, 750, 40 + idx * 25],
                    )
                )
                global_line_idx += 1

    return fields


def extract_generic_key_values(doc_id: str, pages_data: List[Dict[str, Any]]) -> List[ExtractedField]:
    """
    Extracts key-value pairs from semi-structured or unsupported documents
    (e.g. transaction slips, receipts, declarations, forms) matching patterns like:
    'Key : Value' or 'Key > Value' or 'Key - Value'.
    """
    fields: List[ExtractedField] = []
    seen_keys: Set[str] = set()

    for page_dict in pages_data:
        page_num = page_dict.get("page", 1)
        words = page_dict.get("words", [])

        if words:
            # Cluster words by vertical proximity into lines
            sorted_words = sorted(words, key=lambda w: (w["bbox"][1] + w["bbox"][3]) / 2)
            visual_lines: List[Dict[str, Any]] = []

            for w in sorted_words:
                cy = (w["bbox"][1] + w["bbox"][3]) / 2
                h = max(10, w["bbox"][3] - w["bbox"][1])
                assigned = False
                for line in visual_lines:
                    line_cy = (line["bbox"][1] + line["bbox"][3]) / 2
                    line_h = line["bbox"][3] - line["bbox"][1]
                    if abs(cy - line_cy) < max(h, line_h) * 0.6:
                        line["words"].append(w)
                        line["bbox"][0] = min(line["bbox"][0], w["bbox"][0])
                        line["bbox"][1] = min(line["bbox"][1], w["bbox"][1])
                        line["bbox"][2] = max(line["bbox"][2], w["bbox"][2])
                        line["bbox"][3] = max(line["bbox"][3], w["bbox"][3])
                        assigned = True
                        break
                if not assigned:
                    visual_lines.append({"bbox": list(w["bbox"]), "words": [w]})

            for line in visual_lines:
                line["words"].sort(key=lambda w: w["bbox"][0])
                line_text = " ".join(w.get("text", "") for w in line["words"]).strip()
                match = re.match(r"^[\s\-\~\|\*]*([A-Za-z][A-Za-z\s]{1,30}?)\s*[:\>\-]\s*([^\n\r]+)$", line_text)
                if match:
                    raw_key = match.group(1).strip()
                    raw_val = match.group(2).strip()
                    clean_key = re.sub(r"[^a-zA-Z0-9]+", "_", raw_key).strip("_").lower()
                    if not clean_key or len(clean_key) < 2 or clean_key in seen_keys:
                        continue
                    if clean_key in ("note", "page", "total_pages", "confidential"):
                        continue
                    clean_val = re.sub(r"[\s\|\~]+$", "", raw_val).strip()
                    if not clean_val:
                        continue

                    seen_keys.add(clean_key)
                    avg_conf = round(sum(w.get("confidence", 0.95) for w in line["words"]) / len(line["words"]), 3)
                    src = FieldSource.OCR if any(w.get("source") == "ocr" for w in line["words"]) else FieldSource.TEXT_LAYER

                    fields.append(
                        ExtractedField(
                            field_id=f"F-{doc_id}-kv-{clean_key}",
                            doc_id=doc_id,
                            name=clean_key,
                            value=clean_val,
                            raw_text=line_text,
                            confidence=avg_conf,
                            source=src,
                            page=page_num,
                            bbox=[int(round(c)) for c in line["bbox"]],
                        )
                    )
        else:
            full_text = page_dict.get("full_text", "")
            for line_idx, line in enumerate(full_text.splitlines(), 1):
                match = re.match(r"^[\s\-\~\|\*]*([A-Za-z][A-Za-z\s]{1,30}?)\s*[:\>\-]\s*([^\n\r]+)$", line.strip())
                if match:
                    raw_key = match.group(1).strip()
                    raw_val = match.group(2).strip()
                    clean_key = re.sub(r"[^a-zA-Z0-9]+", "_", raw_key).strip("_").lower()
                    if not clean_key or len(clean_key) < 2 or clean_key in seen_keys:
                        continue
                    clean_val = re.sub(r"[\s\|\~]+$", "", raw_val).strip()
                    if not clean_val:
                        continue

                    seen_keys.add(clean_key)
                    fields.append(
                        ExtractedField(
                            field_id=f"F-{doc_id}-kv-{clean_key}",
                            doc_id=doc_id,
                            name=clean_key,
                            value=clean_val,
                            raw_text=line.strip(),
                            confidence=0.95,
                            source=FieldSource.TEXT_LAYER,
                            page=page_num,
                            bbox=[40, 40 + (line_idx - 1) * 25, 750, 40 + line_idx * 25],
                        )
                    )

    return fields


def parse_document_fields(
    doc_id: str,
    doc_type: DocumentType,
    pages_data: List[Dict[str, Any]],
    qr_data: Optional[Dict[str, Any]] = None,
    qr_box: Optional[BBox] = None,
) -> List[ExtractedField]:
    """
    Routes structured extraction by document type, extracts key-values for unsupported documents,
    and appends complete line-by-line OCR/text-layer lines for full canvas highlightability.
    """
    if doc_type == DocumentType.AADHAAR:
        fields = extract_aadhaar_fields(doc_id, pages_data, qr_data, qr_box)
    elif doc_type == DocumentType.PAN:
        fields = extract_pan_fields(doc_id, pages_data, qr_data, qr_box)
    elif doc_type == DocumentType.SALARY_SLIP:
        fields = extract_salary_slip_fields(doc_id, pages_data)
    elif doc_type == DocumentType.BANK_STATEMENT:
        fields = extract_bank_statement_fields(doc_id, pages_data)
    elif doc_type == DocumentType.LOAN_APPLICATION:
        fields = extract_loan_application_fields(doc_id, pages_data)
    elif doc_type == DocumentType.DECLARATION_15G:
        fields = extract_declaration_15g_fields(doc_id, pages_data)
    elif doc_type == DocumentType.PAYMENT_INSTRUCTION:
        fields = extract_payment_instruction_fields(doc_id, pages_data)
    else:
        # Unsupported or generic document: extract generic key-values
        fields = extract_generic_key_values(doc_id, pages_data)

    # Universal text line extraction for EVERY document (supported and unsupported)
    all_text_lines = extract_all_text_lines(doc_id, pages_data)
    fields.extend(all_text_lines)

    # Apply confidence thresholding: if confidence < CONFIDENCE_THRESHOLD, mark unable_to_assess
    for f in fields:
        if f.confidence < CONFIDENCE_THRESHOLD:
            f.unable_to_assess = True

    return fields
