from __future__ import annotations

from typing import Any

import pytest
from palm_helpers import IMAGE, make_fact, make_provenance, make_quality, make_set
from pydantic import ValidationError

from pandit_contracts.palm import (
    CalibrationStatus,
    ConfidenceScore,
    Derivation,
    FactClass,
    FactType,
    FactValue,
    Geometry,
    Labelling,
    LineAnalysisStatus,
    ModelArtifactRef,
    PalmEvidenceBundle,
    PalmFact,
    PalmRuleEvaluation,
    RuleStatus,
    Uncertainty,
    Visibility,
    VisibilityState,
    build_palm_evidence_bundle,
    build_palm_fact,
    build_palm_fact_set,
    canonical_form,
    make_analysis_id,
)
from pandit_contracts.palm_canonical import FloatInCanonicalDataError, canonical_json

KV = "KV-TEST-PALM"


def _evaluation(fact_id: str, **overrides: Any) -> PalmRuleEvaluation:
    fields: dict[str, Any] = {
        "rule_id": "PALMR_TEST",
        "rule_version": "1",
        "source_profile": "PALM_CH_LINES_PART1",
        "source_location": "Part I ch. XVII",
        "status": RuleStatus.TRIGGERED,
        "fact_refs": (fact_id,),
        "knowledge_version": KV,
        "ruleset_id": "RS",
        "source_id": "SRC-CHEIRO-PALMISTRY-FOR-ALL-1916",
        "standards_version": "1.28.0",
        "interpretation_tags": ("LEFT_HAND_INHERITED_TENDENCIES",),
    }
    fields.update(overrides)
    return PalmRuleEvaluation(**fields)


# ---- fact identity ---------------------------------------------------------------------------
def test_the_same_inputs_give_the_same_fact_hash_and_id() -> None:
    one, _, _ = make_set()
    two, _, _ = make_set()
    assert one.fact_set_hash == two.fact_set_hash
    assert [f.fact_id for f in one.facts] == [f.fact_id for f in two.facts]
    assert all(f.fact_id == "PF-" + f.fact_hash[:16] for f in one.facts)


def test_fact_order_never_changes_the_fact_set_hash() -> None:
    fact_set, prov, quality = make_set()
    reordered = build_palm_fact_set(
        analysis_id=fact_set.analysis_id,
        image_ref=IMAGE,
        quality_result=quality,
        facts=list(reversed(fact_set.facts)),
        provenance_blocks=[prov],
    )
    assert reordered.fact_set_hash == fact_set.fact_set_hash


def test_a_timestamp_does_not_affect_identity() -> None:
    fact_set, prov, quality = make_set()
    stamped = build_palm_fact_set(
        analysis_id=fact_set.analysis_id,
        image_ref=IMAGE,
        quality_result=quality,
        facts=list(fact_set.facts),
        provenance_blocks=[prov],
        created_at="2026-10-02T12:00:00Z",
    )
    assert stamped.created_at is not None
    assert stamped.fact_set_hash == fact_set.fact_set_hash
    one = build_palm_evidence_bundle(fact_set=fact_set, rule_evaluations=[], knowledge_version=KV)
    two = build_palm_evidence_bundle(fact_set=stamped, rule_evaluations=[], knowledge_version=KV)
    assert one.bundle_hash == two.bundle_hash


def test_a_content_change_changes_the_hash() -> None:
    fact_set, prov, quality = make_set()
    side = fact_set.facts_of_type(FactType.HAND_SIDE)[0]
    other = make_fact(
        fact_set.analysis_id,
        prov,
        quality,
        confidence=ConfidenceScore(score_bp=9001),
    )
    assert other.fact_hash != side.fact_hash
    assert other.fact_id != side.fact_id


def test_a_tampered_hash_or_id_cannot_be_constructed() -> None:
    fact_set, _, _ = make_set()
    side = fact_set.facts[0]
    data = side.model_dump()
    data["fact_hash"] = "e" * 64
    with pytest.raises(ValidationError):
        PalmFact(**data)
    data = side.model_dump()
    data["fact_id"] = "PF-0000000000000000"
    with pytest.raises(ValidationError):
        PalmFact(**data)


