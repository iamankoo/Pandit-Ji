from __future__ import annotations

import pytest
from pandit_contracts.palm import HandSide, QualityOutcome

from pandit_palm_vision.hand import (
    INDEX_MCP,
    PINKY_MCP,
    WRIST,
    HandCandidate,
    MappingHandDetector,
    StaticHandDetector,
    best_candidate,
)
from pandit_palm_vision.image_input import CaptureContext
from pandit_palm_vision.pipeline import PalmPipeline
from pandit_palm_vision.quality import fixture_quality_config
from pandit_palm_vision.side import classify_side, geometric_side
from pandit_palm_vision.synthetic import SyntheticPalm, make_synthetic_palm

FACING = CaptureContext(mirrored=False, palm_facing=True)


def test_a_right_hand_is_a_right_hand(right_palm: SyntheticPalm) -> None:
    palm = right_palm
    result = classify_side(palm.candidate(False), FACING, False)
    assert result.side is HandSide.RIGHT and not result.reasons


def test_a_left_hand_is_a_left_hand(left_palm: SyntheticPalm) -> None:
    palm = left_palm
    result = classify_side(palm.candidate(False), FACING, False)
    assert result.side is HandSide.LEFT and not result.reasons


def test_the_geometry_convention_is_consistent_for_both_hands(
    right_palm: SyntheticPalm, left_palm: SyntheticPalm
) -> None:
    assert geometric_side(right_palm.landmarks) is HandSide.RIGHT
    assert geometric_side(left_palm.landmarks) is HandSide.LEFT


@pytest.mark.parametrize(
    ("context", "assumes", "reason"),
    [
        (CaptureContext(mirrored=False, palm_facing=None), False, "PALM_FACING_UNKNOWN"),
        (CaptureContext(mirrored=False, palm_facing=False), False, "NOT_PALM_FACING"),
        (CaptureContext(mirrored=None, palm_facing=True), False, "INPUT_MIRRORING_UNKNOWN"),
        (FACING, None, "DETECTOR_MIRRORING_ASSUMPTION_UNKNOWN"),
    ],
)
def test_the_side_is_never_guessed_when_the_capture_is_unknown(
    right_palm: SyntheticPalm, context: CaptureContext, assumes: bool | None, reason: str
) -> None:
    result = classify_side(right_palm.candidate(False), context, assumes)
    assert result.side is HandSide.UNDETERMINED
    assert result.reasons == (reason,)


def test_a_mirrored_capture_is_handled_explicitly() -> None:
    palm = make_synthetic_palm(HandSide.RIGHT, mirrored=True)
    mirrored_ctx = CaptureContext(mirrored=True, palm_facing=True)
    # a detector that knows it sees a mirrored image names the hand correctly
    assert classify_side(palm.candidate(True), mirrored_ctx, True).side is HandSide.RIGHT
    # a detector that assumes an unmirrored image names the opposite hand; the mismatch is
    # corrected, not ignored, and the geometric check agrees with the corrected label
    assert classify_side(palm.candidate(False), mirrored_ctx, False).side is HandSide.RIGHT


def test_a_false_mirroring_declaration_cannot_be_detected_from_the_image() -> None:
    """A documented limitation: a mirrored right hand IS geometrically a left hand.

    The declaration must be truthful; a false one yields the opposite side and no 2D evidence
    can reveal it (see the module docstring of ``pandit_palm_vision.side``).
    """
    palm = make_synthetic_palm(HandSide.RIGHT, mirrored=True)
    lie = CaptureContext(mirrored=False, palm_facing=True)
    assert classify_side(palm.candidate(False), lie, False).side is HandSide.LEFT
    truth = CaptureContext(mirrored=True, palm_facing=True)
    assert classify_side(palm.candidate(False), truth, False).side is HandSide.RIGHT


def test_a_label_that_disagrees_with_the_geometry_is_undetermined(
    right_palm: SyntheticPalm,
) -> None:
    candidate: HandCandidate = right_palm.candidate(False)
    flipped = HandCandidate(candidate.landmarks, "Left", 9500, 9800)
    result = classify_side(flipped, FACING, False)
    assert result.side is HandSide.UNDETERMINED
    assert result.reasons == ("SIDE_LABEL_GEOMETRY_DISAGREE",)


def test_a_low_label_score_is_undetermined_only_when_a_minimum_is_configured(
    right_palm: SyntheticPalm,
) -> None:
    weak = right_palm.candidate(False, score_bp=4000)
    assert classify_side(weak, FACING, False).side is HandSide.RIGHT  # no threshold: not invented
    result = classify_side(weak, FACING, False, min_confidence_bp=6000)
    assert result.side is HandSide.UNDETERMINED and result.reasons == ("SIDE_CONFIDENCE_LOW",)


def test_collinear_landmarks_are_degenerate(right_palm: SyntheticPalm) -> None:
    candidate: HandCandidate = right_palm.candidate(False)
    pts = list(candidate.landmarks)
    pts[INDEX_MCP] = (0.5, 0.5)
    pts[PINKY_MCP] = (0.5, 0.4)
    pts[WRIST] = (0.5, 0.9)
    result = classify_side(HandCandidate(tuple(pts), "Right", 9000, 9000), FACING, False)
    assert result.side is HandSide.UNDETERMINED
    assert result.reasons == ("LANDMARK_GEOMETRY_DEGENERATE",)


def test_a_candidate_must_have_21_landmarks_and_integer_scores() -> None:
    with pytest.raises(ValueError):
        HandCandidate(((0.0, 0.0),) * 20, "Left", 9000, 9000)
    with pytest.raises(ValueError):
        HandCandidate(((0.0, 0.0),) * 21, "Left", 20000, 9000)


def test_best_candidate_and_no_hand(right_palm: SyntheticPalm) -> None:
    assert best_candidate(()) is None
    strong = right_palm.candidate(False, presence_bp=9900)
    weak = right_palm.candidate(False, presence_bp=6000)
    assert best_candidate((weak, strong)) is strong


def test_the_pipeline_covers_absent_multiple_and_undetermined_hands(
    right_palm: SyntheticPalm,
) -> None:
    palm = right_palm
    config = fixture_quality_config()
    none = PalmPipeline(StaticHandDetector(()), quality_config=config)
    absent = none.run(palm.image, FACING)
    assert absent.quality.outcome is QualityOutcome.REJECT and not absent.fact_set.facts

    candidate = palm.candidate(False)
    two = PalmPipeline(StaticHandDetector((candidate, candidate)), quality_config=config)
    several = two.run(palm.image, FACING)
    assert several.quality.outcome is QualityOutcome.RETRY and not several.fact_set.facts

    one = PalmPipeline(StaticHandDetector((candidate,)), quality_config=config)
    unknown = one.run(palm.image, CaptureContext(mirrored=None, palm_facing=True))
    side_fact = unknown.fact_set.facts_of_type(unknown.fact_set.facts[0].fact_type)
    assert unknown.side is not None and unknown.side.side is HandSide.UNDETERMINED
    reasons = {f.visibility.reason for f in side_fact if f.visibility.reason}
    assert "INPUT_MIRRORING_UNKNOWN" in reasons or "SIDE_UNDETERMINED" in reasons


def test_the_mapping_detector_returns_nothing_for_an_unknown_image(
    right_palm: SyntheticPalm,
) -> None:
    detector = MappingHandDetector({})
    assert detector.detect(right_palm.image).candidates == ()
