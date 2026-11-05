"""
Cross-document correlation engine.
Compares shared identity and financial entities across all documents in an investigation:
1. Multi-document Name consistency (using in-house fuzzy matcher)
2. Date of Birth (DOB) consistency (Aadhaar vs PAN)
3. PAN number match (PAN Card vs Salary Slip)
4. Salary slip Net Pay vs Bank Statement salary credit transactions
5. Statement period vs payslip month

Emits Finding records with two-sided evidence bounding boxes.
Produces cross-document comparison matrix for the Cross-Document View.
"""

from typing import Any, Dict, List, Optional, Tuple
from backend.app.models.contracts import (
    DocumentRecord,
    DocumentType,
    EvidenceItem,
    ExtractedField,
    Finding,
    FindingCategory,
    FindingStatus,
    FindingStrength,
    FindingTier,
    ReviewerAction,
)
from backend.app.services.correlation.dates import (
    are_dates_equal,
    check_statement_period_covers_month,
    validate_plausible_dob,
)
from backend.app.services.correlation.name_match import compare_names

SALARY_CREDIT_TOLERANCE_INR = 50.0


def find_field(fields: List[ExtractedField], name: str) -> Optional[ExtractedField]:
    return next((f for f in fields if f.name == name), None)


class CrossDocEngine:
    def __init__(self):
        pass

    def correlate_investigation(
        self,
        investigation_id: str,
        documents: List[DocumentRecord],
    ) -> Tuple[List[Finding], List[Dict[str, Any]]]:
        """
        Runs multi-document correlation across all processed documents.
        Returns:
          (findings_list, comparison_matrix_rows)
        """
        findings: List[Finding] = []
        comparison_matrix: List[Dict[str, Any]] = []

        # Filter processed documents only
        proc_docs = [d for d in documents if d.status.value == "processed"]
        if len(proc_docs) < 2:
            return findings, comparison_matrix

        # Organize documents by type
        doc_by_type: Dict[DocumentType, DocumentRecord] = {d.type: d for d in proc_docs}
        aadhaar_doc = doc_by_type.get(DocumentType.AADHAAR)
        pan_doc = doc_by_type.get(DocumentType.PAN)
        slip_doc = doc_by_type.get(DocumentType.SALARY_SLIP)
        bank_doc = doc_by_type.get(DocumentType.BANK_STATEMENT)

        # -------------------------------------------------------------
        # 1. CROSS-DOCUMENT NAME CORRELATION
        # -------------------------------------------------------------
        name_entries = []
        for d in proc_docs:
            f = find_field(d.fields, "name") or find_field(d.fields, "employee_name") or find_field(d.fields, "account_holder")
            if f and f.value:
                name_entries.append((d, f))

        # Compare pairs of names across documents
        for i in range(len(name_entries)):
            for j in range(i + 1, len(name_entries)):
                d1, f1 = name_entries[i]
                d2, f2 = name_entries[j]

                score, band, detail = compare_names(str(f1.value), str(f2.value))
                matrix_entry = {
                    "field_name": "Full Name",
                    "status": band,
                    "score": score,
                    "docs": [
                        {"doc_id": d1.doc_id, "doc_type": d1.type.value, "value": str(f1.value), "field_id": f1.field_id, "bbox": f1.bbox, "page": f1.page},
                        {"doc_id": d2.doc_id, "doc_type": d2.type.value, "value": str(f2.value), "field_id": f2.field_id, "bbox": f2.bbox, "page": f2.page},
                    ],
                }

                if band == "conflict":
                    finding_id = f"ANM-NAME-{d1.doc_id}-{d2.doc_id}"
                    matrix_entry["finding_id"] = finding_id
                    findings.append(
                        Finding(
                            finding_id=finding_id,
                            tier=FindingTier.INCONSISTENCY,
                            category=FindingCategory.CROSS_DOCUMENT,
                            rule_id="name_match_conflict",
                            title=f"Name conflict between {d1.type.value} and {d2.type.value}",
                            evidence=[
                                EvidenceItem(doc_id=d1.doc_id, field_id=f1.field_id, page=f1.page, bbox=f1.bbox, label=f"{d1.type.value} Name"),
                                EvidenceItem(doc_id=d2.doc_id, field_id=f2.field_id, page=f2.page, bbox=f2.bbox, label=f"{d2.type.value} Name"),
                            ],
                            signals=["cross_doc_name_conflict"],
                            strength=FindingStrength.STRONG,
                            confidence=0.90,
                            status=FindingStatus.REQUIRES_INVESTIGATION,
                            explanation=f"Name on {d1.filename} ('{f1.value}') conflicts with name on {d2.filename} ('{f2.value}') - similarity score: {score}%.",
                            reviewer=ReviewerAction(),
                        )
                    )
                elif band == "needs_review":
                    finding_id = f"ANM-NAME-REV-{d1.doc_id}-{d2.doc_id}"
                    matrix_entry["finding_id"] = finding_id
                    findings.append(
                        Finding(
                            finding_id=finding_id,
                            tier=FindingTier.OBSERVATION,
                            category=FindingCategory.CROSS_DOCUMENT,
                            rule_id="name_match_review",
                            title=f"Minor name variation between {d1.type.value} and {d2.type.value}",
                            evidence=[
                                EvidenceItem(doc_id=d1.doc_id, field_id=f1.field_id, page=f1.page, bbox=f1.bbox, label=f"{d1.type.value} Name"),
                                EvidenceItem(doc_id=d2.doc_id, field_id=f2.field_id, page=f2.page, bbox=f2.bbox, label=f"{d2.type.value} Name"),
                            ],
                            signals=["cross_doc_name_variance"],
                            strength=FindingStrength.WEAK,
                            confidence=0.80,
                            status=FindingStatus.REQUIRES_INVESTIGATION,
                            explanation=f"Minor name variation between {d1.filename} ('{f1.value}') and {d2.filename} ('{f2.value}') - match score: {score}%. Recommended for human reviewer verification.",
                            reviewer=ReviewerAction(),
                        )
                    )

                comparison_matrix.append(matrix_entry)

        # -------------------------------------------------------------
        # 2. CROSS-DOCUMENT DOB CORRELATION (Aadhaar vs PAN)
        # -------------------------------------------------------------
        if aadhaar_doc and pan_doc:
            a_dob = find_field(aadhaar_doc.fields, "dob")
            p_dob = find_field(pan_doc.fields, "dob")

            if a_dob and p_dob and a_dob.value and p_dob.value:
                matrix_entry = {
                    "field_name": "Date of Birth",
                    "status": "match",
                    "score": 100.0,
                    "docs": [
                        {"doc_id": aadhaar_doc.doc_id, "doc_type": "aadhaar", "value": str(a_dob.value), "field_id": a_dob.field_id, "bbox": a_dob.bbox, "page": a_dob.page},
                        {"doc_id": pan_doc.doc_id, "doc_type": "pan", "value": str(p_dob.value), "field_id": p_dob.field_id, "bbox": p_dob.bbox, "page": p_dob.page},
                    ],
                }

                if not are_dates_equal(str(a_dob.value), str(p_dob.value)):
                    finding_id = f"ANM-DOB-{aadhaar_doc.doc_id}-{pan_doc.doc_id}"
                    matrix_entry["status"] = "conflict"
                    matrix_entry["score"] = 0.0
                    matrix_entry["finding_id"] = finding_id
                    findings.append(
                        Finding(
                            finding_id=finding_id,
                            tier=FindingTier.INCONSISTENCY,
                            category=FindingCategory.CROSS_DOCUMENT,
                            rule_id="dob_match",
                            title="Date of Birth mismatch between Aadhaar and PAN",
                            evidence=[
                                EvidenceItem(doc_id=aadhaar_doc.doc_id, field_id=a_dob.field_id, page=a_dob.page, bbox=a_dob.bbox, label="Aadhaar DOB"),
                                EvidenceItem(doc_id=pan_doc.doc_id, field_id=p_dob.field_id, page=p_dob.page, bbox=p_dob.bbox, label="PAN DOB"),
                            ],
                            signals=["cross_doc_dob_mismatch"],
                            strength=FindingStrength.STRONG,
                            confidence=0.95,
                            status=FindingStatus.REQUIRES_INVESTIGATION,
                            explanation=f"Aadhaar card DOB is '{a_dob.value}', but PAN card DOB is '{p_dob.value}'. Conflicting birth dates across official government identity cards.",
                            reviewer=ReviewerAction(),
                        )
                    )

                comparison_matrix.append(matrix_entry)

        # -------------------------------------------------------------
        # 3. PAN NUMBER CORRELATION (PAN Card vs Salary Slip)
        # -------------------------------------------------------------
        if pan_doc and slip_doc:
            p_pan = find_field(pan_doc.fields, "pan_number")
            s_pan = find_field(slip_doc.fields, "pan_number")

            if p_pan and s_pan and p_pan.value and s_pan.value:
                matrix_entry = {
                    "field_name": "PAN Number",
                    "status": "match",
                    "score": 100.0,
                    "docs": [
                        {"doc_id": pan_doc.doc_id, "doc_type": "pan", "value": str(p_pan.value), "field_id": p_pan.field_id, "bbox": p_pan.bbox, "page": p_pan.page},
                        {"doc_id": slip_doc.doc_id, "doc_type": "salary_slip", "value": str(s_pan.value), "field_id": s_pan.field_id, "bbox": s_pan.bbox, "page": s_pan.page},
                    ],
                }

                if str(p_pan.value).strip().upper() != str(s_pan.value).strip().upper():
                    finding_id = f"ANM-PAN-{pan_doc.doc_id}-{slip_doc.doc_id}"
                    matrix_entry["status"] = "conflict"
                    matrix_entry["score"] = 0.0
                    matrix_entry["finding_id"] = finding_id
                    findings.append(
                        Finding(
                            finding_id=finding_id,
                            tier=FindingTier.INCONSISTENCY,
                            category=FindingCategory.CROSS_DOCUMENT,
                            rule_id="pan_cross_match",
                            title="PAN number mismatch between PAN card and salary slip",
                            evidence=[
                                EvidenceItem(doc_id=pan_doc.doc_id, field_id=p_pan.field_id, page=p_pan.page, bbox=p_pan.bbox, label="PAN Card"),
                                EvidenceItem(doc_id=slip_doc.doc_id, field_id=s_pan.field_id, page=s_pan.page, bbox=s_pan.bbox, label="Salary Slip PAN"),
                            ],
                            signals=["cross_doc_pan_mismatch"],
                            strength=FindingStrength.STRONG,
                            confidence=0.98,
                            status=FindingStatus.REQUIRES_INVESTIGATION,
                            explanation=f"PAN Card number is '{p_pan.value}', whereas salary slip quotes '{s_pan.value}'.",
                            reviewer=ReviewerAction(),
                        )
                    )

                comparison_matrix.append(matrix_entry)

        # -------------------------------------------------------------
        # 4. SALARY SLIP NET PAY vs BANK SALARY CREDITS
        # -------------------------------------------------------------
        if slip_doc and bank_doc:
            s_net = find_field(slip_doc.fields, "net_pay")
            b_credits = find_field(bank_doc.fields, "salary_credits")

            if s_net and s_net.value and b_credits and b_credits.value:
                net_val = float(s_net.value)
                credits_list = [float(c) for c in b_credits.value if isinstance(c, (int, float))]

                # Check if net_val matches any credited deposit within tolerance
                matched_credit = next((c for c in credits_list if abs(c - net_val) <= SALARY_CREDIT_TOLERANCE_INR), None)

                matrix_entry = {
                    "field_name": "Salary Credit Match",
                    "status": "match" if matched_credit is not None else "conflict",
                    "score": 100.0 if matched_credit is not None else 0.0,
                    "docs": [
                        {"doc_id": slip_doc.doc_id, "doc_type": "salary_slip", "value": f"INR {net_val:,.2f}", "field_id": s_net.field_id, "bbox": s_net.bbox, "page": s_net.page},
                        {"doc_id": bank_doc.doc_id, "doc_type": "bank_statement", "value": f"Credits: {', '.join(f'INR {c:,.2f}' for c in credits_list)}", "field_id": b_credits.field_id, "bbox": b_credits.bbox, "page": b_credits.page},
                    ],
                }

                if matched_credit is None:
                    finding_id = f"ANM-SAL-{slip_doc.doc_id}-{bank_doc.doc_id}"
                    matrix_entry["finding_id"] = finding_id
                    findings.append(
                        Finding(
                            finding_id=finding_id,
                            tier=FindingTier.INCONSISTENCY,
                            category=FindingCategory.CROSS_DOCUMENT,
                            rule_id="salary_credit_match",
                            title="Salary slip net pay differs from bank credits",
                            evidence=[
                                EvidenceItem(doc_id=slip_doc.doc_id, field_id=s_net.field_id, page=s_net.page, bbox=s_net.bbox, label="Slip Net Pay"),
                                EvidenceItem(doc_id=bank_doc.doc_id, field_id=b_credits.field_id, page=b_credits.page, bbox=b_credits.bbox, label="Bank Salary Credit"),
                            ],
                            signals=["salary_credit_mismatch"],
                            strength=FindingStrength.STRONG,
                            confidence=0.92,
                            status=FindingStatus.REQUIRES_INVESTIGATION,
                            explanation=(
                                f"Salary slip net pay is INR {net_val:,.2f}, but bank statement transaction credits "
                                f"show deposits of {', '.join(f'INR {c:,.2f}' for c in credits_list)}. No matching salary deposit found."
                            ),
                            reviewer=ReviewerAction(),
                        )
                    )

                comparison_matrix.append(matrix_entry)

        # -------------------------------------------------------------
        # 5. STATEMENT PERIOD vs PAYSLIP MONTH
        # -------------------------------------------------------------
        if slip_doc and bank_doc:
            s_month = find_field(slip_doc.fields, "month")
            b_period = find_field(bank_doc.fields, "period")

            if s_month and b_period and s_month.value and b_period.value:
                covers, period_detail = check_statement_period_covers_month(str(b_period.value), str(s_month.value))
                if not covers:
                    findings.append(
                        Finding(
                            finding_id=f"ANM-PERIOD-{slip_doc.doc_id}-{bank_doc.doc_id}",
                            tier=FindingTier.INCONSISTENCY,
                            category=FindingCategory.CROSS_DOCUMENT,
                            rule_id="statement_period_mismatch",
                            title="Bank statement period does not cover salary slip month",
                            evidence=[
                                EvidenceItem(doc_id=slip_doc.doc_id, field_id=s_month.field_id, page=s_month.page, bbox=s_month.bbox, label="Slip Month"),
                                EvidenceItem(doc_id=bank_doc.doc_id, field_id=b_period.field_id, page=b_period.page, bbox=b_period.bbox, label="Bank Period"),
                            ],
                            signals=["statement_period_mismatch"],
                            strength=FindingStrength.MODERATE,
                            confidence=0.85,
                            status=FindingStatus.REQUIRES_INVESTIGATION,
                            explanation=period_detail,
                            reviewer=ReviewerAction(),
                        )
                    )

        return findings, comparison_matrix
