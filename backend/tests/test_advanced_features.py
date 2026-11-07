"""
Comprehensive test suite for the 5 advanced forensic capabilities:
1. Advanced image forensics and tampering localization
2. Multilingual and handwritten document processing
3. Intelligent cross-document relationship discovery
4. Advanced contextual reasoning and anomaly correlation
5. Evidence exploration and investigation analytics
"""

import tempfile
from pathlib import Path
import cv2
import numpy as np
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.contracts import (
    DocumentRecord,
    DocumentType,
    ExtractedField,
    FieldSource,
    Finding,
    FindingCategory,
    FindingStatus,
    FindingStrength,
    FindingTier,
    Investigation,
)
from backend.app.services.correlation.contextual_reasoning import (
    build_contextual_reasoning_and_clusters,
)
from backend.app.services.correlation.relationship_discovery import (
    build_cross_document_relationship_graph,
)
from backend.app.services.extraction.multilingual_handwriting import (
    detect_text_script_and_language,
    enrich_fields_with_multilingual_and_handwriting,
    is_handwritten_patch,
)
from backend.app.services.forensics.image_forensics import (
    detect_copy_move_forgery,
    detect_noise_discrepancies,
    generate_forensic_report,
    generate_tamper_heatmap,
)

client = TestClient(app)


def test_multilingual_script_and_language_detection():
    # Test Devanagari (Hindi)
    script, lang, detected = detect_text_script_and_language("भारतीय स्टेट बैंक")
    assert script == "Devanagari"
    assert lang == "hi"
    assert "Devanagari" in detected

    # Test Mixed English + Hindi
    script, lang, detected = detect_text_script_and_language("State Bank of India भारतीय स्टेट बैंक")
    assert "Devanagari" in detected
    assert "Latin" in detected

    # Test Latin (English)
    script, lang, detected = detect_text_script_and_language("Salary Payslip Corporate")
    assert script == "Latin"
    assert lang == "en"


