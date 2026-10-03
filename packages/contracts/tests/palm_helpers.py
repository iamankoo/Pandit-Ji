"""Builders for palm contract tests (synthetic values only; no image, no user data)."""

from __future__ import annotations

from typing import Any

from pandit_contracts.palm import (
    CalibrationStatus,
    ConfidenceScore,
    Derivation,
    FactClass,
    FactType,
    FactValue,
    Geometry,
    HandSide,
    ImageRef,
    LineAnalysisStatus,
    PalmFact,
    PalmFactSet,
    Provenance,
    QualityCheckResult,
    QualityCheckStatus,
    QualityOutcome,
    QualityResult,
    RuntimeIdentity,
    Visibility,
    VisibilityState,
    build_palm_fact,
    build_palm_fact_set,
    make_analysis_id,
)

IMAGE = ImageRef(image_id="IMG-SYNTH-0001", content_sha256="a" * 64)


def make_provenance(**overrides: Any) -> Provenance:
    fields: dict[str, Any] = {
        "pipeline_version": "0.1.0",
        "preprocessing_id": "PRE-TEST",
        "preprocessing_version": "1",
        "parameters_sha256": "b" * 64,
        "normalized_input_sha256": "c" * 64,
        "quality_config_id": "QC-TEST",
        "quality_config_version": "1",
        "quality_calibration_status": CalibrationStatus.FIXTURE_ONLY,
        "inference_config_sha256": "d" * 64,
        "line_analysis_status": LineAnalysisStatus.MODEL_UNAVAILABLE,
        "models": (),
        "runtime": RuntimeIdentity(python="3.12.0", packages=(("numpy", "2.0.0"),)),
    }
    fields.update(overrides)
    return Provenance(**fields)


def make_quality(outcome: QualityOutcome = QualityOutcome.ACCEPT) -> QualityResult:
    return QualityResult(
        outcome=outcome,
        checks=(QualityCheckResult(check="blur", status=QualityCheckStatus.PASS, metric_fixed=5),),
        config_id="QC-TEST",
        config_version="1",
        calibration_status=CalibrationStatus.FIXTURE_ONLY,
    )


def make_fact(
    analysis_id: str,
    provenance: Provenance,
    quality: QualityResult,
    **overrides: Any,
) -> PalmFact:
    fields: dict[str, Any] = {
        "analysis_id": analysis_id,
        "fact_class": FactClass.OBSERVED,
        "fact_type": FactType.HAND_SIDE,
        "hand_side": HandSide.RIGHT,
        "value": FactValue(kind="ENUM", v="RIGHT"),
        "confidence": ConfidenceScore(score_bp=9000),
        "visibility": Visibility(state=VisibilityState.CLEAR),
        "quality_ref": quality.quality_ref,
        "provenance": provenance.provenance_id,
        "image_ref": IMAGE,
    }
    fields.update(overrides)
    return build_palm_fact(**fields)


def make_set() -> tuple[PalmFactSet, Provenance, QualityResult]:
    prov = make_provenance()
    quality = make_quality()
    analysis_id = make_analysis_id(IMAGE, prov)
    side = make_fact(analysis_id, prov, quality)
    track = make_fact(
        analysis_id,
        prov,
        quality,
        fact_type=FactType.LINE_TRACK,
        value=FactValue(),
        geometry=Geometry(kind="POLYLINE", coords_fixed=((0, 0), (1000, 2000), (2500, 4000))),
    )
    length = make_fact(
        analysis_id,
        prov,
        quality,
        fact_class=FactClass.DERIVED,
        fact_type=FactType.LINE_ATTRIBUTE,
        value=FactValue(kind="RATIO_FIXED", v=4720, unit="PALM_UNIT_E-4"),
        derived_from=(track.fact_id,),
        derivation=Derivation(method_id="POLYLINE_LENGTH", method_version="1"),
    )
    fact_set = build_palm_fact_set(
        analysis_id=analysis_id,
        image_ref=IMAGE,
        quality_result=quality,
        facts=[length, track, side],
        provenance_blocks=[prov],
    )
    return fact_set, prov, quality
