from __future__ import annotations

import cv2
from pandit_contracts.palm import (
    FactClass,
    FactType,
    HandSide,
    QualityOutcome,
    VisibilityState,
    build_palm_evidence_bundle,
)
from pandit_contracts.palm_canonical import canonical_json

from pandit_palm_vision.hand import StaticHandDetector
from pandit_palm_vision.image_input import CaptureContext
from pandit_palm_vision.pipeline import PalmPipeline
from pandit_palm_vision.quality import DEFAULT_QUALITY_CONFIG
from pandit_palm_vision.synthetic import SyntheticPalm, make_synthetic_palm
from tests.helpers import PALM_FACING, pipeline_for


def test_a_clean_hand_produces_observed_and_derived_facts_only(right_palm: SyntheticPalm) -> None:
    outcome = pipeline_for(right_palm).run(right_palm.image, PALM_FACING)
    assert outcome.quality.outcome is QualityOutcome.ACCEPT
    facts = outcome.fact_set.facts
    assert {f.fact_class for f in facts} <= {FactClass.OBSERVED, FactClass.DERIVED}
    kinds = {f.fact_type for f in facts}
    assert {
        FactType.HAND_SIDE,
        FactType.LANDMARK_SET,
        FactType.PALM_REGION,
        FactType.MOUNT_REGION,
        FactType.LINE_ROLE_CANDIDATE,
        FactType.REGION_GEOMETRY,
    } <= kinds
    side = outcome.fact_set.facts_of_type(FactType.HAND_SIDE)[0]
    assert side.hand_side is HandSide.RIGHT and side.visibility.state is VisibilityState.CLEAR
    assert all(f.labelling is None for f in facts)  # the vision pipeline names no palmistry line


def test_every_fact_answers_what_image_pipeline_and_models_produced_it(
    right_palm: SyntheticPalm,
) -> None:
    outcome = pipeline_for(right_palm).run(right_palm.image, PALM_FACING)
    fact_set = outcome.fact_set
    prov = fact_set.provenance_blocks[0]
    assert fact_set.image_ref == right_palm.image.ref
    assert prov.normalized_input_sha256 == right_palm.image.normalized_input_sha256
    assert prov.pipeline_version and prov.preprocessing_id and prov.runtime.python
    assert prov.quality_config_id == fact_set.quality_result.config_id
    assert dict(prov.runtime.packages).get("numpy")
    for fact in fact_set.facts:
        assert fact.image_ref == right_palm.image.ref
        assert fact.provenance == prov.provenance_id
        assert fact.quality_ref == fact_set.quality_result.quality_ref
        assert fact.analysis_id == fact_set.analysis_id
        for parent in fact.derived_from:
            fact_set.fact(parent)  # the derivation chain resolves


def test_the_same_input_gives_the_same_facts_every_time(right_palm: SyntheticPalm) -> None:
    pipeline = pipeline_for(right_palm)
    one = pipeline.run(right_palm.image, PALM_FACING).fact_set
    two = pipeline.run(right_palm.image, PALM_FACING).fact_set
    assert one.fact_set_hash == two.fact_set_hash
    assert canonical_json(one.model_dump(mode="json")) == canonical_json(
        two.model_dump(mode="json")
    )


def test_a_different_image_gives_different_facts(right_palm: SyntheticPalm) -> None:
    other = make_synthetic_palm(HandSide.RIGHT, seed=11, rotation_deg=8.0)
    one = pipeline_for(right_palm).run(right_palm.image, PALM_FACING).fact_set
    two = pipeline_for(other).run(other.image, PALM_FACING).fact_set
    assert one.fact_set_hash != two.fact_set_hash and one.analysis_id != two.analysis_id


def test_a_failed_quality_gate_stops_the_pipeline_before_any_analysis() -> None:
    palm = make_synthetic_palm(HandSide.RIGHT, blur_sigma=6.0)
    outcome = pipeline_for(palm).run(palm.image, PALM_FACING)
    assert outcome.quality.outcome is QualityOutcome.RETRY
    assert outcome.fact_set.facts == ()  # no palm fact is fabricated for a bad image
    assert outcome.fact_set.quality_result.reasons  # the reasons are the evidence


def test_the_default_quality_config_never_lets_an_image_through(right_palm: SyntheticPalm) -> None:
    detector = StaticHandDetector((right_palm.candidate(False),), False)
    outcome = PalmPipeline(detector, quality_config=DEFAULT_QUALITY_CONFIG).run(
        right_palm.image, PALM_FACING
    )
    assert outcome.quality.outcome is QualityOutcome.RETRY
    assert outcome.fact_set.facts == ()


def test_an_undetermined_side_makes_dependent_facts_not_evaluable(
    right_palm: SyntheticPalm,
) -> None:
    outcome = pipeline_for(right_palm).run(
        right_palm.image, CaptureContext(mirrored=None, palm_facing=True)
    )
    facts = outcome.fact_set.facts
    assert outcome.side is not None and outcome.side.side is HandSide.UNDETERMINED
    by_type = {f.fact_type: f for f in facts}
    assert by_type[FactType.HAND_SIDE].visibility.reason == "INPUT_MIRRORING_UNKNOWN"
    for kind in (FactType.LANDMARK_SET, FactType.PALM_REGION):
        assert by_type[kind].visibility.state is VisibilityState.NOT_EVALUABLE
        assert by_type[kind].visibility.reason == "SIDE_UNDETERMINED"
        assert by_type[kind].geometry is None  # no coordinates are guessed
    assert FactType.LINE_TRACK not in by_type  # no line analysis without a determined side


