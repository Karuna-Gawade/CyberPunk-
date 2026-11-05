"""
Unit tests for image-level forensics (ELA and noise analysis).
Verifies that image forensics signals are strictly weak supporting observations.
"""

from pathlib import Path
from backend.app.models.contracts import FindingStrength, FindingTier
from backend.app.services.forensics.image_forensics import (
    compute_ela_difference,
    run_image_forensics_checks,
)

RENDERED_PATH = Path("data/rendered")


def test_ela_computation_and_weak_tier_guarantee():
    # Use any rendered page image if available or test with blank/dummy image
    import cv2
    import numpy as np
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        # Create a synthetic image with a high-contrast square
        img = np.ones((400, 400, 3), dtype=np.uint8) * 240
        img[100:200, 100:200] = [10, 20, 200]
        cv2.imwrite(str(tmp_path), img)

        diff, mse = compute_ela_difference(tmp_path)
        assert diff.shape == img.shape
        assert mse >= 0.0

        findings = run_image_forensics_checks(tmp_path, "DOC-TEST", page_num=1)
        for f in findings:
            # Non-negotiable rule: ELA must NEVER exceed Observation and must be WEAK
            assert f.tier == FindingTier.OBSERVATION
            assert f.strength == FindingStrength.WEAK
            assert "weak supporting signal" in f.explanation
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
