from __future__ import annotations

from typing import Any

import pytest
from pandit_contracts.palm import (
    CalibrationStatus,
    HandSide,
    QualityCheckStatus,
    QualityOutcome,
)

from pandit_palm_vision.quality import (
    CHECKS,
    DEFAULT_QUALITY_CONFIG,
    METRIC_SCALES,
    QualityConfig,
    evaluate_quality,
    fixture_quality_config,
    measure,
)
from pandit_palm_vision.synthetic import make_synthetic_palm

FIXTURE = fixture_quality_config()


def _evaluate(**kwargs: Any) -> Any:
    palm = make_synthetic_palm(HandSide.RIGHT, seed=3, **kwargs)
    return evaluate_quality(palm.image, (palm.candidate(),), FIXTURE).result


def test_a_clean_synthetic_hand_is_accepted_with_the_fixture_config() -> None:
    result = _evaluate()
    assert result.outcome is QualityOutcome.ACCEPT
    assert all(c.status is QualityCheckStatus.PASS for c in result.checks)
    assert result.calibration_status is CalibrationStatus.FIXTURE_ONLY
    assert {c.check for c in result.checks} == set(CHECKS)


def test_the_default_config_has_no_calibrated_threshold_and_never_accepts() -> None:
    assert DEFAULT_QUALITY_CONFIG.calibration_status is CalibrationStatus.CALIBRATION_REQUIRED
    assert all(v is None for v in DEFAULT_QUALITY_CONFIG.thresholds().values())
    palm = make_synthetic_palm(HandSide.RIGHT)
    result = evaluate_quality(palm.image, (palm.candidate(),), DEFAULT_QUALITY_CONFIG).result
    assert result.outcome is QualityOutcome.RETRY
    assert all(c.status is QualityCheckStatus.UNCERTAIN for c in result.checks)
    assert result.reasons == ("THRESHOLD_CALIBRATION_REQUIRED",)
    # the measured value is still reported, but no verdict is given without a threshold
    assert all(c.metric_fixed is not None for c in result.checks)
    assert all(c.threshold_fixed is None for c in result.checks)


@pytest.mark.parametrize(
    ("kwargs", "check"),
    [
        ({"blur_sigma": 6.0}, "blur"),
        ({"brightness": 120, "contrast": 0.4}, "exposure"),
        ({"brightness": -200}, "exposure"),
        ({"brightness": 60, "contrast": 0.15}, "contrast"),
        ({"shift": (0.45, 0.0)}, "framing"),
        ({"rotation_deg": 40.0}, "orientation"),
        ({"scale": 0.25}, "resolution"),
        ({"shift": (0.45, 0.0)}, "palm_visibility"),
        ({"background": "noisy", "noise_sigma": 25.0}, "background"),
    ],
)
def test_each_failing_check_blocks_acceptance(kwargs: dict[str, Any], check: str) -> None:
    result = _evaluate(**kwargs)
    assert result.outcome is QualityOutcome.RETRY, kwargs
    failed = {c.check for c in result.checks if c.status is QualityCheckStatus.FAIL}
    assert check in failed
    assert result.reasons  # never silently empty


def test_low_detector_presence_is_an_occlusion_failure() -> None:
    palm = make_synthetic_palm(HandSide.RIGHT)
    low = palm.candidate(presence_bp=3000)
    result = evaluate_quality(palm.image, (low,), FIXTURE).result
    assert result.outcome is QualityOutcome.RETRY
    assert {c.check for c in result.checks if c.status is QualityCheckStatus.FAIL} == {"occlusion"}


def test_no_hand_is_rejected_and_nothing_is_guessed() -> None:
    palm = make_synthetic_palm(HandSide.RIGHT)
    evaluation = evaluate_quality(palm.image, (), FIXTURE)
    assert evaluation.result.outcome is QualityOutcome.REJECT
    assert evaluation.result.reasons == ("NO_HAND_DETECTED",)
    assert evaluation.hand is None
    assert all(c.status is QualityCheckStatus.NOT_EVALUATED for c in evaluation.result.checks)


def test_several_hands_mean_retry_not_a_choice() -> None:
    palm = make_synthetic_palm(HandSide.RIGHT)
    evaluation = evaluate_quality(palm.image, (palm.candidate(), palm.candidate()), FIXTURE)
    assert evaluation.result.outcome is QualityOutcome.RETRY
    assert evaluation.result.reasons == ("MULTIPLE_HANDS_DETECTED",)
    assert evaluation.hand is None


def test_a_degenerate_hand_is_rejected() -> None:
    palm = make_synthetic_palm(HandSide.RIGHT)
    flat = tuple((0.5, 0.5) for _ in range(21))
    candidate = type(palm.candidate())(flat, "Right", 9000, 9000)
    result = evaluate_quality(palm.image, (candidate,), FIXTURE).result
    assert result.outcome is QualityOutcome.REJECT
    assert result.reasons == ("DEGENERATE_HAND_GEOMETRY",)


def test_the_quality_result_is_structured_hashable_and_integer_only() -> None:
    result = _evaluate()
    assert result.quality_ref.startswith("QR-")
    assert result == _evaluate()
    for check in result.checks:
        assert check.metric_fixed is None or isinstance(check.metric_fixed, int)
    assert set(METRIC_SCALES) == set(CHECKS)


def test_the_config_identity_changes_with_a_threshold_or_status() -> None:
    base = QualityConfig()
    assert base.config_id == QualityConfig().config_id
    assert QualityConfig(blur_min=1).config_id != base.config_id
    assert (
        QualityConfig(calibration_status=CalibrationStatus.FIXTURE_ONLY).config_id != base.config_id
    )


def test_metrics_are_deterministic() -> None:
    palm = make_synthetic_palm(HandSide.LEFT, seed=9)
    assert measure(palm.image, palm.candidate()) == measure(palm.image, palm.candidate())
