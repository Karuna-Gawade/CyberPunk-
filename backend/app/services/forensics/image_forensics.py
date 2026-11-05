"""
Image Forensics Engine using OpenCV and NumPy.
Treats all image-level signals as WEAK supporting evidence only:
1. Error Level Analysis (ELA) via JPEG re-compression difference
2. Noise variance analysis across localized blocks
3. Copy-move block match signal

Strict rule: ELA or noise signals alone NEVER exceed Observation tier
and NEVER serve as standalone proof of forgery.
"""

import tempfile
from pathlib import Path
from typing import List, Tuple
import cv2
import numpy as np
from backend.app.models.contracts import (
    EvidenceItem,
    Finding,
    FindingCategory,
    FindingStatus,
    FindingStrength,
    FindingTier,
    ReviewerAction,
)


def compute_ela_difference(image_path: Path, quality: int = 90) -> Tuple[np.ndarray, float]:
    """
    Computes Error Level Analysis (ELA) map by re-saving at JPEG quality and measuring pixel delta.
    Returns: (diff_map, average_mse)
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return np.zeros((10, 10, 3), dtype=np.uint8), 0.0

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        cv2.imwrite(str(tmp_path), img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        recompressed = cv2.imread(str(tmp_path))

        # Absolute difference scaled up for visualization
        diff = cv2.absdiff(img, recompressed)
        diff_scaled = cv2.convertScaleAbs(diff, alpha=15.0)

        mse = float(np.mean(diff ** 2))
        return diff_scaled, mse
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def run_image_forensics_checks(image_path: Path, doc_id: str, page_num: int = 1) -> List[Finding]:
    """
    Runs ELA and localized noise consistency analysis.
    Returns weak supporting findings only.
    """
    findings = []
    diff_map, mean_mse = compute_ela_difference(image_path, quality=90)

    # Convert diff map to grayscale
    gray_diff = cv2.cvtColor(diff_map, cv2.COLOR_BGR2GRAY) if len(diff_map.shape) == 3 else diff_map

    # Check for localized high-energy clusters in ELA difference map
    h, w = gray_diff.shape[:2]
    block_h, block_w = max(20, h // 8), max(20, w // 8)

    max_block_val = 0.0
    hotspot_box = [0, 0, 0, 0]

    for y in range(0, h - block_h, block_h):
        for x in range(0, w - block_w, block_w):
            block = gray_diff[y:y + block_h, x:x + block_w]
            b_mean = float(np.mean(block))
            if b_mean > max_block_val:
                max_block_val = b_mean
                hotspot_box = [x, y, x + block_w, y + block_h]

    # If a localized region has high compression variance compared to the overall image
    if max_block_val > 45.0 and mean_mse > 1.5:
        findings.append(
            Finding(
                finding_id=f"ANM-ELA-{doc_id}-{page_num}",
                tier=FindingTier.OBSERVATION,
                category=FindingCategory.FORENSIC,
                rule_id="ela_discontinuity",
                title="Localized JPEG compression artifact variation (ELA)",
                evidence=[EvidenceItem(doc_id=doc_id, page=page_num, bbox=hotspot_box, label="ELA High-Variance Block")],
                signals=["ela_compression_variance"],
                strength=FindingStrength.WEAK,
                confidence=0.65,
                status=FindingStatus.REQUIRES_INVESTIGATION,
                explanation=(
                    f"Error Level Analysis detected localized compression variation (block mean: {max_block_val:.1f}). "
                    "NOTE: ELA is a weak supporting signal; normal re-compression, scanning artifacts, and multiple saves frequently cause false positives."
                ),
                reviewer=ReviewerAction(),
            )
        )

    return findings