def test_canonical_form_has_no_floats_and_matches_the_hashed_content() -> None:
    fact_set, _, _ = make_set()
    for fact in fact_set.facts:
        text = canonical_form(fact)
        assert "." not in text.replace("1.0.0", "")  # only the dotted version strings remain
    assert canonical_form(fact_set).startswith("{")


@pytest.mark.parametrize("bad", [0.5, 1.0])
def test_floats_cannot_enter_a_fact_even_when_integral(bad: float) -> None:
    prov = make_provenance()
    quality = make_quality()
    with pytest.raises(ValidationError):
        make_fact(
            make_analysis_id(IMAGE, prov),
            prov,
            quality,
            fact_type=FactType.LINE_TRACK,
            value=FactValue(),
            geometry=Geometry(kind="POLYLINE", coords_fixed=((0, 0), (bad, 1))),  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError):
        ConfidenceScore(score_bp=bad)  # type: ignore[arg-type]
    with pytest.raises(FloatInCanonicalDataError):
        canonical_json({"coords": [(0, bad)]})


# ---- the three layers ------------------------------------------------------------------------
def test_interpreted_is_not_a_fact_class() -> None:
    assert {c.value for c in FactClass} == {"OBSERVED", "DERIVED"}
    prov = make_provenance()
    with pytest.raises(ValueError):
        FactClass("INTERPRETED")
    with pytest.raises(ValidationError):
        make_fact(make_analysis_id(IMAGE, prov), prov, make_quality(), fact_class="INTERPRETED")


def test_observed_facts_have_no_derivation_and_derived_facts_name_their_sources() -> None:
    prov = make_provenance()
    quality = make_quality()
    aid = make_analysis_id(IMAGE, prov)
    with pytest.raises(ValidationError):
        make_fact(aid, prov, quality, derivation=Derivation(method_id="X", method_version="1"))
    with pytest.raises(ValidationError):
        make_fact(aid, prov, quality, fact_class=FactClass.DERIVED)


def test_a_palmistry_label_is_only_on_a_derived_fact() -> None:
    prov = make_provenance()
    quality = make_quality()
    aid = make_analysis_id(IMAGE, prov)
    label = Labelling(
        source_profile="PALM_HA_MAP_LINES_384_393",
        source_id="SRC-HERONALLEN-CHEIROSOPHY",
        source_location="para. 384, p. 190",
        rule="LIFE_LINE_ENCIRCLES_THUMB_BASE",
    )
    with pytest.raises(ValidationError):
        make_fact(aid, prov, quality, labelling=label)


def test_not_evaluable_needs_a_reason() -> None:
    with pytest.raises(ValidationError):
        Visibility(state=VisibilityState.NOT_EVALUABLE)
    assert Visibility(state=VisibilityState.NOT_EVALUABLE, reason="MODEL_UNAVAILABLE")


def test_value_kind_must_match_the_value() -> None:
    with pytest.raises(ValidationError):
        FactValue(kind="INT", v="x")
    with pytest.raises(ValidationError):
        FactValue(kind="NONE", v=3)
    assert FactValue(kind="BOOL", v=True)


def test_geometry_shapes_are_checked() -> None:
    with pytest.raises(ValidationError):
        Geometry(kind="POINT", coords_fixed=((0, 0), (1, 1)))
    with pytest.raises(ValidationError):
        Geometry(kind="POLYLINE", coords_fixed=((0, 0),))
    with pytest.raises(ValidationError):
        Geometry(kind="POLYGON", coords_fixed=((0, 0), (1, 1)))


def test_confidence_calibration_is_explicit_and_uncertainty_is_separate() -> None:
    with pytest.raises(ValidationError):
        ConfidenceScore(score_bp=5000, calibrated=True)
    with pytest.raises(ValidationError):
        Uncertainty(kind="INTERVAL", lo_fixed=5, hi_fixed=1)
    assert Uncertainty().kind == "NONE"


