"""
Unit test for Tesseract 300 DPI -> 150 DPI coordinate system scaling.
Master Spec Section 3.3 requirement.
"""

from backend.app.services.extraction.tesseract_ocr import (
    scale_300_to_150_dpi,
    parse_tesseract_tsv,
)


def test_tesseract_coordinate_scaling():
    # Input at 300 DPI: left=200, top=400, width=100, height=50
    # Expected at 150 DPI: x0=100, y0=200, x1=150, y1=225
    scaled_box = scale_300_to_150_dpi(200, 400, 100, 50)
    assert scaled_box == [100, 200, 150, 225]


def test_tesseract_tsv_parsing_and_normalization():
    tsv_sample = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t100\t200\t80\t40\t95\tSalary\n"
        "5\t1\t1\t1\t1\t2\t190\t200\t60\t40\t-1\t\n"  # should be ignored
        "5\t1\t1\t1\t1\t3\t260\t200\t100\t40\t88\tSlip\n"
    )
    words = parse_tesseract_tsv(tsv_sample)
    assert len(words) == 2
    assert words[0]["text"] == "Salary"
    assert words[0]["confidence"] == 0.95
    assert words[0]["bbox"] == [50, 100, 90, 120]  # scaled by 0.5
    assert words[1]["text"] == "Slip"
    assert words[1]["confidence"] == 0.88
    assert words[1]["bbox"] == [130, 100, 180, 120]
