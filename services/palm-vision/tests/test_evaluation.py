from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from pandit_palm_vision.evaluation.dataset import (
    DatasetManifest,
    ManifestError,
    SampleRecord,
    contributors_missing_a_hand,
    coverage_report,
    validate_manifest,
)
from pandit_palm_vision.evaluation.harness import NOT_MEASURABLE, evaluate
from pandit_palm_vision.evaluation.metrics import (
    Confusion,
    calibration_bins,
    confusion,
    iou_dice_bp,
    match_lines,
    mean_landmark_error_fixed,
    polyline_distance,
    ratio_bp,
)
from pandit_palm_vision.evaluation.synthetic_set import synthetic_eval_set
from pandit_palm_vision.lines import (
    FixtureLineAnalyzer,
    LineTrackResult,
    ModelUnavailableLineAnalyzer,
)
from pandit_palm_vision.pipeline import PalmPipeline
from pandit_palm_vision.quality import DEFAULT_QUALITY_CONFIG, fixture_quality_config
from pandit_palm_vision.synthetic import make_synthetic_palm


# ---- metrics ---------------------------------------------------------------------------------
def test_ratios_are_integer_basis_points_and_undefined_is_none() -> None:
    assert ratio_bp(1, 4) == 2500 and ratio_bp(0, 5) == 0
    assert ratio_bp(1, 0) is None


def test_confusion_metrics() -> None:
    c = confusion([True, True, False, False, True], [True, False, False, True, True])
    assert c == Confusion(tp=2, fp=1, fn=1, tn=1)
    assert c.precision_bp == 6667 and c.recall_bp == 6667
    assert c.false_positive_rate_bp == 5000 and c.accuracy_bp == 6000
    assert confusion([], []).precision_bp is None
    with pytest.raises(ValueError):
        confusion([True], [])


def test_iou_and_dice() -> None:
    a = np.zeros((10, 10), dtype=bool)
    b = np.zeros((10, 10), dtype=bool)
    a[:5, :5] = True
    b[:5, :5] = True
    assert iou_dice_bp(a, b) == (10_000, 10_000)
    b[:] = False
    b[:5, 5:] = True
    assert iou_dice_bp(a, b) == (0, 0)
    assert iou_dice_bp(np.zeros((3, 3), dtype=bool), np.zeros((3, 3), dtype=bool)) == (None, None)


def test_landmark_error_is_in_fixed_point_palm_units() -> None:
    assert mean_landmark_error_fixed([(0.0, 0.0), (1.0, 0.0)], [(0.0, 0.3), (1.0, 0.1)]) == 2000
    assert mean_landmark_error_fixed([], []) is None


def test_line_matching_needs_an_explicit_tolerance() -> None:
    truth = [[(0.0, 0.0), (1.0, 0.0)], [(0.0, 1.0), (1.0, 1.0)]]
    close = [[(0.0, 0.01), (1.0, 0.01)], [(0.0, 3.0), (1.0, 3.0)]]
    match = match_lines(close, truth, tolerance_fixed=500)
    assert (match.true_positives, match.false_positives, match.false_negatives) == (1, 1, 1)
    assert match.precision_bp == 5000 and match.recall_bp == 5000
    assert polyline_distance(truth[0], truth[0]) == pytest.approx(0.0)


def test_calibration_bins_are_descriptive() -> None:
    bins, ece = calibration_bins([9000, 9000, 1000, 1000], [True, True, False, False])
    assert sum(b.count for b in bins) == 4
    assert ece is not None and ece <= 1000
    assert calibration_bins([], [])[1] is None


# ---- dataset governance ----------------------------------------------------------------------
def _record(**overrides: Any) -> SampleRecord:
    fields: dict[str, Any] = {
        "image_id": "I1",
        "content_sha256": "a" * 64,
        "contributor_id": "C1",
        "split": "train",
        "hand_side": "LEFT",
        "device_id": "D1",
        "lighting": "indoor",
        "background": "plain",
        "resolution": "medium",
        "orientation": "upright",
        "occlusion": "none",
        "consent_record_id": "CONSENT-1",
        "adult_attested": True,
    }
    fields.update(overrides)
    return SampleRecord(**fields)