# ---- the fact set ----------------------------------------------------------------------------
def test_a_fact_set_rejects_foreign_facts_and_dangling_references() -> None:
    fact_set, prov, quality = make_set()
    stranger = make_fact("PA-OTHER", prov, quality)
    with pytest.raises(ValidationError):
        build_palm_fact_set(
            analysis_id=fact_set.analysis_id,
            image_ref=IMAGE,
            quality_result=quality,
            facts=[*fact_set.facts, stranger],
            provenance_blocks=[prov],
        )
    orphan = make_fact(
        fact_set.analysis_id,
        prov,
        quality,
        fact_class=FactClass.DERIVED,
        fact_type=FactType.RATIO,
        derived_from=("PF-doesnotexist000",),
        derivation=Derivation(method_id="X", method_version="1"),
    )
    with pytest.raises(ValidationError):
        build_palm_fact_set(
            analysis_id=fact_set.analysis_id,
            image_ref=IMAGE,
            quality_result=quality,
            facts=[*fact_set.facts, orphan],
            provenance_blocks=[prov],
        )
    with pytest.raises(ValidationError):
        build_palm_fact_set(
            analysis_id=fact_set.analysis_id,
            image_ref=IMAGE,
            quality_result=quality,
            facts=list(fact_set.facts),
            provenance_blocks=[make_provenance(pipeline_version="9.9.9")],
        )


def test_the_image_is_referenced_by_hash_never_embedded() -> None:
    fact_set, _, _ = make_set()
    dumped = canonical_form(fact_set)
    assert IMAGE.content_sha256 in dumped
    assert "bytes" not in fact_set.image_ref.model_dump()
    with pytest.raises(ValidationError):
        build_palm_fact(
            **{
                **fact_set.facts[0].model_dump(exclude={"fact_id", "fact_hash"}),
                "image_ref": {"image_id": "x", "content_sha256": "short"},
            }
        )


def test_the_analysis_id_is_deterministic_from_image_and_pipeline_identity() -> None:
    prov = make_provenance()
    assert make_analysis_id(IMAGE, prov) == make_analysis_id(IMAGE, prov)
    assert make_analysis_id(IMAGE, prov) != make_analysis_id(
        IMAGE, make_provenance(pipeline_version="0.2.0")
    )


# ---- rule evaluation -------------------------------------------------------------------------
def test_rule_evaluation_rules() -> None:
    with pytest.raises(ValidationError):
        _evaluation("PF-1", status=RuleStatus.NOT_EVALUABLE, interpretation_tags=())
    with pytest.raises(ValidationError):
        _evaluation("PF-1", status=RuleStatus.NOT_TRIGGERED, reason="x")
    with pytest.raises(ValidationError):
        _evaluation("PF-1", fact_refs=())
    ok = _evaluation(
        "PF-1", status=RuleStatus.NOT_EVALUABLE, interpretation_tags=(), reason="FACT_MISSING"
    )
    assert ok.interpretation_tags == ()


# ---- the evidence bundle ---------------------------------------------------------------------
def test_bundle_connects_facts_rules_and_sources_and_is_deterministic() -> None:
    fact_set, _, _ = make_set()
    side = fact_set.facts_of_type(FactType.HAND_SIDE)[0]
    ev = _evaluation(side.fact_id)
    one = build_palm_evidence_bundle(fact_set=fact_set, rule_evaluations=[ev], knowledge_version=KV)
    two = build_palm_evidence_bundle(fact_set=fact_set, rule_evaluations=[ev], knowledge_version=KV)
    assert one == two and one.bundle_hash == two.bundle_hash
    assert one.hand_fact_ids == (side.fact_id,)
    assert len(one.line_fact_ids) == 2 and not one.landmark_fact_ids
    assert one.source_refs[0].source_profile == "PALM_CH_LINES_PART1"
    assert one.uncertainty_summary.facts_total == 3
    assert one.uncertainty_summary.rules_by_status == (("TRIGGERED", 1),)


