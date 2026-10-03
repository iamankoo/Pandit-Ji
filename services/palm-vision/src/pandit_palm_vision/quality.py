"""Image quality gate: ACCEPT, RETRY or REJECT before any palm-line analysis (Phase 13).

Standards PM-09 and PM-31: **no numeric threshold is hardcoded for production.** Every
threshold lives in a versioned :class:`QualityConfig` and is ``None`` until it is calibrated on
approved evaluation data. A check whose threshold is ``None`` reports ``UNCERTAIN``
(``THRESHOLD_CALIBRATION_REQUIRED``), and a gate with an uncertain check never ACCEPTs: the
outcome is ``RETRY``. The default configuration therefore ACCEPTs nothing, by design.

``fixture_quality_config()`` supplies values for synthetic fixtures and tests only. They are
labelled ``FIXTURE_ONLY``, travel into the provenance of every fact, and keep the evidence
bundle ``production_ready=False``.

Outcomes: ``REJECT`` for structural impossibility (no hand, a degenerate hand, an undecodable
image: rejected before this module); ``RETRY`` for a retake that may succeed (a failed or
uncalibrated check, several hands in view). A missing measurement is never guessed.

Every metric is an integer (fixed-point, scale stated per check) so the result is structured and
hashable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from pandit_contracts.palm import (
    CalibrationStatus,
    QualityCheckResult,
    QualityCheckStatus,
    QualityOutcome,
    QualityResult,
)
from pandit_contracts.palm_canonical import BASIS_POINTS, sha256_hex

from pandit_palm_vision.frame import PALM_POLYGON_LANDMARKS, landmarks_px
from pandit_palm_vision.hand import MIDDLE_MCP, WRIST, HandCandidate
from pandit_palm_vision.image_input import ImageInput

QUALITY_CONFIG_VERSION = "1"
MIN_ROI_PIXELS = 64
CHECKS = (
    "blur",
    "exposure",
    "contrast",
    "framing",
    "occlusion",
    "orientation",
    "resolution",
    "palm_visibility",
    "background",
)
# Scales of the integer metrics (value = metric / scale).
METRIC_SCALES: dict[str, str] = {
    "blur": "laplacian_variance_x100",
    "exposure": "clipped_pixel_fraction_bp",
    "contrast": "p95_minus_p5_luminance_x100",
    "framing": "min_landmark_border_margin_bp",
    "occlusion": "detector_presence_bp",
    "orientation": "abs_axis_angle_from_vertical_centidegrees",
    "resolution": "palm_unit_pixels_x100",
    "palm_visibility": "palm_polygon_inside_frame_bp",
    "background": "background_laplacian_variance_x100",
}


@dataclass(frozen=True)
class QualityConfig:
    """Versioned quality thresholds. ``None`` means calibration required (no value invented)."""

    calibration_status: CalibrationStatus = CalibrationStatus.CALIBRATION_REQUIRED
    version: str = QUALITY_CONFIG_VERSION
    blur_min: int | None = None  # laplacian variance x100, at least
    exposure_max_bp: int | None = None  # clipped fraction, at most
    contrast_min: int | None = None  # p95-p5 x100, at least
    framing_margin_min_bp: int | None = None  # at least (may be negative to allow clipping)
    occlusion_presence_min_bp: int | None = None  # detector presence, at least
    orientation_max_centideg: int | None = None  # absolute axis angle, at most
    resolution_min_x100: int | None = None  # palm unit in pixels x100, at least
    palm_visibility_min_bp: int | None = None  # palm polygon inside the frame, at least
    background_max: int | None = None  # background laplacian variance x100, at most

    def thresholds(self) -> dict[str, int | None]:
        return {
            "blur": self.blur_min,
            "exposure": self.exposure_max_bp,
            "contrast": self.contrast_min,
            "framing": self.framing_margin_min_bp,
            "occlusion": self.occlusion_presence_min_bp,
            "orientation": self.orientation_max_centideg,
            "resolution": self.resolution_min_x100,
            "palm_visibility": self.palm_visibility_min_bp,
            "background": self.background_max,
        }

    @property
    def config_id(self) -> str:
        content: dict[str, Any] = {
            "version": self.version,
            "calibration_status": self.calibration_status.value,
            "thresholds": self.thresholds(),
        }
        return "QC-" + sha256_hex(content)[:16]


DEFAULT_QUALITY_CONFIG = QualityConfig()


def fixture_quality_config() -> QualityConfig:
    """Values for synthetic fixtures and tests ONLY (never a production setting)."""
    return QualityConfig(
        calibration_status=CalibrationStatus.FIXTURE_ONLY,
        blur_min=5_000,
        exposure_max_bp=2_000,
        contrast_min=2_000,
        framing_margin_min_bp=200,
        occlusion_presence_min_bp=5_000,
        orientation_max_centideg=3_000,
        resolution_min_x100=10_000,
        palm_visibility_min_bp=9_000,
        background_max=300_000,
    )


@dataclass(frozen=True)
class QualityEvaluation:
    result: QualityResult
    hand: HandCandidate | None  # the single detected hand when exactly one was found


def _not_evaluated(reason: str) -> tuple[QualityCheckResult, ...]:
    return tuple(
        QualityCheckResult(check=c, status=QualityCheckStatus.NOT_EVALUATED, reason=reason)
        for c in CHECKS
    )


def _finish(
    outcome: QualityOutcome,
    checks: tuple[QualityCheckResult, ...],
    reasons: tuple[str, ...],
    config: QualityConfig,
) -> QualityResult:
    return QualityResult(
        outcome=outcome,
        checks=checks,
        reasons=reasons,
        config_id=config.config_id,
        config_version=config.version,
        calibration_status=config.calibration_status,
    )


def _palm_mask(px: np.ndarray, width: int, height: int) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    polygon = np.round(px[list(PALM_POLYGON_LANDMARKS)]).astype(np.int32)
    cv2.fillPoly(mask, [polygon], 255)
    return mask


def _polygon_area(points: np.ndarray) -> float:
    x, y = points[:, 0], points[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def measure(image: ImageInput, hand: HandCandidate) -> dict[str, int | None]:
    """The integer metric of every check (``None`` where it could not be measured)."""
    width, height = image.width, image.height
    px = landmarks_px(hand, width, height)
    gray = cv2.cvtColor(image.pixels, cv2.COLOR_BGR2GRAY)
    mask = _palm_mask(px, width, height)
    inside = mask > 0
    metrics: dict[str, int | None] = dict.fromkeys(CHECKS)

    lap = cv2.Laplacian(gray, cv2.CV_64F)
    if int(inside.sum()) >= MIN_ROI_PIXELS:
        roi = gray[inside].astype(np.float64)
        metrics["blur"] = round(float(lap[inside].var()) * 100)
        low = float((roi <= 5).mean())
        high = float((roi >= 250).mean())
        metrics["exposure"] = round(max(low, high) * BASIS_POINTS)
        p5, p95 = np.percentile(roi, [5, 95])
        metrics["contrast"] = round(float(p95 - p5) * 100)

    norm = np.asarray(hand.landmarks, dtype=np.float64)
    margins = np.minimum(
        np.minimum(norm[:, 0], 1.0 - norm[:, 0]), np.minimum(norm[:, 1], 1.0 - norm[:, 1])
    )
    metrics["framing"] = round(float(np.min(margins)) * BASIS_POINTS)
    metrics["occlusion"] = hand.presence_bp

    vector = px[MIDDLE_MCP] - px[WRIST]
    unit = float(np.hypot(vector[0], vector[1]))
    metrics["resolution"] = round(unit * 100)
    if unit > 1e-9:
        # angle between the wrist->middle vector and "up" in the image (0, -1)
        angle = float(np.degrees(np.arctan2(vector[0], -vector[1])))
        metrics["orientation"] = round(abs(angle) * 100)

    area = _polygon_area(px[list(PALM_POLYGON_LANDMARKS)])
    if area > 1e-9:
        metrics["palm_visibility"] = round(min(1.0, float(inside.sum()) / area) * BASIS_POINTS)

    hull = cv2.convexHull(np.round(px).astype(np.int32))
    hull_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillConvexPoly(hull_mask, hull, 255)
    background = cv2.dilate(hull_mask, np.ones((15, 15), dtype=np.uint8)) == 0
    if int(background.sum()) >= MIN_ROI_PIXELS:
        metrics["background"] = round(float(lap[background].var()) * 100)
    return metrics


_AT_LEAST = {"blur", "contrast", "framing", "occlusion", "resolution", "palm_visibility"}


def _judge(check: str, metric: int | None, threshold: int | None) -> QualityCheckResult:
    if metric is None:
        return QualityCheckResult(
            check=check,
            status=QualityCheckStatus.NOT_EVALUATED,
            threshold_fixed=threshold,
            reason="METRIC_NOT_MEASURABLE",
        )
    if threshold is None:
        return QualityCheckResult(
            check=check,
            status=QualityCheckStatus.UNCERTAIN,
            metric_fixed=metric,
            reason="THRESHOLD_CALIBRATION_REQUIRED",
        )
    ok = metric >= threshold if check in _AT_LEAST else metric <= threshold
    return QualityCheckResult(
        check=check,
        status=QualityCheckStatus.PASS if ok else QualityCheckStatus.FAIL,
        metric_fixed=metric,
        threshold_fixed=threshold,
        reason=None if ok else f"{check.upper()}_OUTSIDE_THRESHOLD",
    )


def evaluate_quality(
    image: ImageInput,
    candidates: tuple[HandCandidate, ...],
    config: QualityConfig = DEFAULT_QUALITY_CONFIG,
) -> QualityEvaluation:
    if not candidates:
        return QualityEvaluation(
            _finish(
                QualityOutcome.REJECT, _not_evaluated("NO_HAND"), ("NO_HAND_DETECTED",), config
            ),
            None,
        )
    if len(candidates) > 1:
        return QualityEvaluation(
            _finish(
                QualityOutcome.RETRY,
                _not_evaluated("MULTIPLE_HANDS"),
                ("MULTIPLE_HANDS_DETECTED",),
                config,
            ),
            None,
        )
    hand = candidates[0]
    px = landmarks_px(hand, image.width, image.height)
    if float(np.hypot(*(px[MIDDLE_MCP] - px[WRIST]))) < 1e-6:
        return QualityEvaluation(
            _finish(
                QualityOutcome.REJECT,
                _not_evaluated("DEGENERATE_HAND"),
                ("DEGENERATE_HAND_GEOMETRY",),
                config,
            ),
            hand,
        )
    metrics = measure(image, hand)
    thresholds = config.thresholds()
    checks = tuple(_judge(c, metrics[c], thresholds[c]) for c in CHECKS)
    failed = [c for c in checks if c.status is QualityCheckStatus.FAIL]
    uncertain = [
        c
        for c in checks
        if c.status in {QualityCheckStatus.UNCERTAIN, QualityCheckStatus.NOT_EVALUATED}
    ]
    if failed:
        reasons = tuple(sorted(c.reason or c.check for c in failed))
        outcome = QualityOutcome.RETRY
    elif uncertain:
        reasons = tuple(sorted({c.reason or c.check for c in uncertain}))
        outcome = QualityOutcome.RETRY
    else:
        reasons = ()
        outcome = QualityOutcome.ACCEPT
    return QualityEvaluation(_finish(outcome, checks, reasons, config), hand)
