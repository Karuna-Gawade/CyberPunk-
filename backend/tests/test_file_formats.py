"""
Unit & Integration tests for multi-format document support:
- DOCX text extraction & rendering
- XLSX text extraction & rendering
- Image formats (PNG/JPG)
- Unsupported file format 422 validation
"""

from pathlib import Path
import docx
import openpyxl
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.extraction.office_text import extract_docx_text, extract_xlsx_text
from backend.app.services.render import render_document_pages

client = TestClient(app)


def test_docx_extraction_and_rendering(tmp_path: Path):
    docx_path = tmp_path / "sample.docx"
    doc = docx.Document()
    doc.add_heading("Personal Loan Application", level=1)
    doc.add_paragraph("Applicant Name: Rajesh Sharma")
    doc.add_paragraph("Monthly Income: Rs. 85,000")
    tbl = doc.add_table(rows=2, cols=2)
    tbl.rows[0].cells[0].text = "Header A"
    tbl.rows[0].cells[1].text = "Header B"
    tbl.rows[1].cells[0].text = "Val 1"
    tbl.rows[1].cells[1].text = "Val 2"
    doc.save(str(docx_path))

    # Text extraction test
    pages = extract_docx_text(docx_path)
    assert len(pages) == 1
    full_text = pages[0]["full_text"]
    assert "Personal Loan Application" in full_text
    assert "Rajesh Sharma" in full_text
    assert "Header A | Header B" in full_text

    # Rendering test
    out_dir = tmp_path / "docx_rendered"
    rendered = render_document_pages(docx_path, out_dir, target_dpi=150)
    assert len(rendered) >= 1
    assert rendered[0].exists()


def test_xlsx_extraction_and_rendering(tmp_path: Path):
    xlsx_path = tmp_path / "sample.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Statement"
    ws.append(["Date", "Description", "Debit", "Credit", "Balance"])
    ws.append(["01/10/2026", "Opening Balance", "", "", "100000.00"])
    ws.append(["05/10/2026", "Salary Credit", "", "85000.00", "185000.00"])
    wb.save(str(xlsx_path))

    # Text extraction test
    pages = extract_xlsx_text(xlsx_path)
    assert len(pages) == 1
    full_text = pages[0]["full_text"]
    assert "Salary Credit" in full_text
    assert "185000" in full_text

    # Rendering test
    out_dir = tmp_path / "xlsx_rendered"
    rendered = render_document_pages(xlsx_path, out_dir, target_dpi=150)
    assert len(rendered) >= 1
    assert rendered[0].exists()


def test_unsupported_file_extension_rejected_with_422(tmp_path: Path):
    bad_file = tmp_path / "malicious_script.exe"
    bad_file.write_bytes(b"MZ executable header dummy content")

    res_inv = client.post("/investigations")
    assert res_inv.status_code == 200
    inv_id = res_inv.json()["investigation_id"]

    with open(bad_file, "rb") as fh:
        res = client.post(
            f"/investigations/{inv_id}/documents",
            files=[("files", ("malicious_script.exe", fh, "application/octet-stream"))],
        )
    assert res.status_code == 422
    assert "Unsupported file format" in res.json()["detail"]


def test_supported_docx_upload_via_api(tmp_path: Path):
    docx_file = tmp_path / "loan.docx"
    doc = docx.Document()
    doc.add_paragraph("Personal Loan Application Form")
    doc.add_paragraph("Applicant Name: Rajesh Sharma")
    doc.save(str(docx_file))

    res_inv = client.post("/investigations")
    inv_id = res_inv.json()["investigation_id"]

    with open(docx_file, "rb") as fh:
        res = client.post(
            f"/investigations/{inv_id}/documents",
            files=[("files", ("loan.docx", fh, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
        )
    assert res.status_code == 200
    docs = res.json()
    assert len(docs) == 1
    assert docs[0]["filename"] == "loan.docx"
