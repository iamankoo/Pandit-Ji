"""Helpers for the palm ruleset tests (synthetic facts built with the contracts only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pandit_contracts.palm import (
    CalibrationStatus,
    ConfidenceScore,
    Derivation,
    FactClass,
    FactType,
    FactValue,
    HandSide,
    ImageRef,
    Labelling,
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
from pandit_contracts.palm_coverage import CoverageRecord, PalmSourceCoverage

REPO = Path(__file__).resolve().parents[3]
PALM_RULES_DIR = REPO / "services" / "rule-engine" / "palm_rules"
VEDIC_RULES_DIR = REPO / "services" / "knowledge" / "rules"
PALM_COVERAGE_FILE = REPO / "services" / "knowledge" / "content" / "palm" / "source_coverage.yaml"
KV = "KV-TEST-PALM"
IMAGE = ImageRef(image_id="IMG-SYNTH-RULES", content_sha256="d" * 64)
HA_MAP = "PALM_HA_MAP_LINES_384_393"


def load_coverage(path: Path = PALM_COVERAGE_FILE) -> PalmSourceCoverage:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return PalmSourceCoverage(
        manifest_id=data["manifest_id"],
        manifest_version=data["manifest_version"],
        records=tuple(CoverageRecord(**r) for r in data["records"]),
    )


def _provenance() -> Provenance:
    return Provenance(
        pipeline_version="test",
        preprocessing_id="PRE",
        preprocessing_version="1",
        parameters_sha256="a" * 64,
        normalized_input_sha256="b" * 64,
        quality_config_id="QC-TEST",
        quality_config_version="1",
        quality_calibration_status=CalibrationStatus.FIXTURE_ONLY,
        inference_config_sha256="c" * 64,
        line_analysis_status=LineAnalysisStatus.FIXTURE_SYNTHETIC,
        runtime=RuntimeIdentity(python="3.12.0"),
    )


def _quality() -> QualityResult:
    return QualityResult(
        outcome=QualityOutcome.ACCEPT,
        checks=(QualityCheckResult(check="blur", status=QualityCheckStatus.PASS),),
        config_id="QC-TEST",
        config_version="1",
        calibration_status=CalibrationStatus.FIXTURE_ONLY,
    )


def fact_set(
    side: HandSide, *, with_roles: bool = False, not_evaluable_roles: bool = False
) -> PalmFactSet:
    """A synthetic fact set. ``with_roles`` adds the labelled line facts the HA rules need;
    ``not_evaluable_roles`` adds the NOT_EVALUABLE role facts the real pipeline produces."""
    prov, quality = _provenance(), _quality()
    analysis = make_analysis_id(IMAGE, prov)
    base: dict[str, Any] = {
        "analysis_id": analysis,
        "quality_ref": quality.quality_ref,
        "provenance": prov.provenance_id,
        "image_ref": IMAGE,
        "confidence": ConfidenceScore(score_bp=9000),
    }

    def make(**kw: Any) -> PalmFact:
        return build_palm_fact(**base, **kw)

    side_fact = make(
        fact_class=FactClass.OBSERVED,
        fact_type=FactType.HAND_SIDE,
        hand_side=side,
        value=FactValue(kind="ENUM", v=side.value),
        visibility=Visibility(state=VisibilityState.CLEAR),
        region_id="HAND",
    )
    facts = [side_fact]
    derivation = Derivation(method_id="TEST", method_version="1")
    if with_roles:
        for role, attribute in (
            ("LIFE", "START_REGION:MOUNT.JUPITER"),
            ("FATE", "ORIGIN:ROLE.LIFE"),
        ):
            label = Labelling(
                source_profile=HA_MAP,
                source_id="SRC-HERONALLEN-CHEIROSOPHY",
                source_location="para. 384, p. 190",
                rule=f"{role}_LOCATION_DEFINITION",
            )
            role_fact = make(
                fact_class=FactClass.DERIVED,
                fact_type=FactType.LINE_ROLE_CANDIDATE,
                hand_side=side,
                region_id=f"ROLE.{role}",
                value=FactValue(kind="ENUM", v=role),
                visibility=Visibility(state=VisibilityState.CLEAR),
                derived_from=(side_fact.fact_id,),
                derivation=derivation,
                labelling=label,
            )
            facts.append(role_fact)
            facts.append(
                make(
                    fact_class=FactClass.DERIVED,
                    fact_type=FactType.LINE_ATTRIBUTE,
                    hand_side=side,
                    region_id=f"ROLE.{role}",
                    value=FactValue(kind="ENUM", v=attribute),
                    visibility=Visibility(state=VisibilityState.CLEAR),
                    derived_from=(role_fact.fact_id,),
                    derivation=derivation,
                )
            )
    if not_evaluable_roles:
        for role in ("LIFE", "FATE"):
            facts.append(
                make(
                    fact_class=FactClass.DERIVED,
                    fact_type=FactType.LINE_ROLE_CANDIDATE,
                    hand_side=side,
                    region_id=f"ROLE.{role}",
                    visibility=Visibility(
                        state=VisibilityState.NOT_EVALUABLE, reason="ROLE_ASSIGNMENT_UNVALIDATED"
                    ),
                    derived_from=(side_fact.fact_id,),
                    derivation=derivation,
                )
            )
    return build_palm_fact_set(
        analysis_id=analysis,
        image_ref=IMAGE,
        quality_result=quality,
        facts=facts,
        provenance_blocks=[prov],
    )
