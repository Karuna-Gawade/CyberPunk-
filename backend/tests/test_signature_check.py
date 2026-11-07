"""
Unit tests for visual signature verification and baseline alignment forensics.
"""

from pathlib import Path
import fitz
import pytest
from backend.app.services.forensics.pdf_native import (
    check_baseline_alignment,
    check_signature_region,
)
from backend.app.services.render import render_document_pages


@pytest.fixture
def empty_signature_fixture(tmp_path: Path):
    pdf_path = tmp_path / "unsigned.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Insert signature text with nothing below it
    page.insert_text(fitz.Point(100, 700), "Applicant Signature", fontsize=12)
    doc.save(str(pdf_path))
    doc.close()

    render_dir = tmp_path / "unsigned_rendered"
    rendered = render_document_pages(pdf_path, render_dir, target_dpi=150)
    return pdf_path, rendered


@pytest.fixture
def signed_signature_fixture(tmp_path: Path):
    pdf_path = tmp_path / "signed.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(100, 700), "Applicant Signature", fontsize=12)
    # Draw dark strokes underneath the signature line
    shape = page.new_shape()
    shape.draw_line(fitz.Point(100, 720), fitz.Point(200, 740))
    shape.draw_line(fitz.Point(120, 750), fitz.Point(180, 715))
    shape.draw_line(fitz.Point(110, 730), fitz.Point(190, 730))
    shape.finish(color=(0, 0, 0), width=2.0)
    shape.commit()
    doc.save(str(pdf_path))
    doc.close()

    render_dir = tmp_path / "signed_rendered"
    rendered = render_document_pages(pdf_path, render_dir, target_dpi=150)
    return pdf_path, rendered


def test_signature_region_empty_detected(empty_signature_fixture):
    pdf_path, rendered_pages = empty_signature_fixture
    findings = check_signature_region(pdf_path, "DOC_EMPTY", rendered_pages)
    assert any(f.rule_id == "signature_region_empty" for f in findings)


def test_signature_stroke_present_no_empty_finding(signed_signature_fixture):
    pdf_path, rendered_pages = signed_signature_fixture
    findings = check_signature_region(pdf_path, "DOC_SIGNED", rendered_pages)
    assert not any(f.rule_id == "signature_region_empty" for f in findings)


def test_baseline_alignment_disparity(tmp_path: Path):
    pdf_path = tmp_path / "spliced_baseline.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Insert two text spans on roughly the same row with baseline y differing by 6 points
    page.insert_text(fitz.Point(100, 200), "Monthly Salary: ", fontsize=12)
    page.insert_text(fitz.Point(200, 206), "INR 85,000", fontsize=12)

    doc.save(str(pdf_path))
    doc.close()

    findings = check_baseline_alignment(pdf_path, "DOC_ALIGNED")
    assert any(f.rule_id == "baseline_alignment_anomaly" for f in findings)
