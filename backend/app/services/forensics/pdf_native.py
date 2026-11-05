"""
PDF-Native Forensics Engine using PyMuPDF.
Lead forensics methods:
1. Metadata Producer/Creator analysis (Photoshop, Canva, Sejda, iLovePDF, etc.)
2. Incremental update detection (counting %%EOF markers)
3. Sibling span font, size, and color anomaly inspection
4. Hidden text detection (microscopic font <3pt, white-on-white color, out-of-page bounds)
5. Text-layer vs rasterized OCR overlay diff detection
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import fitz  # PyMuPDF
from backend.app.models.contracts import (
    EvidenceItem,
    Finding,
    FindingCategory,
    FindingStatus,
    FindingStrength,
    FindingTier,
    ReviewerAction,
)
from backend.app.services.correlation.name_match import levenshtein_distance
from backend.app.services.extraction.text_layer import points_to_150_dpi

SUSPICIOUS_PRODUCERS = [
    "photoshop", "canva", "sejda", "ilovepdf", "gimp", "inkscape",
    "pdfescape", "smallpdf", "foxit phantompdf", "nitro pro", "wondershare"
]


def check_pdf_metadata(doc_path: Path, doc_id: str) -> List[Finding]:
    """Inspects PDF metadata dictionary for design/editing software and date drift."""
    findings = []
    try:
        doc = fitz.open(doc_path)
        meta = doc.metadata or {}
        producer = (meta.get("producer") or "").lower()
        creator = (meta.get("creator") or "").lower()

        # Check for editing software
        matched_tool = next((tool for tool in SUSPICIOUS_PRODUCERS if tool in producer or tool in creator), None)
        if matched_tool:
            findings.append(
                Finding(
                    finding_id=f"ANM-META-{doc_id}",
                    tier=FindingTier.OBSERVATION,
                    category=FindingCategory.FORENSIC,
                    rule_id="producer_editing_tool",
                    title="Design/editing software detected in PDF metadata",
                    evidence=[EvidenceItem(doc_id=doc_id, page=1, bbox=[10, 10, 200, 40], label="Document Metadata Header")],
                    signals=["editing_tool_metadata"],
                    strength=FindingStrength.WEAK,
                    confidence=0.85,
                    status=FindingStatus.REQUIRES_INVESTIGATION,
                    explanation=(
                        f"PDF metadata identifies creation/editing tool '{meta.get('producer') or meta.get('creator')}'. "
                        "Commercial editing software is atypical for automated banking and payroll generation systems."
                    ),
                    reviewer=ReviewerAction(),
                )
            )

        # Check creation vs modification date
        c_date = meta.get("creationDate")
        m_date = meta.get("modDate")
        if c_date and m_date and c_date != m_date:
            findings.append(
                Finding(
                    finding_id=f"ANM-DATE-REV-{doc_id}",
                    tier=FindingTier.OBSERVATION,
                    category=FindingCategory.FORENSIC,
                    rule_id="pdf_modification_date_drift",
                    title="PDF file was modified after original creation",
                    evidence=[EvidenceItem(doc_id=doc_id, page=1, bbox=[10, 10, 200, 40], label="Metadata Dates")],
                    signals=["pdf_modified_after_creation"],
                    strength=FindingStrength.WEAK,
                    confidence=0.75,
                    status=FindingStatus.REQUIRES_INVESTIGATION,
                    explanation=f"PDF creation timestamp ({c_date}) differs from modification timestamp ({m_date}).",
                    reviewer=ReviewerAction(),
                )
            )

        doc.close()
    except Exception:
        pass

    return findings


def check_incremental_updates(doc_path: Path, doc_id: str) -> List[Finding]:
    """Counts %%EOF markers to identify incremental PDF re-saving."""
    findings = []
    try:
        with open(doc_path, "rb") as f:
            content = f.read()

        eof_count = content.count(b"%%EOF")
        if eof_count > 1:
            findings.append(
                Finding(
                    finding_id=f"ANM-EOF-{doc_id}",
                    tier=FindingTier.OBSERVATION,
                    category=FindingCategory.FORENSIC,
                    rule_id="incremental_updates_flag",
                    title=f"Multiple incremental PDF updates detected ({eof_count} %%EOF markers)",
                    evidence=[EvidenceItem(doc_id=doc_id, page=1, bbox=[10, 10, 150, 30], label="PDF Structure Trail")],
                    signals=["pdf_multiple_eof"],
                    strength=FindingStrength.MODERATE,
                    confidence=0.88,
                    status=FindingStatus.REQUIRES_INVESTIGATION,
                    explanation=(
                        f"The PDF contains {eof_count} separate '%%EOF' end-of-file markers, "
                        "indicating the file was modified and re-saved incrementally after original compilation."
                    ),
                    reviewer=ReviewerAction(),
                )
            )
    except Exception:
        pass

    return findings


def get_base_font_family(font_name: str) -> str:
    """Normalizes font name to base family, ignoring weights/styles like Bold, Italic, Oblique."""
    # Strip subset prefixes like ABCDEF+Helvetica
    base = font_name.split("+")[-1]
    # Strip hyphenated style e.g. Helvetica-Bold -> Helvetica
    base = base.split("-")[0].split(",")[0]
    for style in ("Bold", "Italic", "Oblique", "Regular", "Medium", "Light"):
        base = base.replace(style, "")
    return base.strip().lower()


def check_font_inconsistencies(doc_path: Path, doc_id: str) -> List[Finding]:
    """
    Inspects PyMuPDF spans across the document.
    Flags spans with a differing font family (e.g. Courier vs dominant Helvetica)
    or significant font size anomalies (> 5pt difference from sibling spans on the same row).
    """
    findings = []
    try:
        doc = fitz.open(doc_path)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_dict = page.get_text("dict")

            # Collect all valid text spans on the page
            page_spans = []
            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span["text"].strip()
                        if text:
                            page_spans.append(span)

            if not page_spans:
                continue

            # Determine dominant font family of the document page
            families = [get_base_font_family(s["font"]) for s in page_spans]
            dominant_family = max(set(families), key=families.count)

            # 1. Check for alien/deviant font family (e.g. Courier in Helvetica document)
            for s in page_spans:
                s_text = s["text"].strip()
                s_family = get_base_font_family(s["font"])
                if s_family != dominant_family and len(s_text) >= 2:
                    pt_box = (s["bbox"][0], s["bbox"][1], s["bbox"][2], s["bbox"][3])
                    bbox_150 = points_to_150_dpi(pt_box)
                    findings.append(
                        Finding(
                            finding_id=f"ANM-FONT-{doc_id}-{page_idx + 1}-{bbox_150[0]}",
                            tier=FindingTier.OBSERVATION,
                            category=FindingCategory.FORENSIC,
                            rule_id="font_anomaly",
                            title=f"Inconsistent font family detected in span '{s_text}'",
                            evidence=[EvidenceItem(doc_id=doc_id, page=page_idx + 1, bbox=bbox_150, label=f"Font Anomaly: {s_text}")],
                            signals=["deviant_font_family"],
                            strength=FindingStrength.MODERATE,
                            confidence=0.92,
                            status=FindingStatus.REQUIRES_INVESTIGATION,
                            explanation=(
                                f"Span '{s_text}' uses font '{s['font']}' (family: {s_family}), diverging from dominant document font family '{dominant_family}'."
                            ),
                            reviewer=ReviewerAction(),
                        )
                    )

            # 2. Check for localized row size anomalies (horizontal alignment |y0 - y1| < 8)
            for i, s1 in enumerate(page_spans):
                for j in range(i + 1, len(page_spans)):
                    s2 = page_spans[j]
                    y_diff = abs(s1["bbox"][1] - s2["bbox"][1])
                    if y_diff < 5 and abs(s1["size"] - s2["size"]) > 6.0:
                        pt_box = (s1["bbox"][0], s1["bbox"][1], s1["bbox"][2], s1["bbox"][3])
                        bbox_150 = points_to_150_dpi(pt_box)
                        findings.append(
                            Finding(
                                finding_id=f"ANM-SIZE-{doc_id}-{page_idx + 1}-{bbox_150[0]}",
                                tier=FindingTier.OBSERVATION,
                                category=FindingCategory.FORENSIC,
                                rule_id="font_size_anomaly",
                                title=f"Font size anomaly across same row in '{s1['text'][:20]}'",
                                evidence=[EvidenceItem(doc_id=doc_id, page=page_idx + 1, bbox=bbox_150, label="Font Size Disparity")],
                                signals=["row_size_disparity"],
                                strength=FindingStrength.MODERATE,
                                confidence=0.88,
                                status=FindingStatus.REQUIRES_INVESTIGATION,
                                explanation=f"Row font size disparity: {round(s1['size'], 1)}pt vs {round(s2['size'], 1)}pt in neighboring span.",
                                reviewer=ReviewerAction(),
                            )
                        )
                        break

        doc.close()
    except Exception:
        pass

    return findings


def check_hidden_text_spans(doc_path: Path, doc_id: str) -> List[Tuple[Finding, Dict[str, Any]]]:
    """
    Detects hidden, microscopic, or white-on-white text spans.
    Returns list of (Finding, raw_span_dict).
    """
    results = []
    try:
        doc = fitz.open(doc_path)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_rect = page.rect
            page_dict = page.get_text("dict")

            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span["text"].strip()
                        if not text:
                            continue

                        size = span["size"]
                        color = span["color"]  # integer RGB
                        pt_box = span["bbox"]
                        bbox_150 = points_to_150_dpi(pt_box)

                        # Microscopic text (< 3.0 pt)
                        if size < 3.0:
                            f = Finding(
                                finding_id=f"ANM-MICRO-{doc_id}-{page_idx + 1}",
                                tier=FindingTier.OBSERVATION,
                                category=FindingCategory.FORENSIC,
                                rule_id="microscopic_text_detected",
                                title=f"Microscopic hidden text span ({round(size, 1)}pt)",
                                evidence=[EvidenceItem(doc_id=doc_id, page=page_idx + 1, bbox=bbox_150, label="Microscopic Text Span")],
                                signals=["hidden_microscopic_text"],
                                strength=FindingStrength.MODERATE,
                                confidence=0.92,
                                status=FindingStatus.REQUIRES_INVESTIGATION,
                                explanation=f"Text span '{text[:40]}...' rendered at microscopic font size ({round(size, 1)}pt).",
                                reviewer=ReviewerAction(),
                            )
                            results.append((f, span))

                        # White-on-white text (color 16777215 == 0xFFFFFF)
                        elif color == 16777215 or color == 0xFFFFFF:
                            f = Finding(
                                finding_id=f"ANM-WHITE-{doc_id}-{page_idx + 1}",
                                tier=FindingTier.OBSERVATION,
                                category=FindingCategory.FORENSIC,
                                rule_id="white_on_white_text_detected",
                                title="White-on-white hidden text span detected",
                                evidence=[EvidenceItem(doc_id=doc_id, page=page_idx + 1, bbox=bbox_150, label="White Hidden Text")],
                                signals=["hidden_white_text"],
                                strength=FindingStrength.STRONG,
                                confidence=0.95,
                                status=FindingStatus.REQUIRES_INVESTIGATION,
                                explanation=f"Text span with white font color (0xFFFFFF) detected: '{text[:50]}...'. Likely intended to be invisible to human eyes.",
                                reviewer=ReviewerAction(),
                            )
                            results.append((f, span))

                        # Outside page box
                        elif pt_box[0] < 0 or pt_box[1] < 0 or pt_box[2] > page_rect.width + 10 or pt_box[3] > page_rect.height + 10:
                            f = Finding(
                                finding_id=f"ANM-OFFPAGE-{doc_id}-{page_idx + 1}",
                                tier=FindingTier.OBSERVATION,
                                category=FindingCategory.FORENSIC,
                                rule_id="off_page_text_detected",
                                title="Text placed outside visible page boundary",
                                evidence=[EvidenceItem(doc_id=doc_id, page=page_idx + 1, bbox=bbox_150, label="Off-page Text Box")],
                                signals=["hidden_offpage_text"],
                                strength=FindingStrength.MODERATE,
                                confidence=0.90,
                                status=FindingStatus.REQUIRES_INVESTIGATION,
                                explanation=f"Text span '{text[:40]}...' positioned outside the printable page boundary.",
                                reviewer=ReviewerAction(),
                            )
                            results.append((f, span))

        doc.close()
    except Exception:
        pass

    return results


def check_text_layer_vs_ocr_diff(
    text_spans: List[Dict[str, Any]],
    ocr_words: List[Dict[str, Any]],
    doc_id: str,
    page_num: int = 1,
) -> List[Finding]:
    """
    Compares the vector PDF text layer against rasterized OCR output in the same spatial region.
    Significant difference indicates overlaid or digitally altered visual text.
    Tolerance threshold: normalized Levenshtein distance > 0.40.
    """
    findings = []
    if not text_spans or not ocr_words:
        return findings

    for s in text_spans:
        s_text = s["text"].strip()
        if len(s_text) < 4 or not any(c.isalnum() for c in s_text):
            continue

        s_box = s["bbox"]  # [x0, y0, x1, y1] at 150 DPI

        # Find matching OCR words overlapping this span's box
        overlapping_ocr = []
        for w in ocr_words:
            w_box = w["bbox"]
            # Overlap in 2D
            x_overlap = max(0, min(s_box[2], w_box[2]) - max(s_box[0], w_box[0]))
            y_overlap = max(0, min(s_box[3], w_box[3]) - max(s_box[1], w_box[1]))
            if x_overlap > 5 and y_overlap > 5:
                overlapping_ocr.append(w)

        if overlapping_ocr:
            ocr_text = " ".join(w["text"] for w in overlapping_ocr).strip()
            # Calculate edit distance
            dist = levenshtein_distance(s_text.lower(), ocr_text.lower())
            max_len = max(len(s_text), len(ocr_text))
            ratio = (dist / max_len) if max_len > 0 else 0.0

            # Significant mismatch threshold (accounting for slight OCR noise)
            if ratio > 0.40 and len(ocr_text) >= 3:
                findings.append(
                    Finding(
                        finding_id=f"ANM-LAYER-DIFF-{doc_id}-{page_num}-{s_box[0]}",
                        tier=FindingTier.INCONSISTENCY,
                        category=FindingCategory.FORENSIC,
                        rule_id="layer_ocr_mismatch",
                        title=f"Text-layer vs. visible OCR mismatch in region '{s_text}'",
                        evidence=[EvidenceItem(doc_id=doc_id, page=page_num, bbox=s_box, label="Overlay Tamper Region")],
                        signals=["text_layer_ocr_mismatch"],
                        strength=FindingStrength.STRONG,
                        confidence=0.92,
                        status=FindingStatus.REQUIRES_INVESTIGATION,
                        explanation=(
                            f"Underlying vector text layer contains '{s_text}', but visible rasterized OCR detects '{ocr_text}'. "
                            "Indicates text was overlaid or digitally patched over original content."
                        ),
                        reviewer=ReviewerAction(),
                    )
                )

    return findings