def _manifest(records: tuple[SampleRecord, ...], **overrides: Any) -> DatasetManifest:
    fields: dict[str, Any] = {
        "dataset_id": "D",
        "dataset_version": "1",
        "annotation_version": "1",
        "guideline_version": "1",
        "label_vocabulary": ("HAND_SIDE", "LINE_TRACK_POLYLINE"),
        "synthetic": False,
        "records": records,
    }
    fields.update(overrides)
    return DatasetManifest(**fields)


def test_a_valid_manifest_passes_and_has_a_stable_hash() -> None:
    m = _manifest((_record(), _record(image_id="I2", content_sha256="b" * 64, hand_side="RIGHT")))
    validate_manifest(m)
    assert m.manifest_hash == _manifest(m.records).manifest_hash
    assert contributors_missing_a_hand(m) == ()


def test_no_silent_user_images_and_no_minors() -> None:
    with pytest.raises(ValueError, match="consent"):
        _record(consent_record_id=None)
    with pytest.raises(ValueError, match="adult"):
        _record(adult_attested=False)


def test_contributors_never_span_splits() -> None:
    m = _manifest((_record(), _record(image_id="I2", content_sha256="b" * 64, split="test")))
    with pytest.raises(ManifestError, match="contributor C1"):
        validate_manifest(m)


def test_the_same_image_never_leaks_across_splits() -> None:
    m = _manifest(
        (_record(), _record(image_id="I2", contributor_id="C2", split="test")),
    )
    with pytest.raises(ManifestError, match="leaks across splits"):
        validate_manifest(m)


def test_no_skin_tone_or_other_demographic_label_can_be_added() -> None:
    with pytest.raises(ValueError):
        SampleRecord(**{**_record().model_dump(), "skin_tone": "x"})
    with pytest.raises(ValueError):
        DatasetManifest(**{**_manifest((_record(),)).model_dump(), "demographics": {}})


@pytest.mark.parametrize(
    "label", ["DISEASE_RISK", "CRIMINAL_TENDENCY", "FERTILITY_SCORE", "MORAL_CHARACTER", "LIFESPAN"]
)
def test_prohibited_interpretation_categories_are_never_labels(label: str) -> None:
    m = _manifest((_record(),), label_vocabulary=("HAND_SIDE", label))
    with pytest.raises(ManifestError, match="prohibited"):
        validate_manifest(m)


def test_only_known_annotation_labels_are_allowed() -> None:
    with pytest.raises(ManifestError, match="not an allowed"):
        validate_manifest(_manifest((_record(),), label_vocabulary=("MYSTERY",)))


def test_coverage_is_reported_including_empty_strata_and_sets_no_target() -> None:
    report = coverage_report(
        _manifest((_record(), _record(image_id="I2", content_sha256="b" * 64)))
    )
    assert report["split"] == {"test": 0, "train": 2, "validation": 0}
    assert report["lighting"]["low"] == 0 and report["lighting"]["indoor"] == 2
    assert report["hand_side"] == {"LEFT": 2, "RIGHT": 0}
    assert contributors_missing_a_hand(_manifest((_record(),))) == ("C1",)


