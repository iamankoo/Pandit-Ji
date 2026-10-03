from __future__ import annotations

import json
import sys
import types
from typing import Any

import numpy as np
import pytest
from pandit_contracts.palm import FactType, LineAnalysisStatus, VisibilityState
from pandit_contracts.palm_canonical import canonical_json

from pandit_palm_vision.artifacts import REQUIRED_PREPROCESSING, ArtifactPolicyError, ModelArtifact
from pandit_palm_vision.frame import build_frame
from pandit_palm_vision.lines import (
    ArtifactBackedLineAnalyzer,
    BaselineRidgeLineAnalyzer,
    BaselineRidgeParams,
    FixtureLineAnalyzer,
    LineTrackResult,
    ModelUnavailableLineAnalyzer,
    polyline_intersection,
    polyline_length,
)
from pandit_palm_vision.synthetic import SyntheticPalm
from tests.helpers import PALM_FACING, pipeline_for


def _frame(palm: SyntheticPalm) -> Any:
    return build_frame(palm.candidate(False), palm.side, 480, 640, palm.mirrored)


def test_without_a_model_the_status_is_explicit_and_no_line_is_produced(
    right_palm: SyntheticPalm,
) -> None:
    analyzer = ModelUnavailableLineAnalyzer()
    result = analyzer.analyze(right_palm.image, _frame(right_palm), right_palm.candidate(False))
    assert result.status is LineAnalysisStatus.MODEL_UNAVAILABLE
    assert result.tracks == () and result.reasons == ("PALM_LINE_MODEL_UNAVAILABLE",)


def test_the_production_default_yields_not_evaluable_line_facts(right_palm: SyntheticPalm) -> None:
    outcome = pipeline_for(right_palm).run(right_palm.image, PALM_FACING)
    tracks = outcome.fact_set.facts_of_type(FactType.LINE_TRACK)
    assert len(tracks) == 1
    assert tracks[0].visibility.state is VisibilityState.NOT_EVALUABLE
    assert tracks[0].visibility.reason == "PALM_LINE_MODEL_UNAVAILABLE"
    assert outcome.line_status is LineAnalysisStatus.MODEL_UNAVAILABLE
    provenance = outcome.fact_set.provenance_blocks[0]
    assert provenance.line_analysis_status is LineAnalysisStatus.MODEL_UNAVAILABLE


def test_the_baseline_is_experimental_and_returns_nothing_until_a_threshold_is_calibrated(
    right_palm: SyntheticPalm,
) -> None:
    result = BaselineRidgeLineAnalyzer().analyze(
        right_palm.image, _frame(right_palm), right_palm.candidate(False)
    )
    assert result.status is LineAnalysisStatus.BASELINE_EXPERIMENTAL
    assert result.tracks == ()
    assert result.reasons == ("RIDGE_THRESHOLD_CALIBRATION_REQUIRED",)


def test_the_baseline_with_an_explicit_experimental_threshold_finds_candidate_tracks(
    right_palm: SyntheticPalm,
) -> None:
    analyzer = BaselineRidgeLineAnalyzer(BaselineRidgeParams(ridge_threshold_x100=300))
    result = analyzer.analyze(right_palm.image, _frame(right_palm), right_palm.candidate(False))
    assert result.status is LineAnalysisStatus.BASELINE_EXPERIMENTAL
    assert "BASELINE_NOT_VALIDATED" in result.reasons
    assert result.tracks, "the synthetic image has drawn lines the ridge filter should respond to"
    for track in result.tracks:
        assert 0 <= track.score_bp <= 10_000 and len(track.points_pcf) >= 2
    # deterministic
    again = analyzer.analyze(right_palm.image, _frame(right_palm), right_palm.candidate(False))
    assert again == result


def test_baseline_tracks_are_unlabelled_and_roles_stay_not_evaluable(
    right_palm: SyntheticPalm,
) -> None:
    analyzer = BaselineRidgeLineAnalyzer(BaselineRidgeParams(ridge_threshold_x100=300))
    outcome = pipeline_for(right_palm, line_analyzer=analyzer).run(right_palm.image, PALM_FACING)
    roles = outcome.fact_set.facts_of_type(FactType.LINE_ROLE_CANDIDATE)
    assert len(roles) == 6
    assert all(f.visibility.state is VisibilityState.NOT_EVALUABLE for f in roles)
    reasons = {f.region_id: f.visibility.reason for f in roles}
    assert reasons["ROLE.MERCURY_LINE_VARIANT"] == "SOURCE_CONFLICT_MERCURY_LINE_DEFINITION"
    assert reasons["ROLE.LIFE"] == "ROLE_ASSIGNMENT_UNVALIDATED"
    assert all(f.labelling is None for f in outcome.fact_set.facts)  # no palmistry name assigned
    assert outcome.fact_set.provenance_blocks[0].line_analysis_status is (
        LineAnalysisStatus.BASELINE_EXPERIMENTAL
    )


