"""
Dossier PDF generation using ReportLab.
Produces a comprehensive investigation report with:
- Investigation summary & review priority
- All findings with evidence details
- Evidence thumbnail crops from rendered pages
- Audit trail summary
- DRAFT watermark until a human case decision is recorded

Advisory output. Final decision rests with the human reviewer.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.app.models.contracts import (
    AuditEvent,
    Finding,
    FindingTier,
    Investigation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tier_label(tier: FindingTier) -> str:
    return tier.value.replace("_", " ").title()


def _crop_evidence_thumbnail(
    rendered_dir: Path,
    doc_id: str,
    page: int,
    bbox: List[int],
) -> Optional[str]:
    """
    Crops a thumbnail from the rendered page image at 150 DPI.
    Returns the path to the cropped image, or None if unavailable.
    """
    page_path = rendered_dir / doc_id / f"page_{page}.png"
    if not page_path.exists():
        return None

    try:
        import cv2
        import numpy as np

        img = cv2.imread(str(page_path))
        if img is None:
            return None

        x0, y0, x1, y1 = bbox
        h, w = img.shape[:2]
        # Clamp to image bounds with small padding
        pad = 8
        x0 = max(0, x0 - pad)
        y0 = max(0, y0 - pad)
        x1 = min(w, x1 + pad)
        y1 = min(h, y1 + pad)

        if x1 <= x0 or y1 <= y0:
            return None

        crop = img[y0:y1, x0:x1]

        # Save crop
        crop_dir = rendered_dir / doc_id / "crops"
        crop_dir.mkdir(parents=True, exist_ok=True)
        crop_path = crop_dir / f"evidence_p{page}_{x0}_{y0}_{x1}_{y1}.png"
        cv2.imwrite(str(crop_path), crop)
        return str(crop_path)
    except Exception:
        return None


def _truncate(s: str, max_len: int = 120) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


# ---------------------------------------------------------------------------
# DRAFT watermark callback
# ---------------------------------------------------------------------------

def _draw_draft_watermark(canvas, doc):
    """Draws a diagonal DRAFT watermark on every page."""
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 72)
    canvas.setFillColor(colors.Color(0.85, 0.85, 0.85, alpha=0.4))
    canvas.translate(doc.pagesize[0] / 2, doc.pagesize[1] / 2)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "DRAFT")
    canvas.restoreState()


def _draw_advisory_footer(canvas, doc):
    """Advisory footer on every page."""
    canvas.saveState()
    canvas.setFont("Helvetica-Oblique", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(
        doc.pagesize[0] / 2,
        12 * mm,
        "Advisory output. Final decision rests with the human reviewer. "
        "Informed by ISO/IEC 27037, 27041, 27042, NIST SP 800-86.",
    )
    canvas.restoreState()


def _page_callback_draft(canvas, doc):
    _draw_draft_watermark(canvas, doc)
    _draw_advisory_footer(canvas, doc)


def _page_callback_final(canvas, doc):
    _draw_advisory_footer(canvas, doc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_dossier(
    investigation: Investigation,
    findings: List[Finding],
    audit_events: List[AuditEvent],
    rendered_dir: Path,
    output_dir: Path,
) -> Path:
    """
    Generates a ReportLab PDF dossier for the given investigation.
    Returns the path to the generated PDF file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"dossier_{investigation.investigation_id}.pdf"
    pdf_path = output_dir / filename

    is_draft = investigation.case_decision is None
    page_callback = _page_callback_draft if is_draft else _page_callback_final

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        title=f"Investigation Dossier — {investigation.investigation_id}",
        author="AI Document Forensics System (Advisory)",
    )

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "DossierTitle",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )
    style_heading = ParagraphStyle(
        "DossierHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=14,
        spaceAfter=6,
    )
    style_body = ParagraphStyle(
        "DossierBody",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#334155"),
        leading=13,
    )
    style_small = ParagraphStyle(
        "DossierSmall",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.grey,
        leading=9,
    )
    style_advisory = ParagraphStyle(
        "DossierAdvisory",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#b91c1c"),
        alignment=TA_CENTER,
        spaceAfter=10,
        spaceBefore=4,
        backColor=colors.HexColor("#fef2f2"),
    )

    elements = []

    # ---- Title ----
    elements.append(Paragraph("Investigation Dossier", style_title))
    elements.append(
        Paragraph(
            "<b>Advisory output. Final decision rests with the human reviewer.</b>",
            style_advisory,
        )
    )
    elements.append(Spacer(1, 6))

    # ---- Summary Table ----
    summary_data = [
        ["Investigation ID", investigation.investigation_id],
        ["Created", investigation.created_at],
        ["Review Priority", investigation.review_priority.value.upper()],
        ["Priority Score", str(investigation.priority_score)],
        ["Documents", str(len(investigation.documents))],
        ["Total Findings", str(len(findings))],
        [
            "Case Decision",
            investigation.case_decision.decision.value.replace("_", " ").title()
            if investigation.case_decision
            else "PENDING (DRAFT)",
        ],
    ]
    if investigation.case_decision:
        summary_data.append(
            ["Decided By", investigation.case_decision.decided_by]
        )
        summary_data.append(
            ["Decision Note", _truncate(investigation.case_decision.outcome_note, 80)]
        )

    summary_table = Table(
        summary_data,
        colWidths=[55 * mm, 120 * mm],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1e293b")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 10))

    # ---- Documents List ----
    elements.append(Paragraph("Documents Submitted", style_heading))
    for d in investigation.documents:
        elements.append(
            Paragraph(
                f"<b>{d.filename}</b> — Type: {d.type.value}, Status: {d.status.value}, "
                f"SHA-256: {d.sha256[:16]}..., Pages: {d.pages}",
                style_body,
            )
        )
    elements.append(Spacer(1, 8))

    # ---- Findings ----
    elements.append(Paragraph(f"Findings ({len(findings)})", style_heading))

    if not findings:
        elements.append(
            Paragraph(
                "No inconsistencies or anomalies detected by deterministic rules.",
                style_body,
            )
        )
    else:
        # Group by tier
        tier_order = [
            FindingTier.POTENTIAL_MANIPULATION,
            FindingTier.INCONSISTENCY,
            FindingTier.OBSERVATION,
        ]
        for tier in tier_order:
            tier_findings = [f for f in findings if f.tier == tier]
            if not tier_findings:
                continue

            elements.append(
                Paragraph(
                    f"{_tier_label(tier)} ({len(tier_findings)})",
                    ParagraphStyle(
                        "TierSub",
                        parent=styles["Heading3"],
                        fontSize=11,
                        textColor=colors.HexColor("#475569"),
                        spaceBefore=8,
                        spaceAfter=4,
                    ),
                )
            )

            for f in tier_findings:
                # Finding card
                finding_data = [
                    [
                        Paragraph(f"<b>{f.title}</b>", style_body),
                        Paragraph(
                            f"Rule: {f.rule_id} | Strength: {f.strength.value} | "
                            f"Confidence: {f.confidence:.0%}",
                            style_small,
                        ),
                    ],
                ]
                ft = Table(finding_data, colWidths=[120 * mm, 55 * mm])
                ft.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ]
                    )
                )
                elements.append(ft)

                # Explanation
                elements.append(
                    Paragraph(
                        _truncate(f.explanation, 300),
                        style_body,
                    )
                )

                # Status
                status_text = f.status.value.replace("_", " ").title()
                if f.reviewer.decision:
                    status_text += f" (Reviewer: {f.reviewer.decision.value})"
                    if f.reviewer.reason:
                        status_text += f" — {_truncate(f.reviewer.reason, 60)}"
                elements.append(
                    Paragraph(f"<i>Status: {status_text}</i>", style_small)
                )

                # Evidence locations
                for ev in f.evidence:
                    ev_text = f"Evidence: {ev.doc_id} page {ev.page} bbox [{', '.join(str(v) for v in ev.bbox)}]"
                    if ev.label:
                        ev_text += f" — {ev.label}"
                    elements.append(Paragraph(ev_text, style_small))

                    # Thumbnail crop
                    thumb_path = _crop_evidence_thumbnail(
                        rendered_dir, ev.doc_id, ev.page, ev.bbox
                    )
                    if thumb_path and os.path.exists(thumb_path):
                        try:
                            img = Image(thumb_path)
                            # Scale to fit within 150mm wide, max 40mm tall
                            max_w, max_h = 150 * mm, 40 * mm
                            iw, ih = img.imageWidth, img.imageHeight
                            if iw > 0 and ih > 0:
                                ratio = min(max_w / iw, max_h / ih, 1.0)
                                img.drawWidth = iw * ratio
                                img.drawHeight = ih * ratio
                            elements.append(img)
                        except Exception:
                            pass

                elements.append(Spacer(1, 6))

    # ---- Priority Breakdown ----
    if investigation.priority_breakdown:
        elements.append(Paragraph("Review Priority Breakdown", style_heading))
        bd_data = [["Rule ID", "Title", "Points", "Tier"]]
        for item in investigation.priority_breakdown:
            bd_data.append(
                [
                    item.rule_id,
                    _truncate(item.title, 50),
                    str(item.points),
                    item.tier.value,
                ]
            )
        bd_table = Table(bd_data, colWidths=[40 * mm, 70 * mm, 20 * mm, 40 * mm])
        bd_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        elements.append(bd_table)
        elements.append(Spacer(1, 8))

    # ---- Audit Trail (tail — last 20 events) ----
    elements.append(PageBreak())
    elements.append(Paragraph("Audit Trail (latest events)", style_heading))

    tail_events = audit_events[-20:] if len(audit_events) > 20 else audit_events
    if tail_events:
        aud_data = [["Seq", "Timestamp", "Actor", "Action", "Object"]]
        for ev in tail_events:
            aud_data.append(
                [
                    str(ev.seq),
                    ev.timestamp[:19],
                    ev.actor,
                    ev.action,
                    _truncate(ev.object_id, 30),
                ]
            )
        aud_table = Table(
            aud_data, colWidths=[12 * mm, 38 * mm, 30 * mm, 38 * mm, 50 * mm]
        )
        aud_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        elements.append(aud_table)
    else:
        elements.append(Paragraph("No audit events recorded.", style_body))

    # ---- Build PDF ----
    doc.build(elements, onFirstPage=page_callback, onLaterPages=page_callback)
    return pdf_path
