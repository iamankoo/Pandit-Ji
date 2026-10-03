"""The evaluation harness (Phase 13): run the pipeline over labelled samples and report metrics.

It **measures; it never decides.** The report records measured integers and ``None`` for undefined
metrics; the acceptance thresholds are ``CALIBRATION_REQUIRED`` and appear in the report as such.
Line precision and recall are reported as ``NOT_MEASURABLE_MODEL_UNAVAILABLE`` when no line
analyzer is active: a missing model is never reported as a score of zero.

A report built on synthetic samples carries ``data_class = SYNTHETIC_PLUMBING_ONLY``: it proves
the harness and the pipeline plumbing, and says nothing about accuracy on real hands.

Reports are canonical JSON with a SHA-256 ``report_hash`` over the content, so they are
versioned and reproducible: the same samples, pipeline and parameters give the same report.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np
from pandit_contracts.palm import (
    FactType,
    HandSide,
    LineAnalysisStatus,
    PalmFactSet,
    QualityOutcome,
)
from pandit_contracts.palm_canonical import BASIS_POINTS, PCF_SCALE, canonical_json, sha256_hex
from pydantic import BaseModel, ConfigDict

from pandit_palm_vision.evaluation.dataset import DatasetManifest, SampleRecord, validate_manifest
from pandit_palm_vision.evaluation.metrics import (
    Polyline,
    accuracy_bp,
    calibration_bins,
    confusion,
    iou_dice_bp,
    match_lines,
    mean_landmark_error_fixed,
    ratio_bp,
)
from pandit_palm_vision.image_input import CaptureContext, ImageInput
from pandit_palm_vision.pipeline import PalmPipeline, PipelineResult
from pandit_palm_vision.reproducibility import ToleranceRecord, compare_fact_sets, load_tolerances

HARNESS_VERSION = "1"
NOT_MEASURABLE = "NOT_MEASURABLE_MODEL_UNAVAILABLE"
_CANVAS = 600
_X_RANGE = (-1.5, 1.5)
_Y_RANGE = (-0.5, 1.5)


@dataclass(frozen=True)
class GroundTruth:
    hand_present: bool
    side: HandSide | None
    landmarks_pcf: tuple[tuple[float, float], ...] | None
    palm_polygon_pcf: tuple[tuple[float, float], ...] | None
    lines: tuple[tuple[tuple[float, float], ...], ...]
    usable: bool  # the annotators' IMAGE_ANALYSABLE verdict


@dataclass(frozen=True)
class EvalSample:
    record: SampleRecord
    image: ImageInput
    context: CaptureContext
    truth: GroundTruth


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    harness_version: str
    dataset_id: str
    dataset_version: str
    annotation_version: str
    manifest_hash: str
    data_class: str  # SYNTHETIC_PLUMBING_ONLY | GOVERNED_DATASET
    pipeline: dict[str, str]
    parameters: dict[str, int]
    sample_count: int
    metrics: dict[str, int | str | None]
    verdicts: dict[str, int]
    acceptance_thresholds: str  # always CALIBRATION_REQUIRED here
    report_hash: str

    def canonical(self) -> str:
        return canonical_json(self.model_dump(mode="json"))


def _raster(polygon_pcf: Sequence[tuple[float, float]]) -> np.ndarray:
    pts = np.asarray(polygon_pcf, dtype=np.float64)
    x = (pts[:, 0] - _X_RANGE[0]) / (_X_RANGE[1] - _X_RANGE[0]) * (_CANVAS - 1)
    y = (_Y_RANGE[1] - pts[:, 1]) / (_Y_RANGE[1] - _Y_RANGE[0]) * (_CANVAS - 1)
    canvas = np.zeros((_CANVAS, _CANVAS), dtype=np.uint8)
    cv2.fillPoly(canvas, [np.round(np.stack([x, y], axis=1)).astype(np.int32)], 1)
    return np.asarray(canvas > 0, dtype=bool)


def _fact_points(
    fact_set: PalmFactSet, fact_type: FactType, region: str
) -> list[tuple[float, float]]:
    for fact in fact_set.facts:
        if fact.fact_type is fact_type and fact.region_id == region and fact.geometry is not None:
            return [(x / PCF_SCALE, y / PCF_SCALE) for x, y in fact.geometry.coords_fixed]
    return []


def _tracks(fact_set: PalmFactSet) -> list[Polyline]:
    return [
        [(x / PCF_SCALE, y / PCF_SCALE) for x, y in f.geometry.coords_fixed]
        for f in fact_set.facts
        if f.fact_type is FactType.LINE_TRACK and f.geometry is not None
    ]


def _mean(values: list[int]) -> int | None:
    return round(sum(values) / len(values)) if values else None


def evaluate(
    pipeline: PalmPipeline,
    samples: Sequence[EvalSample],
    manifest: DatasetManifest,
    *,
    line_match_tolerance_fixed: int,
    tolerance: ToleranceRecord | None = None,
) -> EvaluationReport:
    """Run ``pipeline`` over ``samples`` and report what was measured.

    ``line_match_tolerance_fixed`` is an evaluation parameter (how close a predicted line must be
    to a true line to match), required explicitly: there is no default distance.
    """
    validate_manifest(manifest)
    tolerance = tolerance or load_tolerances()
    by_id = {r.image_id: r for r in manifest.records}
    for sample in samples:
        if sample.record != by_id.get(sample.record.image_id):
            raise ValueError(f"sample {sample.record.image_id} is not in the manifest")

    detected: list[bool] = []
    present: list[bool] = []
    outcomes: list[QualityOutcome] = []
    usable: list[bool] = []
    side_determined = 0
    side_correct = 0
    side_conf: list[int] = []
    side_ok: list[bool] = []
    landmark_errors: list[int] = []
    ious: list[int] = []
    dices: list[int] = []
    line_tp = line_fp = line_fn = 0
    line_status: LineAnalysisStatus = pipeline.line_analyzer.declared_status
    verdicts: Counter[str] = Counter()

    for sample in samples:
        result: PipelineResult = pipeline.run(sample.image, sample.context)
        again = pipeline.run(sample.image, sample.context)
        verdicts[compare_fact_sets(result.fact_set, again.fact_set, tolerance).verdict] += 1
        detected.append("NO_HAND_DETECTED" not in result.quality.reasons)
        present.append(sample.truth.hand_present)
        outcomes.append(result.quality.outcome)
        usable.append(sample.truth.usable)
        facts = result.fact_set
        if result.side is not None and sample.truth.side is not None:
            if result.side.side is not HandSide.UNDETERMINED:
                side_determined += 1
                is_ok = result.side.side is sample.truth.side
                side_correct += int(is_ok)
                side_conf.append(result.side.confidence_bp)
                side_ok.append(is_ok)
        landmarks = _fact_points(facts, FactType.LANDMARK_SET, "LANDMARKS.HAND_21")
        if landmarks and sample.truth.landmarks_pcf:
            err = mean_landmark_error_fixed(landmarks, sample.truth.landmarks_pcf)
            if err is not None:
                landmark_errors.append(err)
        region = _fact_points(facts, FactType.PALM_REGION, "PALM")
        if region and sample.truth.palm_polygon_pcf:
            iou, dice = iou_dice_bp(_raster(region), _raster(sample.truth.palm_polygon_pcf))
            if iou is not None and dice is not None:
                ious.append(iou)
                dices.append(dice)
        if result.quality.outcome is QualityOutcome.ACCEPT and result.line_status is not (
            LineAnalysisStatus.MODEL_UNAVAILABLE
        ):
            match = match_lines(_tracks(facts), sample.truth.lines, line_match_tolerance_fixed)
            line_tp += match.true_positives
            line_fp += match.false_positives
            line_fn += match.false_negatives

    hand = confusion(detected, present)
    gate = confusion([o is QualityOutcome.ACCEPT for o in outcomes], usable)
    n = len(samples)
    line_measurable = line_status is not LineAnalysisStatus.MODEL_UNAVAILABLE
    _, ece = calibration_bins(side_conf, side_ok)
    metrics: dict[str, int | str | None] = {
        "hand_detection_precision_bp": hand.precision_bp,
        "hand_detection_recall_bp": hand.recall_bp,
        "hand_detection_false_positive_rate_bp": hand.false_positive_rate_bp,
        "side_determined_rate_bp": ratio_bp(side_determined, n),
        "side_accuracy_among_determined_bp": accuracy_bp(side_correct, side_determined),
        "side_confidence_ece_bp": ece,
        "landmark_error_mean_fixed": _mean(landmark_errors),
        "palm_region_iou_mean_bp": _mean(ious),
        "palm_region_dice_mean_bp": _mean(dices),
        "line_precision_bp": ratio_bp(line_tp, line_tp + line_fp)
        if line_measurable
        else NOT_MEASURABLE,
        "line_recall_bp": ratio_bp(line_tp, line_tp + line_fn)
        if line_measurable
        else NOT_MEASURABLE,
        "quality_gate_accuracy_bp": gate.accuracy_bp,
        "quality_gate_false_accept_rate_bp": gate.false_positive_rate_bp,
        "accept_rate_bp": ratio_bp(sum(o is QualityOutcome.ACCEPT for o in outcomes), n),
        "retry_rate_bp": ratio_bp(sum(o is QualityOutcome.RETRY for o in outcomes), n),
        "reject_rate_bp": ratio_bp(sum(o is QualityOutcome.REJECT for o in outcomes), n),
        "reproducibility_identical_rate_bp": ratio_bp(verdicts["IDENTICAL"], n),
    }
    config = pipeline.quality_config
    pipeline_identity = {
        "quality_config_id": config.config_id,
        "quality_calibration_status": config.calibration_status.value,
        "line_analyzer_id": pipeline.line_analyzer.analyzer_id,
        "line_analysis_status": line_status.value,
        "tolerance_id": tolerance.tolerance_id,
        "tolerance_status": tolerance.status,
    }
    content = {
        "harness_version": HARNESS_VERSION,
        "dataset_id": manifest.dataset_id,
        "dataset_version": manifest.dataset_version,
        "annotation_version": manifest.annotation_version,
        "manifest_hash": manifest.manifest_hash,
        "data_class": "SYNTHETIC_PLUMBING_ONLY" if manifest.synthetic else "GOVERNED_DATASET",
        "pipeline": pipeline_identity,
        "parameters": {"line_match_tolerance_fixed": line_match_tolerance_fixed},
        "sample_count": n,
        "metrics": metrics,
        "verdicts": dict(sorted(verdicts.items())),
        "acceptance_thresholds": "CALIBRATION_REQUIRED",
    }
    return EvaluationReport(**content, report_hash=sha256_hex(content))  # type: ignore[arg-type]


__all__ = ["BASIS_POINTS", "EvalSample", "EvaluationReport", "GroundTruth", "evaluate"]
