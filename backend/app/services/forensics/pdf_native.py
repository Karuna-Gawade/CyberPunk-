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


def check_signature_region(
    doc_path: Path,
    doc_id: str,
    rendered_pages: List[Path],
    fields: Optional[List[Any]] = None,
) -> List[Finding]:
    """
    Checks for the presence of signature stroke pixels in the region below
    'signature' or 'authorised signatory' labels.
    - If empty: emits 'signature_region_empty' observation.
    - If signature overlaps an extracted data field: emits 'signature_placement_overlap'.
    NOTE: Does not compare signature shape/biometrics.
    """
    findings = []
    if not rendered_pages:
        return findings

    try:
        import cv2
        import numpy as np

        doc = fitz.open(doc_path)
        for page_idx in range(len(doc)):
            if page_idx >= len(rendered_pages):
                break
            page = doc[page_idx]
            page_dict = page.get_text("dict")
            img_path = rendered_pages[page_idx]
            if not img_path.exists():
                continue

            gray_img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if gray_img is None:
                continue
            img_h, img_w = gray_img.shape

            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span["text"].strip().lower()
                        if any(term in text for term in ["signature", "authorised signatory", "authorized signatory"]):
                            pt_box = span["bbox"]
                            sig_pt_box = (
                                pt_box[0],
                                pt_box[3],
                                max(pt_box[2], pt_box[0] + 120),
                                pt_box[3] + 50,
                            )
                            sig_150 = points_to_150_dpi(sig_pt_box)
                            x0 = max(0, min(sig_150[0], img_w - 1))
                            y0 = max(0, min(sig_150[1], img_h - 1))
                            x1 = max(0, min(sig_150[2], img_w))
                            y1 = max(0, min(sig_150[3], img_h))

                            if x1 <= x0 + 10 or y1 <= y0 + 10:
                                continue

                            crop = gray_img[y0:y1, x0:x1]
                            dark_pixels = np.sum(crop < 180)
                            total_pixels = crop.size
                            dark_ratio = (dark_pixels / total_pixels) if total_pixels > 0 else 0.0

                            if dark_ratio < 0.002:
                                findings.append(
                                    Finding(
                                        finding_id=f"ANM-SIG-EMPTY-{doc_id}-{page_idx + 1}-{x0}",
                                        tier=FindingTier.OBSERVATION,
                                        category=FindingCategory.FORENSIC,
                                        rule_id="signature_region_empty",
                                        title=f"Signature region below '{span['text'].strip()}' appears unexecuted / empty",
                                        evidence=[EvidenceItem(doc_id=doc_id, page=page_idx + 1, bbox=[x0, y0, x1, y1], label="Unsigned Signature Area")],
                                        signals=["signature_region_empty"],
                                        strength=FindingStrength.WEAK,
                                        confidence=0.85,
                                        status=FindingStatus.REQUIRES_INVESTIGATION,
                                        explanation=(
                                            f"Signature region below '{span['text'].strip()}' contains no visible ink or stroke marks "
                                            f"(stroke pixel density: {dark_ratio:.2%})."
                                        ),
                                        reviewer=ReviewerAction(),
                                    )
                                )
                            elif fields and dark_ratio >= 0.005:
                                for f in fields:
                                    if getattr(f, "page", 1) == page_idx + 1 and getattr(f, "name", "") not in ("purpose", "address"):
                                        fx0, fy0, fx1, fy1 = getattr(f, "bbox", [0, 0, 0, 0])
                                        x_ov = max(0, min(x1, fx1) - max(x0, fx0))
                                        y_ov = max(0, min(y1, fy1) - max(y0, fy0))
                                        if x_ov > 15 and y_ov > 10:
                                            findings.append(
                                                Finding(
                                                    finding_id=f"ANM-SIG-OVERLAP-{doc_id}-{page_idx + 1}-{f.name}",
                                                    tier=FindingTier.OBSERVATION,
                                                    category=FindingCategory.FORENSIC,
                                                    rule_id="signature_placement_overlap",
                                                    title=f"Signature stroke placement overlaps data field '{f.name}'",
                                                    evidence=[
                                                        EvidenceItem(doc_id=doc_id, page=page_idx + 1, bbox=[x0, y0, x1, y1], label="Signature Region"),
                                                        EvidenceItem(doc_id=doc_id, field_id=f.field_id, page=f.page, bbox=f.bbox, label=f"Overlapped Field: {f.name}"),
                                                    ],
                                                    signals=["signature_placement_overlap"],
                                                    strength=FindingStrength.WEAK,
                                                    confidence=0.82,
                                                    status=FindingStatus.REQUIRES_INVESTIGATION,
                                                    explanation=f"Signature mark intersects coordinate bounding box of extracted data field '{f.name}'.",
                                                    reviewer=ReviewerAction(),
                                                )
                                            )
                                            break

        doc.close()
    except Exception:
        pass

    return findings


def check_baseline_alignment(doc_path: Path, doc_id: str) -> List[Finding]:
    """
    Inspects text line spans to identify irregular vertical baseline displacements.
    Spans that share a logical line with > 3pt baseline disparity indicate potential text splicing.
    Emits at most one finding per line.
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
                        txt = span.get("text", "").strip()
                        if txt and len(txt) >= 2:
                            origin = span.get("origin")
                            by = origin[1] if origin else span.get("bbox", [0, 0, 0, 0])[3]
                            page_spans.append((by, span))

            # Sort spans by vertical coordinate, then horizontal
            page_spans.sort(key=lambda item: (item[1]["bbox"][1], item[1]["bbox"][0]))

            found_anomaly = False
            for i in range(len(page_spans) - 1):
                b1_y, s1 = page_spans[i]
                b2_y, s2 = page_spans[i + 1]
                y_diff = abs(s1["bbox"][1] - s2["bbox"][1])
                # Spans on the same visual horizontal band (< 8pt) and within reasonable horizontal proximity
                h_gap = s2["bbox"][0] - s1["bbox"][2]
                if y_diff < 8 and (-10 <= h_gap < 80):
                    diff = abs(b1_y - b2_y)
                    line_h = max(s1.get("size", 10), s2.get("size", 10))

                    if 3.0 < diff < (line_h * 1.5):
                        pt_box = s2["bbox"]
                        bbox_150 = points_to_150_dpi(pt_box)
                        findings.append(
                            Finding(
                                finding_id=f"ANM-BASE-{doc_id}-{page_idx + 1}-{bbox_150[0]}",
                                tier=FindingTier.OBSERVATION,
                                category=FindingCategory.FORENSIC,
                                rule_id="baseline_alignment_anomaly",
                                title=f"Baseline alignment irregularity ({diff:.1f}pt) on row '{s1['text'][:15]}...'",
                                evidence=[EvidenceItem(doc_id=doc_id, page=page_idx + 1, bbox=bbox_150, label="Misaligned Span Baseline")],
                                signals=["baseline_alignment_anomaly"],
                                strength=FindingStrength.WEAK,
                                confidence=0.80,
                                status=FindingStatus.REQUIRES_INVESTIGATION,
                                explanation=(
                                    f"Neighboring spans '{s1['text'][:20]}' and '{s2['text'][:20]}' share a visual row "
                                    f"but exhibit a vertical baseline displacement of {diff:.1f}pt."
                                ),
                                reviewer=ReviewerAction(),
                            )
                        )
                        found_anomaly = True
                        if len(findings) >= 5:
                            break

        doc.close()
    except Exception:
        pass

    return findings
