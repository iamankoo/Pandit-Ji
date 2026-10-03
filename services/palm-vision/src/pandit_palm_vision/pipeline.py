"""The palm pipeline: image to structured palm facts (Phase 13).

IMAGE -> QUALITY -> HAND -> SIDE -> REGION -> LANDMARKS -> LINE/FEATURE ANALYSIS -> FACTS

Facts flow one direction. The pipeline produces OBSERVED and DERIVED facts only and never an
interpretation; it never guesses what it cannot establish:

* the quality gate runs first; anything but ``ACCEPT`` yields a fact set with **no facts** (the
  quality result with its reasons is the evidence);
* an undetermined hand side yields ``NOT_EVALUABLE`` facts for everything that needs the side
  (no silent mirroring, no coordinate guess);
* line analysis is whatever the configured analyzer honestly is: with no palm-line model the
  production default reports ``MODEL_UNAVAILABLE`` and the line facts are ``NOT_EVALUABLE``;
* palmistry line roles (Life, Head, ...) are **not assigned** here: assignment needs a validated
  rule set (a role fact is ``NOT_EVALUABLE``: ``ROLE_ASSIGNMENT_UNVALIDATED``). The Health /
  Mercury role additionally carries the recorded source conflict.

Identical image bytes, configuration, analyzer and runtime give identical facts (reproducibility
within a tolerance is checked by :mod:`pandit_palm_vision.reproducibility`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from pandit_contracts.palm import (
    ConfidenceScore,
    Derivation,
    FactClass,
    FactType,
    FactValue,
    Geometry,
    HandSide,
    ImageRef,
    LineAnalysisStatus,
    ModelArtifactRef,
    PalmFact,
    PalmFactSet,
    Provenance,
    QualityOutcome,
    QualityResult,
    Visibility,
    VisibilityState,
    build_palm_fact,
    build_palm_fact_set,
    make_analysis_id,
)
from pandit_contracts.palm_canonical import sha256_hex, to_fixed

from pandit_palm_vision.frame import (
    MOUNT_ANCHORS,
    MOUNT_REGION_DEFINITION_ID,
    MOUNTS_NOT_EVALUABLE,
    PALM_REGION_DEFINITION_ID,
    PalmFrame,
    build_frame,
    landmark_points_pcf,
    mount_polygon_pcf,
    palm_polygon_pcf,
    quantize,
    venus_polygon_pcf,
)
from pandit_palm_vision.hand import HandCandidate, HandDetector
from pandit_palm_vision.identity import (
    INFERENCE_CONFIG,
    PIPELINE_VERSION,
    PREPROCESSING_ID,
    PREPROCESSING_VERSION,
    preprocessing_parameters_sha256,
    runtime_identity,
)
from pandit_palm_vision.image_input import CaptureContext, ImageInput, decode_image
from pandit_palm_vision.lines import (
    LineAnalysisResult,
    LineAnalyzer,
    LineTrackResult,
    ModelUnavailableLineAnalyzer,
    polyline_intersection,
    polyline_length,
)
from pandit_palm_vision.quality import DEFAULT_QUALITY_CONFIG, QualityConfig, evaluate_quality
from pandit_palm_vision.side import SideResult, classify_side

LANDMARK_METHOD = "HAND_LANDMARKS_PCF1_V1"
LENGTH_METHOD = "POLYLINE_LENGTH_PCF1_V1"
INTERSECTION_METHOD = "POLYLINE_INTERSECTION_PCF1_V1"
# Roles of the first Western profile: nothing assigns them yet (validated assignment required).
LINE_ROLES = (
    "LIFE",
    "HEAD",
    "HEART",
    "FATE",
    "SUN_APOLLO",
    "MERCURY_LINE_VARIANT",  # the sources disagree on this line's definition: UNRESOLVED_CONFLICT
)
ROLE_REASON = "ROLE_ASSIGNMENT_UNVALIDATED"
ROLE_CONFLICT_REASON = "SOURCE_CONFLICT_MERCURY_LINE_DEFINITION"
REGION_REASON = "ROLE_ASSIGNMENT_UNVALIDATED"


@dataclass(frozen=True)
class PipelineResult:
    fact_set: PalmFactSet
    quality: QualityResult
    side: SideResult | None
    line_status: LineAnalysisStatus


class _FactFactory:
    """Builds facts that share one analysis, quality result, provenance and image."""

    def __init__(
        self, analysis_id: str, quality: QualityResult, provenance: Provenance, image_ref: ImageRef
    ) -> None:
        self._base: dict[str, Any] = {
            "analysis_id": analysis_id,
            "quality_ref": quality.quality_ref,
            "provenance": provenance.provenance_id,
            "image_ref": image_ref,
        }

    def make(
        self,
        *,
        fact_class: FactClass,
        fact_type: FactType,
        side: HandSide,
        score_bp: int,
        visibility: Visibility | None = None,
        region_id: str | None = None,
        geometry: Geometry | None = None,
        value: FactValue | None = None,
        derived_from: tuple[str, ...] = (),
        derivation: Derivation | None = None,
    ) -> PalmFact:
        return build_palm_fact(
            **self._base,
            fact_class=fact_class,
            fact_type=fact_type,
            hand_side=side,
            region_id=region_id,
            geometry=geometry,
            value=value or FactValue(),
            confidence=ConfidenceScore(score_bp=score_bp),
            visibility=visibility or Visibility(state=VisibilityState.CLEAR),
            derived_from=derived_from,
            derivation=derivation,
        )

    def not_evaluable(
        self,
        fact_type: FactType,
        side: HandSide,
        region_id: str,
        reason: str,
        *,
        derived_from: tuple[str, ...] = (),
        method: str = "NOT_EVALUABLE_V1",
    ) -> PalmFact:
        derived = bool(derived_from)
        return self.make(
            fact_class=FactClass.DERIVED if derived else FactClass.OBSERVED,
            fact_type=fact_type,
            side=side,
            score_bp=0,
            visibility=Visibility(state=VisibilityState.NOT_EVALUABLE, reason=reason),
            region_id=region_id,
            derived_from=derived_from,
            derivation=Derivation(method_id=method, method_version="1") if derived else None,
        )


class PalmPipeline:
    def __init__(
        self,
        detector: HandDetector,
        line_analyzer: LineAnalyzer | None = None,
        quality_config: QualityConfig = DEFAULT_QUALITY_CONFIG,
        side_min_confidence_bp: int | None = None,
    ) -> None:
        self.detector = detector
        self.line_analyzer: LineAnalyzer = line_analyzer or ModelUnavailableLineAnalyzer()
        self.quality_config = quality_config
        self.side_min_confidence_bp = side_min_confidence_bp

    # ------------------------------------------------------------------ provenance
    def _provenance(
        self, models: tuple[ModelArtifactRef, ...], detector_id: str, detector_version: str
    ) -> Provenance:
        inference = {
            **INFERENCE_CONFIG,
            "detector": f"{detector_id}:{detector_version}",
            "lines": self.line_analyzer.identity(),
            "side_min_confidence_bp": self.side_min_confidence_bp,
        }
        all_models = tuple(
            sorted({*models, *self.line_analyzer.models()}, key=lambda m: m.artifact_id)
        )
        return Provenance(
            pipeline_version=PIPELINE_VERSION,
            preprocessing_id=PREPROCESSING_ID,
            preprocessing_version=PREPROCESSING_VERSION,
            parameters_sha256=preprocessing_parameters_sha256(),
            normalized_input_sha256="0" * 64,  # replaced per image below
            quality_config_id=self.quality_config.config_id,
            quality_config_version=self.quality_config.version,
            quality_calibration_status=self.quality_config.calibration_status,
            inference_config_sha256=sha256_hex(inference),
            line_analysis_status=self.line_analyzer.declared_status,
            models=all_models,
            runtime=runtime_identity(),
        )

    # ------------------------------------------------------------------ run
    def run_bytes(
        self, data: bytes, image_id: str, context: CaptureContext | None = None
    ) -> PipelineResult:
        return self.run(decode_image(data, image_id), context or CaptureContext())

    def run(self, image: ImageInput, context: CaptureContext | None = None) -> PipelineResult:
        context = context or CaptureContext()
        detection = self.detector.detect(image)
        evaluation = evaluate_quality(image, detection.candidates, self.quality_config)
        quality = evaluation.result
        provenance = self._provenance(
            detection.models, detection.detector_id, detection.detector_version
        )
        provenance = provenance.model_copy(
            update={"normalized_input_sha256": image.normalized_input_sha256}
        )
        analysis_id = make_analysis_id(image.ref, provenance)

        facts: list[PalmFact] = []
        side_result: SideResult | None = None
        line_status = self.line_analyzer.declared_status
        hand = evaluation.hand
        if quality.outcome is QualityOutcome.ACCEPT and hand is not None:
            factory = _FactFactory(analysis_id, quality, provenance, image.ref)
            side_result = classify_side(
                hand, context, detection.assumes_mirrored_input, self.side_min_confidence_bp
            )
            facts, line_status = self._facts(factory, image, hand, side_result, context)
        fact_set = build_palm_fact_set(
            analysis_id=analysis_id,
            image_ref=image.ref,
            quality_result=quality,
            facts=facts,
            provenance_blocks=[provenance],
        )
        return PipelineResult(fact_set, quality, side_result, line_status)

    # ------------------------------------------------------------------ facts
    def _facts(
        self,
        factory: _FactFactory,
        image: ImageInput,
        hand: HandCandidate,
        side_result: SideResult,
        context: CaptureContext,
    ) -> tuple[list[PalmFact], LineAnalysisStatus]:
        side = side_result.side
        determined = side is not HandSide.UNDETERMINED
        side_fact = factory.make(
            fact_class=FactClass.OBSERVED,
            fact_type=FactType.HAND_SIDE,
            side=side,
            score_bp=side_result.confidence_bp,
            visibility=Visibility(state=VisibilityState.CLEAR)
            if determined
            else Visibility(
                state=VisibilityState.NOT_EVALUABLE,
                reason=side_result.reasons[0] if side_result.reasons else "SIDE_UNDETERMINED",
            ),
            region_id="HAND",
            value=FactValue(kind="ENUM", v=side.value),
        )
        facts = [side_fact]
        if not determined:
            for fact_type, region in (
                (FactType.LANDMARK_SET, "LANDMARKS.HAND_21"),
                (FactType.PALM_REGION, "PALM"),
            ):
                facts.append(
                    factory.not_evaluable(
                        fact_type,
                        side,
                        region,
                        "SIDE_UNDETERMINED",
                        derived_from=(side_fact.fact_id,),
                    )
                )
            return facts, self.line_analyzer.declared_status

        frame = build_frame(hand, side, image.width, image.height, bool(context.mirrored))
        landmarks = landmark_points_pcf(hand, frame)
        mirror_flag = "MIRRORED_FOR_CANONICAL" if frame.mirrored_for_canonical else "NOT_MIRRORED"
        landmark_fact = factory.make(
            fact_class=FactClass.OBSERVED,
            fact_type=FactType.LANDMARK_SET,
            side=side,
            score_bp=hand.presence_bp,
            region_id="LANDMARKS.HAND_21",
            geometry=Geometry(kind="POINT_SET", coords_fixed=quantize(landmarks)),
            value=FactValue(kind="ENUM", v=mirror_flag),
        )
        facts.append(landmark_fact)
        parent = (landmark_fact.fact_id,)
        facts.append(
            factory.make(
                fact_class=FactClass.DERIVED,
                fact_type=FactType.PALM_REGION,
                side=side,
                score_bp=hand.presence_bp,
                region_id="PALM",
                geometry=Geometry(
                    kind="POLYGON", coords_fixed=quantize(palm_polygon_pcf(landmarks))
                ),
                value=FactValue(kind="ENUM", v=mirror_flag),
                derived_from=parent,
                derivation=Derivation(method_id=PALM_REGION_DEFINITION_ID, method_version="1"),
            )
        )
        for name in sorted(MOUNT_ANCHORS):
            facts.append(
                factory.make(
                    fact_class=FactClass.DERIVED,
                    fact_type=FactType.MOUNT_REGION,
                    side=side,
                    score_bp=hand.presence_bp,
                    region_id=name,
                    geometry=Geometry(
                        kind="POLYGON", coords_fixed=quantize(mount_polygon_pcf(name, landmarks))
                    ),
                    value=FactValue(kind="ENUM", v="PROJECT_DERIVED_POSITION_ONLY"),
                    derived_from=parent,
                    derivation=Derivation(method_id=MOUNT_REGION_DEFINITION_ID, method_version="1"),
                )
            )
        facts.append(
            factory.make(
                fact_class=FactClass.DERIVED,
                fact_type=FactType.MOUNT_REGION,
                side=side,
                score_bp=hand.presence_bp,
                region_id="MOUNT.VENUS",
                geometry=Geometry(
                    kind="POLYGON", coords_fixed=quantize(venus_polygon_pcf(landmarks))
                ),
                value=FactValue(kind="ENUM", v="PROJECT_DERIVED_POSITION_ONLY"),
                derived_from=parent,
                derivation=Derivation(method_id=MOUNT_REGION_DEFINITION_ID, method_version="1"),
            )
        )
        for name, reason in sorted(MOUNTS_NOT_EVALUABLE.items()):
            facts.append(
                factory.not_evaluable(
                    FactType.MOUNT_REGION, side, name, reason, derived_from=parent
                )
            )

        analysis = self.line_analyzer.analyze(image, frame, hand)
        facts.extend(self._line_facts(factory, side, parent, frame, analysis))
        return facts, analysis.status

    def _line_facts(
        self,
        factory: _FactFactory,
        side: HandSide,
        parent: tuple[str, ...],
        frame: PalmFrame,
        analysis: LineAnalysisResult,
    ) -> list[PalmFact]:
        facts: list[PalmFact] = []
        if analysis.status is LineAnalysisStatus.MODEL_UNAVAILABLE:
            facts.append(
                factory.not_evaluable(
                    FactType.LINE_TRACK, side, "LINES.ALL", "PALM_LINE_MODEL_UNAVAILABLE"
                )
            )
        tracks = sorted(analysis.tracks, key=lambda t: (-t.score_bp, t.points_pcf))
        track_facts: list[tuple[PalmFact, LineTrackResult]] = []
        for index, track in enumerate(tracks):
            fact = factory.make(
                fact_class=FactClass.OBSERVED,
                fact_type=FactType.LINE_TRACK,
                side=side,
                score_bp=track.score_bp,
                region_id=f"TRACK.{index:02d}",
                geometry=Geometry(
                    kind="POLYLINE",
                    coords_fixed=quantize(np.asarray(track.points_pcf, dtype=np.float64)),
                    sampling_spec="CENTRE_LINE_ORDERED",
                ),
            )
            track_facts.append((fact, track))
            facts.append(fact)
            facts.append(
                factory.make(
                    fact_class=FactClass.DERIVED,
                    fact_type=FactType.LINE_ATTRIBUTE,
                    side=side,
                    score_bp=track.score_bp,
                    region_id=f"TRACK.{index:02d}",
                    value=FactValue(
                        kind="RATIO_FIXED",
                        v=to_fixed(polyline_length(track.points_pcf)),
                        unit="PALM_UNIT_E-4",
                    ),
                    derived_from=(fact.fact_id,),
                    derivation=Derivation(method_id=LENGTH_METHOD, method_version="1"),
                )
            )
        for i, (fact_a, track_a) in enumerate(track_facts):
            for j in range(i + 1, len(track_facts)):
                fact_b, track_b = track_facts[j]
                crossing = polyline_intersection(track_a.points_pcf, track_b.points_pcf)
                if crossing is None:
                    continue
                facts.append(
                    factory.make(
                        fact_class=FactClass.DERIVED,
                        fact_type=FactType.LINE_INTERSECTION,
                        side=side,
                        score_bp=min(track_a.score_bp, track_b.score_bp),
                        region_id=f"TRACK.{i:02d}X{j:02d}",
                        geometry=Geometry(
                            kind="POINT",
                            coords_fixed=((to_fixed(crossing[0]), to_fixed(crossing[1])),),
                        ),
                        derived_from=(fact_a.fact_id, fact_b.fact_id),
                        derivation=Derivation(method_id=INTERSECTION_METHOD, method_version="1"),
                    )
                )
        for role in LINE_ROLES:
            reason = ROLE_CONFLICT_REASON if role == "MERCURY_LINE_VARIANT" else ROLE_REASON
            facts.append(
                factory.not_evaluable(
                    FactType.LINE_ROLE_CANDIDATE,
                    side,
                    f"ROLE.{role}",
                    reason,
                    derived_from=parent,
                    method="LINE_ROLE_ASSIGNMENT_NOT_IMPLEMENTED_V1",
                )
            )
        for region in ("TRIANGLE", "QUADRANGLE"):
            facts.append(
                factory.not_evaluable(
                    FactType.REGION_GEOMETRY,
                    side,
                    f"REGION.{region}",
                    REGION_REASON,
                    derived_from=parent,
                    method="LINE_BOUNDED_REGION_NOT_IMPLEMENTED_V1",
                )
            )
        return facts