# ---- harness ---------------------------------------------------------------------------------
def test_the_harness_reports_measurements_never_thresholds() -> None:
    manifest, samples, detector = synthetic_eval_set()
    pipeline = PalmPipeline(detector, quality_config=fixture_quality_config())
    report = evaluate(pipeline, samples, manifest, line_match_tolerance_fixed=500)
    assert report.data_class == "SYNTHETIC_PLUMBING_ONLY"
    assert report.acceptance_thresholds == "CALIBRATION_REQUIRED"
    assert report.pipeline["tolerance_status"] == "CALIBRATION_REQUIRED"
    assert report.sample_count == len(samples) == 8
    m = report.metrics
    assert m["hand_detection_precision_bp"] == 10_000 and m["hand_detection_recall_bp"] == 10_000
    assert (
        m["side_accuracy_among_determined_bp"] == 10_000 and m["side_determined_rate_bp"] == 10_000
    )
    assert m["quality_gate_accuracy_bp"] == 10_000
    assert m["landmark_error_mean_fixed"] == 0 and m["palm_region_iou_mean_bp"] == 10_000
    assert all(not isinstance(v, float) for v in m.values())


def test_without_a_line_model_line_metrics_are_not_measurable_not_zero() -> None:
    manifest, samples, detector = synthetic_eval_set()
    pipeline = PalmPipeline(detector, ModelUnavailableLineAnalyzer(), fixture_quality_config())
    metrics = evaluate(pipeline, samples, manifest, line_match_tolerance_fixed=500).metrics
    assert metrics["line_precision_bp"] == NOT_MEASURABLE
    assert metrics["line_recall_bp"] == NOT_MEASURABLE


def test_a_fixture_line_analyzer_is_measured_against_the_truth() -> None:
    manifest, samples, detector = synthetic_eval_set()
    truth_tracks = [
        LineTrackResult(points_pcf=line, score_bp=9000) for line in samples[0].truth.lines
    ]
    pipeline = PalmPipeline(detector, FixtureLineAnalyzer(truth_tracks), fixture_quality_config())
    metrics = evaluate(pipeline, samples, manifest, line_match_tolerance_fixed=500).metrics
    assert metrics["line_precision_bp"] == 10_000 and metrics["line_recall_bp"] == 10_000


def test_the_report_is_reproducible_and_hashed() -> None:
    manifest, samples, detector = synthetic_eval_set()
    pipeline = PalmPipeline(detector, quality_config=fixture_quality_config())
    one = evaluate(pipeline, samples, manifest, line_match_tolerance_fixed=500)
    two = evaluate(pipeline, samples, manifest, line_match_tolerance_fixed=500)
    assert one.report_hash == two.report_hash and one.canonical() == two.canonical()
    other = evaluate(pipeline, samples, manifest, line_match_tolerance_fixed=900)
    assert other.report_hash != one.report_hash


def test_the_default_quality_config_shows_up_as_rejection_not_a_fake_score() -> None:
    manifest, samples, detector = synthetic_eval_set()
    pipeline = PalmPipeline(detector, quality_config=DEFAULT_QUALITY_CONFIG)
    metrics = evaluate(pipeline, samples, manifest, line_match_tolerance_fixed=500).metrics
    assert metrics["accept_rate_bp"] == 0 and metrics["retry_rate_bp"] == 10_000
    assert metrics["quality_gate_accuracy_bp"] == 0
    assert metrics["side_determined_rate_bp"] == 0


def test_the_synthetic_set_is_governed_like_a_real_one() -> None:
    manifest, samples, _ = synthetic_eval_set(contributors=6)
    validate_manifest(manifest)
    assert contributors_missing_a_hand(manifest) == ()
    assert {r.split for r in manifest.records} == {"train", "validation", "test"}
    assert all(r.synthetic for r in manifest.records)
    assert len(samples) == 12


def test_a_sample_outside_the_manifest_is_refused() -> None:
    manifest, samples, detector = synthetic_eval_set()
    stranger = make_synthetic_palm(seed=77, image_id="NOT-IN-MANIFEST")
    bad = type(samples[0])(
        samples[0].record.model_copy(update={"image_id": stranger.image.image_id}),
        stranger.image,
        samples[0].context,
        samples[0].truth,
    )
    with pytest.raises(ValueError, match="not in the manifest"):
        evaluate(
            PalmPipeline(detector, quality_config=fixture_quality_config()),
            [bad],
            manifest,
            line_match_tolerance_fixed=500,
        )