def test_a_later_phase_can_check_that_a_claim_cites_the_bundle() -> None:
    fact_set, _, _ = make_set()
    side = fact_set.facts_of_type(FactType.HAND_SIDE)[0]
    bundle = build_palm_evidence_bundle(
        fact_set=fact_set, rule_evaluations=[_evaluation(side.fact_id)], knowledge_version=KV
    )
    assert bundle.is_claim_supported(side.fact_id)
    assert bundle.is_claim_supported("PALMR_TEST")
    assert not bundle.is_claim_supported("PF-invented0000000")
    assert not bundle.is_claim_supported("PALMR_INVENTED")


def test_bundle_hash_changes_with_the_evaluations() -> None:
    fact_set, _, _ = make_set()
    side = fact_set.facts_of_type(FactType.HAND_SIDE)[0]
    one = build_palm_evidence_bundle(
        fact_set=fact_set, rule_evaluations=[_evaluation(side.fact_id)], knowledge_version=KV
    )
    two = build_palm_evidence_bundle(
        fact_set=fact_set,
        rule_evaluations=[_evaluation(side.fact_id, interpretation_tags=("OTHER_TAG",))],
        knowledge_version=KV,
    )
    assert one.bundle_hash != two.bundle_hash


def test_bundle_rejects_a_dangling_fact_ref_and_a_knowledge_version_mismatch() -> None:
    fact_set, _, _ = make_set()
    with pytest.raises(ValidationError):
        build_palm_evidence_bundle(
            fact_set=fact_set,
            rule_evaluations=[_evaluation("PF-nothere00000000")],
            knowledge_version=KV,
        )
    side = fact_set.facts_of_type(FactType.HAND_SIDE)[0]
    with pytest.raises(ValidationError):
        build_palm_evidence_bundle(
            fact_set=fact_set,
            rule_evaluations=[_evaluation(side.fact_id, knowledge_version="KV-OTHER")],
            knowledge_version=KV,
        )


def test_a_tampered_bundle_cannot_be_constructed() -> None:
    fact_set, _, _ = make_set()
    bundle = build_palm_evidence_bundle(
        fact_set=fact_set, rule_evaluations=[], knowledge_version=KV
    )
    data = bundle.model_dump()
    data["bundle_hash"] = "f" * 64
    with pytest.raises(ValidationError):
        PalmEvidenceBundle(**data)


def test_readiness_is_never_silently_ready() -> None:
    fact_set, _, _ = make_set()
    bundle = build_palm_evidence_bundle(
        fact_set=fact_set, rule_evaluations=[], knowledge_version=KV
    )
    assert bundle.production_ready is False
    assert "LINE_ANALYSIS_MODEL_UNAVAILABLE" in bundle.readiness_blockers
    assert "QUALITY_THRESHOLDS_FIXTURE_ONLY" in bundle.readiness_blockers
    assert "REPRODUCIBILITY_TOLERANCES_CALIBRATION_REQUIRED" in bundle.readiness_blockers
    assert "LEGAL_REVIEW_GATE_OPEN" in bundle.readiness_blockers


def test_unverified_model_artifacts_are_a_blocker() -> None:
    prov = make_provenance(
        line_analysis_status=LineAnalysisStatus.TRAINED_MODEL,
        quality_calibration_status=CalibrationStatus.CALIBRATED,
        models=(ModelArtifactRef(artifact_id="M1", version="1", role="line", sha256="a" * 64),),
    )
    quality = make_quality()
    aid = make_analysis_id(IMAGE, prov)
    fact = make_fact(aid, prov, quality)
    fact_set = build_palm_fact_set(
        analysis_id=aid,
        image_ref=IMAGE,
        quality_result=quality,
        facts=[fact],
        provenance_blocks=[prov],
    )
    bundle = build_palm_evidence_bundle(
        fact_set=fact_set, rule_evaluations=[], knowledge_version=KV
    )
    assert "MODEL_ARTIFACT_UNVERIFIED_M1" in bundle.readiness_blockers
