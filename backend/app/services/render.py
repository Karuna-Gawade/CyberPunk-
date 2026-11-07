"""
Document rendering service.
Renders PDF and image documents server-side to PNG images at a fixed 150 DPI.
"""

import tempfile
from pathlib import Path
from typing import List, Tuple
import fitz  # PyMuPDF
import cv2
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
import docx
import openpyxl


def _docx_to_rendered_pages(file_path: Path, output_dir: Path, target_dpi: int = 150) -> List[Path]:
    """Converts DOCX content to a clean temporary PDF and renders to PNGs at target DPI."""
    styles = getSampleStyleSheet()
    story = []

    doc_docx = docx.Document(str(file_path))
    for p in doc_docx.paragraphs:
        txt = p.text.strip()
        if txt:
            story.append(Paragraph(txt, styles["Normal"]))
            story.append(Spacer(1, 4))

    for t in doc_docx.tables:
        table_data = []
        for row in t.rows:
            row_cells = [Paragraph(c.text.strip(), styles["Normal"]) for c in row.cells]
            table_data.append(row_cells)
        if table_data:
            col_count = len(table_data[0])
            col_width = (500 / col_count) if col_count > 0 else 100
            rl_table = Table(table_data, colWidths=[col_width] * col_count)
            rl_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(rl_table)
            story.append(Spacer(1, 6))

    if not story:
        story.append(Paragraph("[Empty DOCX Document]", styles["Normal"]))

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        pdf_doc = SimpleDocTemplate(str(tmp_path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        pdf_doc.build(story)

        rendered_paths = []
        fz_doc = fitz.open(tmp_path)
        for page_idx in range(len(fz_doc)):
            pix = fz_doc[page_idx].get_pixmap(dpi=target_dpi)
            out_file = output_dir / f"page_{page_idx + 1}.png"
            pix.save(str(out_file))
            rendered_paths.append(out_file)
        fz_doc.close()
        return rendered_paths
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _xlsx_to_rendered_pages(file_path: Path, output_dir: Path, target_dpi: int = 150) -> List[Path]:
    """Converts XLSX worksheets to a clean temporary PDF and renders to PNGs at target DPI."""
    styles = getSampleStyleSheet()
    story = []

    wb = openpyxl.load_workbook(str(file_path), data_only=True, read_only=True)
    sheet_count = len(wb.worksheets)

    for s_idx, ws in enumerate(wb.worksheets):
        story.append(Paragraph(f"<b>Sheet: {ws.title}</b>", styles["Heading2"]))
        story.append(Spacer(1, 6))

        rows_data = []
        for row in ws.iter_rows(values_only=True):
            r_vals = [Paragraph(str(val) if val is not None else "", styles["Normal"]) for val in row]
            if any(val is not None for val in row):
                rows_data.append(r_vals)

        if rows_data:
            col_count = max(len(r) for r in rows_data)
            col_w = min(120, max(40, 500 // col_count)) if col_count > 0 else 60
            t = Table(rows_data, colWidths=[col_w] * col_count)
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(t)
        else:
            story.append(Paragraph("[Empty Sheet]", styles["Normal"]))

        if s_idx < sheet_count - 1:
            story.append(PageBreak())

    wb.close()

    if not story:
        story.append(Paragraph("[Empty Workbook]", styles["Normal"]))

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        pdf_doc = SimpleDocTemplate(str(tmp_path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        pdf_doc.build(story)

        rendered_paths = []
        fz_doc = fitz.open(tmp_path)
        for page_idx in range(len(fz_doc)):
            pix = fz_doc[page_idx].get_pixmap(dpi=target_dpi)
            out_file = output_dir / f"page_{page_idx + 1}.png"
            pix.save(str(out_file))
            rendered_paths.append(out_file)
        fz_doc.close()
        return rendered_paths
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def render_document_pages(file_path: Path, output_dir: Path, target_dpi: int = 150) -> List[Path]:
    """
    Renders every page of a PDF, image, DOCX, or XLSX file into PNG format at fixed 150 DPI.
    Returns list of paths to rendered PNG images: [page_1.png, page_2.png, ...]
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered_paths: List[Path] = []
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        doc = fitz.open(file_path)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            pix = page.get_pixmap(dpi=target_dpi)
            out_file = output_dir / f"page_{page_idx + 1}.png"
            pix.save(str(out_file))
            rendered_paths.append(out_file)
        doc.close()
    elif suffix in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"):
        img = cv2.imread(str(file_path))
        if img is not None:
            out_file = output_dir / "page_1.png"
            cv2.imwrite(str(out_file), img)
            rendered_paths.append(out_file)
        else:
            raise ValueError(f"Unable to read image file: {file_path}")
    elif suffix in (".docx",):
        rendered_paths = _docx_to_rendered_pages(file_path, output_dir, target_dpi)
    elif suffix in (".xlsx", ".xls"):
        rendered_paths = _xlsx_to_rendered_pages(file_path, output_dir, target_dpi)
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")

    return rendered_paths


def get_rendered_page_path(rendered_dir: Path, doc_id: str, page_number: int) -> Path:
    """Returns the expected path to the rendered 150 DPI PNG for a given doc and page."""
    return rendered_dir / doc_id / f"page_{page_number}.png"