def test_left_and_right_hands_agree_in_the_canonical_frame(
    right_palm: SyntheticPalm, left_palm: SyntheticPalm
) -> None:
    def landmarks(palm: SyntheticPalm) -> tuple[tuple[int, int], ...]:
        fact = (
            pipeline_for(palm)
            .run(palm.image, PALM_FACING)
            .fact_set.facts_of_type(FactType.LANDMARK_SET)[0]
        )
        assert fact.geometry is not None
        return fact.geometry.coords_fixed

    right, left = landmarks(right_palm), landmarks(left_palm)
    assert (
        max(abs(a - b) for p, q in zip(right, left, strict=True) for a, b in zip(p, q, strict=True))
        <= 1
    )


def test_the_mirroring_is_recorded_on_the_geometry_facts() -> None:
    left = make_synthetic_palm(HandSide.LEFT)
    fact = (
        pipeline_for(left)
        .run(left.image, PALM_FACING)
        .fact_set.facts_of_type(FactType.PALM_REGION)[0]
    )
    assert fact.value.v == "MIRRORED_FOR_CANONICAL"
    right = make_synthetic_palm(HandSide.RIGHT)
    fact = (
        pipeline_for(right)
        .run(right.image, PALM_FACING)
        .fact_set.facts_of_type(FactType.PALM_REGION)[0]
    )
    assert fact.value.v == "NOT_MIRRORED"


def test_mount_regions_are_positions_only_and_mars_moon_are_not_evaluable(
    right_palm: SyntheticPalm,
) -> None:
    facts = (
        pipeline_for(right_palm)
        .run(right_palm.image, PALM_FACING)
        .fact_set.facts_of_type(FactType.MOUNT_REGION)
    )
    by_region = {f.region_id: f for f in facts}
    for name in (
        "MOUNT.JUPITER",
        "MOUNT.SATURN",
        "MOUNT.APOLLO_SUN",
        "MOUNT.MERCURY",
        "MOUNT.VENUS",
    ):
        assert by_region[name].value.v == "PROJECT_DERIVED_POSITION_ONLY"
        assert by_region[name].geometry is not None
    assert by_region["MOUNT.MARS"].visibility.reason == "SOURCE_CONFLICT_MARS_REGION"
    assert by_region["MOUNT.MOON"].visibility.state is VisibilityState.NOT_EVALUABLE
    # no mount "development" (a volume property) is ever inferred from one image
    assert not any("DEVELOP" in str(f.value.v) for f in facts)


def test_triangle_and_quadrangle_wait_for_validated_lines(right_palm: SyntheticPalm) -> None:
    regions = (
        pipeline_for(right_palm)
        .run(right_palm.image, PALM_FACING)
        .fact_set.facts_of_type(FactType.REGION_GEOMETRY)
    )
    assert {f.region_id for f in regions} == {"REGION.TRIANGLE", "REGION.QUADRANGLE"}
    assert all(f.visibility.state is VisibilityState.NOT_EVALUABLE for f in regions)


def test_the_canonical_facts_hold_no_floats_and_no_pixels(right_palm: SyntheticPalm) -> None:
    fact_set = pipeline_for(right_palm).run(right_palm.image, PALM_FACING).fact_set
    text = canonical_json(fact_set.model_dump(mode="json"))  # raises on any float
    assert right_palm.image.content_sha256 in text
    assert len(text) < 200_000  # an image would be megabytes
    pixels = right_palm.image.pixels.tobytes()[:64]
    assert pixels.hex() not in text


def test_the_pipeline_runs_from_encoded_bytes(right_palm: SyntheticPalm) -> None:
    ok, encoded = cv2.imencode(".png", right_palm.image.pixels)
    assert ok
    outcome = pipeline_for(right_palm).run_bytes(
        bytes(encoded.tobytes()), right_palm.image.image_id, PALM_FACING
    )
    assert outcome.quality.outcome is QualityOutcome.ACCEPT
    assert (
        outcome.fact_set.image_ref.content_sha256 != right_palm.image.content_sha256
    )  # file bytes vs buffer


def test_the_whole_flow_ends_in_an_evidence_bundle_that_is_not_production_ready(
    right_palm: SyntheticPalm,
) -> None:
    fact_set = pipeline_for(right_palm).run(right_palm.image, PALM_FACING).fact_set
    bundle = build_palm_evidence_bundle(
        fact_set=fact_set, rule_evaluations=[], knowledge_version="KV-NONE"
    )
    assert bundle.production_ready is False
    assert "LINE_ANALYSIS_MODEL_UNAVAILABLE" in bundle.readiness_blockers
    assert "QUALITY_THRESHOLDS_FIXTURE_ONLY" in bundle.readiness_blockers
    assert bundle.hand_fact_ids and bundle.landmark_fact_ids and bundle.region_fact_ids
