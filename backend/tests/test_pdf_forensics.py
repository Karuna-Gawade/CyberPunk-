"""
Unit tests for PDF-native forensic inspection.
"""

from pathlib import Path
from backend.app.models.contracts import FindingTier
from backend.app.services.forensics.pdf_native import (
    check_pdf_metadata,
    check_incremental_updates,
    check_font_inconsistencies,
    check_hidden_text_spans,
)

BUNDLES_ROOT = Path("samples/bundles")


def test_pdf_font_inconsistency_detected():
    # tampered_07_font_edit has Courier font in salary net pay row
    slip_path = BUNDLES_ROOT / "tampered_07_font_edit" / "salary_slip.pdf"
    findings = check_font_inconsistencies(slip_path, "DOC-SLIP")
    assert len(findings) >= 1
    font_f = next(f for f in findings if f.rule_id in ("font_anomaly", "font_size_anomaly"))
    assert font_f.tier == FindingTier.OBSERVATION
    assert len(font_f.evidence) == 1
    assert font_f.evidence[0].bbox[2] > font_f.evidence[0].bbox[0]


def test_pdf_metadata_and_incremental_updates():
    # tampered_08 has Canva in producer and 2 %%EOF markers
    bank_path = BUNDLES_ROOT / "tampered_08_text_overlay" / "bank_statement.pdf"

    meta_findings = check_pdf_metadata(bank_path, "DOC-BANK")
    assert any(f.rule_id == "producer_editing_tool" for f in meta_findings)

    eof_findings = check_incremental_updates(bank_path, "DOC-BANK")
    assert any(f.rule_id == "incremental_updates_flag" for f in eof_findings)


def test_clean_bundle_pdf_forensics():
    # genuine_01 should produce zero font or producer anomalies
    slip_path = BUNDLES_ROOT / "genuine_01" / "salary_slip.pdf"
    findings = check_font_inconsistencies(slip_path, "DOC-SLIP")
    assert len(findings) == 0