def test_handwriting_patch_analysis():
    # Synthetic printed block (rigid rectangle)
    printed = np.ones((60, 140, 3), dtype=np.uint8) * 255
    cv2.putText(printed, "PRINTED", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    is_hw_p, _ = is_handwritten_patch(printed)
    assert is_hw_p is False

    # Synthetic handwritten-style cursive stroke
    hw_img = np.ones((60, 140, 3), dtype=np.uint8) * 255
    cv2.polylines(
        hw_img,
        [np.array([[10, 30], [25, 15], [35, 45], [50, 20], [70, 48], [95, 12], [120, 40]])],
        isClosed=False,
        color=(20, 20, 20),
        thickness=2,
    )
    is_hw_h, conf = is_handwritten_patch(hw_img)
    assert isinstance(is_hw_h, bool)
    assert 0.0 <= conf <= 1.0


def test_advanced_image_forensics_pipeline(tmp_path):
    # Create test image with localized noise anomaly
    img = np.ones((300, 300, 3), dtype=np.uint8) * 230
    # Add localized high-frequency noise square (spliced patch)
    noise = np.random.normal(0, 35, (60, 60, 3)).astype(np.uint8)
    img[80:140, 80:140] = cv2.add(img[80:140, 80:140], noise)

    img_file = tmp_path / "forensic_test.png"
    cv2.imwrite(str(img_file), img)

    # 1. Test noise discrepancy detection
    regions, max_delta = detect_noise_discrepancies(img)
    assert isinstance(regions, list)
    assert isinstance(max_delta, float)

    # 2. Test copy-move detection
    cm_regions, cm_matches = detect_copy_move_forgery(img)
    assert isinstance(cm_regions, list)

    # 3. Test comprehensive forensic report
    report = generate_forensic_report(img_file, "DOC-F1", page_num=1)
    assert report.doc_id == "DOC-F1"
    assert 0.0 <= report.tamper_score <= 1.0
    assert len(report.techniques_run) >= 3

    # 4. Test tamper heatmap generation
    heatmap_out = tmp_path / "heatmap.png"
    result_path = generate_tamper_heatmap(img_file, heatmap_out)
    assert result_path is not None
    assert result_path.exists()


def test_cross_document_relationship_discovery():
    doc1 = DocumentRecord(
        doc_id="DOC-PAN",
        filename="pan.pdf",
        sha256="abc1",
        type=DocumentType.PAN,
        fields=[
            ExtractedField(
                field_id="f1",
                doc_id="DOC-PAN",
                name="name",
                value="Rahul Sharma",
                raw_text="Rahul Sharma",
                confidence=0.98,
                source=FieldSource.OCR,
                page=1,
                bbox=[10, 10, 100, 30],
            ),
            ExtractedField(
                field_id="f2",
                doc_id="DOC-PAN",
                name="pan",
                value="ABCDE1234F",
                raw_text="ABCDE1234F",
                confidence=0.99,
                source=FieldSource.OCR,
                page=1,
                bbox=[10, 40, 100, 60],
            ),
        ],
    )

    doc2 = DocumentRecord(
        doc_id="DOC-AADHAAR",
        filename="aadhaar.pdf",
        sha256="abc2",
        type=DocumentType.AADHAAR,
        fields=[
            ExtractedField(
                field_id="f3",
                doc_id="DOC-AADHAAR",
                name="name",
                value="Rahul Sharma",
                raw_text="Rahul Sharma",
                confidence=0.97,
                source=FieldSource.OCR,
                page=1,
                bbox=[10, 10, 100, 30],
            ),
            ExtractedField(
                field_id="f4",
                doc_id="DOC-AADHAAR",
                name="aadhaar",
                value="1234 5678 9012",
                raw_text="1234 5678 9012",
                confidence=0.99,
                source=FieldSource.OCR,
                page=1,
                bbox=[10, 40, 100, 60],
            ),
        ],
    )

    graph = build_cross_document_relationship_graph([doc1, doc2])
    assert len(graph.nodes) >= 4  # 2 docs + at least 2 entities
    assert len(graph.edges) >= 3  # Doc linkages + Cross-validation edge

    # Confirm cross-validation edge was created
    cross_edges = [e for e in graph.edges if e.relation == "CROSS_VALIDATES"]
    assert len(cross_edges) >= 1
    assert graph.consistency_score >= 0.80


def test_contextual_reasoning_and_clusters():
    findings = [
        Finding(
            finding_id="F-1",
            tier=FindingTier.INCONSISTENCY,
            category=FindingCategory.CROSS_DOCUMENT,
            rule_id="name_mismatch_pan_aadhaar",
            title="Name Discrepancy between PAN and Aadhaar",
            evidence=[],
            signals=["name_levenshtein_distance"],
            strength=FindingStrength.MODERATE,
            confidence=0.88,
            status=FindingStatus.REQUIRES_INVESTIGATION,
            explanation="Name spelling variance detected between documents.",
        ),
        Finding(
            finding_id="F-2",
            tier=FindingTier.OBSERVATION,
            category=FindingCategory.FORENSIC,
            rule_id="ela_discontinuity",
            title="Localized compression artifact variation (ELA)",
            evidence=[],
            signals=["ela_compression_variance"],
            strength=FindingStrength.WEAK,
            confidence=0.65,
            status=FindingStatus.REQUIRES_INVESTIGATION,
            explanation="Error Level Analysis detected localized compression variation.",
        ),
    ]

    clusters = build_contextual_reasoning_and_clusters(findings, [])
    assert len(clusters) == 2

    themes = [c.theme for c in clusters]
    assert "Identity Divergence" in themes
    assert "Document Tampering" in themes

    # Check reasoning chains
    id_cluster = next(c for c in clusters if c.theme == "Identity Divergence")
    assert len(id_cluster.chain) == 1
    assert "Identity Signal" in id_cluster.chain[0].title
    assert "forbidden" not in id_cluster.synthesis_rationale.lower()


def test_investigation_analytics_and_forensics_endpoints():
    res_inv = client.post("/investigations")
    assert res_inv.status_code == 200
    inv_id = res_inv.json()["investigation_id"]

    # Test relationships endpoint
    res_rel = client.get(f"/investigations/{inv_id}/relationships")
    assert res_rel.status_code == 200
    rel_data = res_rel.json()
    assert "nodes" in rel_data
    assert "edges" in rel_data
    assert "consistency_score" in rel_data

    # Test analytics endpoint
    res_ana = client.get(f"/investigations/{inv_id}/analytics")
    assert res_ana.status_code == 200
    ana_data = res_ana.json()
    assert "tampering_risk_score" in ana_data
    assert "consistency_score" in ana_data
    assert "handwriting_stats" in ana_data
    assert "correlation_clusters" in ana_data
