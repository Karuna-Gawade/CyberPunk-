"""
Direct text extraction from Office documents (DOCX and XLSX).
Returns pages_data compatible with extract_pdf_text_layer:
[{"page": int, "full_text": str, "words": [], "spans": []}]
"""

from pathlib import Path
from typing import Any, Dict, List
import docx
import openpyxl


def extract_docx_text(file_path: Path) -> List[Dict[str, Any]]:
    """Extracts text paragraphs and table cells from a DOCX document."""
    try:
        doc = docx.Document(str(file_path))
        lines = []

        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt:
                lines.append(txt)

        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    lines.append(" | ".join(row_cells))

        full_text = "\n".join(lines).strip()
        return [{"page": 1, "full_text": full_text, "words": [], "spans": []}]
    except Exception as e:
        return [{"page": 1, "full_text": "", "words": [], "spans": []}]


def extract_xlsx_text(file_path: Path) -> List[Dict[str, Any]]:
    """Extracts cell values from an Excel workbook (.xlsx / .xls)."""
    try:
        wb = openpyxl.load_workbook(str(file_path), data_only=True, read_only=True)
        pages_data = []

        for page_idx, ws in enumerate(wb.worksheets, start=1):
            lines = []
            for row in ws.iter_rows(values_only=True):
                non_empty = [str(val).strip() for val in row if val is not None and str(val).strip()]
                if non_empty:
                    lines.append(" | ".join(non_empty))

            sheet_text = f"Sheet: {ws.title}\n" + "\n".join(lines).strip()
            pages_data.append({"page": page_idx, "full_text": sheet_text, "words": [], "spans": []})

        wb.close()
        return pages_data if pages_data else [{"page": 1, "full_text": "", "words": [], "spans": []}]
    except Exception as e:
        return [{"page": 1, "full_text": "", "words": [], "spans": []}]