def test_fixture_tracks_become_observed_tracks_and_derived_attributes(
    right_palm: SyntheticPalm,
) -> None:
    analyzer = FixtureLineAnalyzer(right_palm.lines)
    outcome = pipeline_for(right_palm, line_analyzer=analyzer).run(right_palm.image, PALM_FACING)
    facts = outcome.fact_set
    tracks = facts.facts_of_type(FactType.LINE_TRACK)
    assert len(tracks) == len(right_palm.lines)
    assert facts.provenance_blocks[0].line_analysis_status is LineAnalysisStatus.FIXTURE_SYNTHETIC
    lengths = facts.facts_of_type(FactType.LINE_ATTRIBUTE)
    assert len(lengths) == len(tracks)
    for fact in lengths:
        assert fact.value.kind == "RATIO_FIXED" and isinstance(fact.value.v, int)
        assert fact.derived_from and fact.derivation is not None
    floats: list[str] = []
    json.loads(
        canonical_json(facts.model_dump(mode="json")),
        parse_float=lambda text: floats.append(text) or 0.0,
    )
    assert floats == []


def _artifact(**overrides: Any) -> ModelArtifact:
    fields: dict[str, Any] = {
        "artifact_id": "LINE_MODEL_FIXTURE",
        "version": "1",
        "role": "palm_line_segmentation",
        "sha256": "a" * 64,
        "source": "unit test fixture (not a model)",
        "licence_id": "FIXTURE",
        "licence_verified": True,
        "provenance_note": "fixture",
        "preprocessing_compat": (REQUIRED_PREPROCESSING,),
        "runtime_compat": ("python>=3.10",),
    }
    fields.update(overrides)
    return ModelArtifact(**fields)


class _FakeBackend:
    def predict(self, roi_gray: np.ndarray) -> list[tuple[list[tuple[float, float]], float]]:
        return [([(40.0, 200.0), (120.0, 140.0), (200.0, 120.0)], 0.8), ([(1.0, 1.0)], 0.9)]


def test_an_unusable_artifact_cannot_back_the_analyzer() -> None:
    with pytest.raises(ArtifactPolicyError):
        ArtifactBackedLineAnalyzer(_artifact(licence_verified=False), _FakeBackend())


def test_an_unvalidated_model_is_reported_as_such(right_palm: SyntheticPalm) -> None:
    analyzer = ArtifactBackedLineAnalyzer(_artifact(), _FakeBackend())
    result = analyzer.analyze(right_palm.image, _frame(right_palm), right_palm.candidate(False))
    assert result.status is LineAnalysisStatus.MODEL_UNVALIDATED
    assert result.reasons == ("MODEL_VALIDATION_REPORT_MISSING",)
    assert len(result.tracks) == 1  # the one-point polyline is dropped, never invented into a track
    assert result.models[0].artifact_id == "LINE_MODEL_FIXTURE"


def test_only_a_validated_model_reports_trained_model(right_palm: SyntheticPalm) -> None:
    analyzer = ArtifactBackedLineAnalyzer(
        _artifact(validation_report_sha256="b" * 64), _FakeBackend()
    )
    assert analyzer.declared_status is LineAnalysisStatus.TRAINED_MODEL
    result = analyzer.analyze(right_palm.image, _frame(right_palm), right_palm.candidate(False))
    assert result.status is LineAnalysisStatus.TRAINED_MODEL and result.reasons == ()
    outcome = pipeline_for(right_palm, line_analyzer=analyzer).run(right_palm.image, PALM_FACING)
    provenance = outcome.fact_set.provenance_blocks[0]
    assert provenance.models[0].artifact_id == "LINE_MODEL_FIXTURE"
    assert provenance.line_analysis_status is LineAnalysisStatus.TRAINED_MODEL


def test_polyline_geometry_helpers() -> None:
    assert polyline_length([(0.0, 0.0), (3.0, 4.0)]) == pytest.approx(5.0)
    crossing = polyline_intersection([(0.0, 0.0), (2.0, 2.0)], [(0.0, 2.0), (2.0, 0.0)])
    assert crossing == pytest.approx((1.0, 1.0))
    assert polyline_intersection([(0.0, 0.0), (1.0, 0.0)], [(0.0, 1.0), (1.0, 1.0)]) is None
    with pytest.raises(ValueError):
        LineTrackResult(points_pcf=((0.0, 0.0),), score_bp=1)


def test_crossing_tracks_produce_derived_intersection_facts(right_palm: SyntheticPalm) -> None:
    crossing = (
        LineTrackResult(((-0.3, 0.2), (0.3, 0.6)), 9000),
        LineTrackResult(((-0.3, 0.6), (0.3, 0.2)), 8000),
    )
    outcome = pipeline_for(right_palm, line_analyzer=FixtureLineAnalyzer(crossing)).run(
        right_palm.image, PALM_FACING
    )
    points = outcome.fact_set.facts_of_type(FactType.LINE_INTERSECTION)
    assert len(points) == 1 and len(points[0].derived_from) == 2


def test_the_optional_mediapipe_package_is_not_needed_to_import_the_service() -> None:
    assert "mediapipe" not in sys.modules or isinstance(sys.modules["mediapipe"], types.ModuleType)
