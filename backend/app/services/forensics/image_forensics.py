"""
Advanced Image Forensics Engine using OpenCV and NumPy.
Multi-signal image forensics and tampering localization:
1. Error Level Analysis (ELA) via JPEG re-compression difference
2. Noise Residual Discrepancy analysis (high-pass Laplacian variance across localized blocks)
3. Copy-Move Forgery Detection (ORB keypoint matching with geometric consistency)
4. Splicing Edge Boundary Discontinuity detection
5. Tamper localization heatmaps and region bounding boxes

Strict rule: Image forensic signals alone NEVER exceed Observation tier
and NEVER serve as standalone proof of forgery (strictly advisory under ISO/IEC 27037).
"""

import math
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from backend.app.models.contracts import (
    EvidenceItem,
    Finding,
    FindingCategory,
    FindingStatus,
    FindingStrength,
    FindingTier,
    ForensicAnalysisReport,
    ReviewerAction,
    TamperRegion,
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

        if recompressed is None or recompressed.shape != img.shape:
            return np.zeros((10, 10, 3), dtype=np.uint8), 0.0

        # Absolute difference scaled up for visualization
        diff = cv2.absdiff(img, recompressed)
        diff_scaled = cv2.convertScaleAbs(diff, alpha=15.0)

        mse = float(np.mean(diff.astype(np.float32) ** 2))
        return diff_scaled, mse
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def detect_noise_discrepancies(img: np.ndarray, block_size: int = 32) -> Tuple[List[TamperRegion], float]:
    """
    Analyzes localized sensor/high-frequency noise variance using Laplacian residuals.
    Spliced elements from different origins display distinct noise levels from the background canvas.
    Returns: (list_of_regions, max_variance_delta)
    """
    if img is None or len(img.shape) < 2:
        return [], 0.0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    h, w = gray.shape[:2]

    if h < block_size * 2 or w < block_size * 2:
        return [], 0.0

    # High-pass Laplacian filter to isolate noise residuals
    laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
    lap_sq = laplacian ** 2

    # Compute variance across grid blocks
    variances = []
    block_coords = []
    step = block_size

    for y in range(0, h - block_size + 1, step):
        for x in range(0, w - block_size + 1, step):
            b = lap_sq[y:y + block_size, x:x + block_size]
            v = float(np.mean(b))
            variances.append(v)
            block_coords.append((x, y, x + block_size, y + block_size))

    if not variances:
        return [], 0.0

    med_var = float(np.median(variances))
    std_var = float(np.std(variances))
    if std_var < 1.0:
        return [], 0.0

    regions = []
    max_delta = 0.0

    for v, (x0, y0, x1, y1) in zip(variances, block_coords):
        z_score = abs(v - med_var) / std_var
        if z_score > 3.2:
            delta = float(round(z_score, 2))
            if delta > max_delta:
                max_delta = delta
            regions.append(
                TamperRegion(
                    bbox=[x0, y0, x1, y1],
                    score=min(0.95, round(z_score / 6.0, 2)),
                    technique="noise_discrepancy",
                    description=f"Localized noise variance discrepancy (Z-score: {delta:.1f}\u03c3 vs document baseline)",
                )
            )

    return regions[:5], max_delta


def detect_copy_move_forgery(img: np.ndarray) -> Tuple[List[TamperRegion], int]:
    """
    Detects duplicated or cloned image content using ORB keypoint matching with geometric distance filtering.
    Identifies identical stamps, repeated signatures, or copied numeric patches.
    Returns: (list_of_tamper_regions, match_count)
    """
    if img is None:
        return [], 0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    h, w = gray.shape[:2]

    # Initialize ORB detector
    orb = cv2.ORB_create(nfeatures=1200, fastThreshold=15)
    keypoints, descriptors = orb.detectAndCompute(gray, None)

    if descriptors is None or len(descriptors) < 20:
        return [], 0

    # Brute-force matcher with k-NN (k=2)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(descriptors, descriptors, k=3)

    min_pixel_distance = 60.0
    valid_pairs = []

    for m in matches:
        if len(m) >= 2:
            # First match is the keypoint itself (dist=0); check second and third
            for candidate in m[1:]:
                if candidate.distance < 45:
                    pt1 = np.array(keypoints[candidate.queryIdx].pt)
                    pt2 = np.array(keypoints[candidate.trainIdx].pt)
                    dist = float(np.linalg.norm(pt1 - pt2))
                    if dist >= min_pixel_distance:
                        valid_pairs.append((pt1, pt2, dist))

    if len(valid_pairs) < 8:
        return [], len(valid_pairs)

    # Cluster paired coordinates to form bounding boxes
    all_pts = []
    for pt1, pt2, _ in valid_pairs:
        all_pts.extend([pt1, pt2])

    pts_arr = np.array(all_pts)
    x_min = int(max(0, np.min(pts_arr[:, 0]) - 15))
    y_min = int(max(0, np.min(pts_arr[:, 1]) - 15))
    x_max = int(min(w, np.max(pts_arr[:, 0]) + 15))
    y_max = int(min(h, np.max(pts_arr[:, 1]) + 15))

    region = TamperRegion(
        bbox=[x_min, y_min, x_max, y_max],
        score=min(0.92, round(len(valid_pairs) / 25.0, 2)),
        technique="copy_move",
        description=f"Duplicated texture/keypoint clusters detected ({len(valid_pairs)} cross-block feature matches)",
    )

    return [region], len(valid_pairs)


def detect_splicing_edge_discontinuities(img: np.ndarray) -> List[TamperRegion]:
    """
    Detects rectangular or sharp artificial gradient boundaries indicating pasted patch borders.
    """
    if img is None:
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    h, w = gray.shape[:2]

    # Canny edge detection followed by contour analysis
    edges = cv2.Canny(gray, 60, 180)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        # Check for sharp artificial rectangular boxes of significant size (e.g. pasted text patches)
        if 40 < bw < w * 0.7 and 20 < bh < h * 0.4:
            area = cv2.contourArea(c)
            bbox_area = bw * bh
            if bbox_area > 0 and (area / bbox_area) > 0.88:  # Highly rectangular bounding contour
                regions.append(
                    TamperRegion(
                        bbox=[x, y, x + bw, y + bh],
                        score=0.72,
                        technique="edge_boundary",
                        description="Abrupt rectangular boundary discontinuity (potential pasted patch border)",
                    )
                )

    return regions[:3]


def generate_tamper_heatmap(image_path: Path, output_path: Path) -> Optional[Path]:
    """
    Generates a visual forensic composite heatmap blending the original image with
    normalized ELA difference and noise residual intensity.
    Saves the rendered PNG to output_path.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return None

    h, w = img.shape[:2]
    ela_map, _ = compute_ela_difference(image_path, quality=90)
    gray_ela = cv2.cvtColor(ela_map, cv2.COLOR_BGR2GRAY) if len(ela_map.shape) == 3 else ela_map

    # Normalize ELA to 0-255
    norm_ela = cv2.normalize(gray_ela, None, 0, 255, cv2.NORM_MINMAX)

    # Compute high-pass noise
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    lap = np.abs(cv2.Laplacian(gray_img, cv2.CV_64F))
    norm_lap = cv2.normalize(lap, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    # Blend ELA and Noise into composite heat map
    composite = cv2.addWeighted(norm_ela, 0.65, norm_lap, 0.35, 0)
    colored_heat = cv2.applyColorMap(composite, cv2.COLORMAP_JET)

    # Alpha blend overlay over original image
    blend = cv2.addWeighted(img, 0.55, colored_heat, 0.45, 0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), blend)
    return output_path


def generate_forensic_report(image_path: Path, doc_id: str, page_num: int = 1) -> ForensicAnalysisReport:
    """
    Executes full multi-method forensics and compiles a structured ForensicAnalysisReport.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return ForensicAnalysisReport(doc_id=doc_id, page=page_num)

    # 1. ELA
    diff_map, mean_mse = compute_ela_difference(image_path, quality=90)
    gray_diff = cv2.cvtColor(diff_map, cv2.COLOR_BGR2GRAY) if len(diff_map.shape) == 3 else diff_map
    h, w = gray_diff.shape[:2]
    block_h, block_w = max(20, h // 8), max(20, w // 8)

    max_block_val = 0.0
    ela_box = [0, 0, 0, 0]
    for y in range(0, h - block_h, block_h):
        for x in range(0, w - block_w, block_w):
            b = gray_diff[y:y + block_h, x:x + block_w]
            b_mean = float(np.mean(b))
            if b_mean > max_block_val:
                max_block_val = b_mean
                ela_box = [x, y, x + block_w, y + block_h]

    regions: List[TamperRegion] = []
    if max_block_val > 45.0 and mean_mse > 1.5:
        regions.append(
            TamperRegion(
                bbox=ela_box,
                score=min(0.85, round(max_block_val / 80.0, 2)),
                technique="ela",
                description=f"Localized compression artifact variation (ELA mean: {max_block_val:.1f})",
            )
        )

    # 2. Noise Discrepancies
    noise_regions, max_delta = detect_noise_discrepancies(img)
    regions.extend(noise_regions)

    # 3. Copy-Move
    copy_regions, match_count = detect_copy_move_forgery(img)
    regions.extend(copy_regions)

    # 4. Splicing Edge Boundaries
    edge_regions = detect_splicing_edge_discontinuities(img)
    regions.extend(edge_regions)

    # Calculate overall tamper risk score (0.0 to 1.0)
    scores = [r.score for r in regions]
    tamper_score = min(0.95, round(max(scores) if scores else 0.05, 2))
    is_anomalous = len(regions) > 0 and tamper_score >= 0.60

    return ForensicAnalysisReport(
        doc_id=doc_id,
        page=page_num,
        tamper_score=tamper_score,
        is_anomalous=is_anomalous,
        techniques_run=["ela", "noise_discrepancy", "copy_move", "edge_boundary"],
        regions=regions,
        ela_mean_mse=round(mean_mse, 2),
        noise_variance_delta=round(max_delta, 2),
        copy_move_matches=match_count,
        heatmap_available=True,
    )


def run_image_forensics_checks(image_path: Path, doc_id: str, page_num: int = 1) -> List[Finding]:
    """
    Executes multi-method image forensics checks.
    Treats all image-level signals as strictly WEAK supporting observations under ISO/IEC 27037.
    """
    findings = []
    report = generate_forensic_report(image_path, doc_id, page_num=page_num)

    for idx, r in enumerate(report.regions):
        sig_id = f"ANM-{r.technique.upper()}-{doc_id}-{page_num}-{idx}"
        title_map = {
            "ela": "Localized JPEG compression artifact variation (ELA)",
            "noise_discrepancy": "Localized high-frequency sensor noise discrepancy",
            "copy_move": "Duplicate texture / copy-move feature cluster",
            "edge_boundary": "Abrupt rectangular boundary gradient discontinuity",
        }
        title = title_map.get(r.technique, "Localized surface pattern anomaly")

        findings.append(
            Finding(
                finding_id=sig_id,
                tier=FindingTier.OBSERVATION,
                category=FindingCategory.FORENSIC,
                rule_id=f"{r.technique}_discontinuity",
                title=title,
                evidence=[EvidenceItem(doc_id=doc_id, page=page_num, bbox=r.bbox, label=f"Anomaly: {r.technique}")],
                signals=[f"image_{r.technique}_variance"],
                strength=FindingStrength.WEAK,
                confidence=r.score,
                status=FindingStatus.REQUIRES_INVESTIGATION,
                explanation=(
                    f"{r.description}. "
                    "NOTE: Image-level forensic signals are weak supporting signals; normal compression, rescanning, and digital rasterization can trigger false positives."
                ),
                reviewer=ReviewerAction(),
            )
        )

    return findings
