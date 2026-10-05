"""Builders for the Phase 16 verification tests.

Everything here is synthetic and uses only the public contracts and the verification package, so
the component's CI job (which installs contracts and shared only) can run it. The palmistry bundle is
a real ``PalmEvidenceBundle`` (real content hash, real fact and rule contracts). The astrology
bundle is a pydantic model with the structure of the Phase 6 ``EvidenceBundle`` and the same
hashing rule; ``tests/integration/test_verification_phase16.py`` runs the real bundles.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pandit_contracts.agent import (
    AgentStatus,
    AgentTrace,
    ClaimType,
    Domain,
    EvidenceReference,
    NarrationClaim,
    NarrationResponse,
    NarrationSection,
    UncertaintyFlag,
)
from pandit_contracts.llm import LLMLanguage
from pandit_contracts.palm import (
    CalibrationStatus,
    ConfidenceScore,
    Derivation,
    FactClass,
    FactType,
    FactValue,
    HandSide,
    ImageRef,
    LineAnalysisStatus,
    PalmEvidenceBundle,
    PalmFact,
    PalmRuleEvaluation,
    Provenance,
    QualityCheckResult,
    QualityCheckStatus,
    QualityOutcome,
    QualityResult,
    RuleStatus,
    RuntimeIdentity,
    Visibility,
    VisibilityState,
    build_palm_evidence_bundle,
    build_palm_fact,
    build_palm_fact_set,
    make_analysis_id,
)
from pydantic import BaseModel

from pandit_verification import TrustedEvidence, Verifier, VerifierConfig
from pandit_verification.evidence import EvidenceItem

KV = "KV-a21c2c040abe9663"
IMAGE = ImageRef(image_id="IMG-SYNTH-0001", content_sha256="a" * 64)
RULESET_HASH = "8d29a18ccd5e57c5d5ec7c70854a9e45997226f5540eb2d3c1a0bc6099b77209"


# -- palmistry ---------------------------------------------------------------------------------


def _provenance() -> Provenance:
    return Provenance(
        pipeline_version="0.1.0",
        preprocessing_id="PRE-TEST",
        preprocessing_version="1",
        parameters_sha256="b" * 64,
        normalized_input_sha256="c" * 64,
        quality_config_id="QC-TEST",
        quality_config_version="1",
        quality_calibration_status=CalibrationStatus.FIXTURE_ONLY,
        inference_config_sha256="d" * 64,
        line_analysis_status=LineAnalysisStatus.MODEL_UNAVAILABLE,
        models=(),
        runtime=RuntimeIdentity(python="3.12.0", packages=(("numpy", "2.0.0"),)),
    )


def _quality() -> QualityResult:
    return QualityResult(
        outcome=QualityOutcome.ACCEPT,
        checks=(QualityCheckResult(check="blur", status=QualityCheckStatus.PASS, metric_fixed=5),),
        config_id="QC-TEST",
        config_version="1",
        calibration_status=CalibrationStatus.FIXTURE_ONLY,
    )


def _rule(rule_id: str, status: RuleStatus, **kw: Any) -> PalmRuleEvaluation:
    fields: dict[str, Any] = {
        "rule_id": rule_id,
        "rule_version": "1",
        "source_profile": "PALM_HA_LINE_LIFE_523_550",
        "source_location": "para. 538",
        "status": status,
        "knowledge_version": KV,
        "ruleset_id": "PANDIT_JI_PALM_WESTERN_PHASE13",
        "source_id": "SRC-HERONALLEN-CHEIROSOPHY",
        "standards_version": "1.0.0",
    }
    fields.update(kw)
    return PalmRuleEvaluation(**fields)


@dataclass
class PalmWorld:
    bundle: PalmEvidenceBundle
    ids: dict[str, str]  # a name -> a fact id or rule id


def make_palm_world() -> PalmWorld:
    """A palm bundle covering every case the tests need.

    Facts: ``hand`` (OBSERVED, RIGHT, CLEAR), ``landmarks`` (OBSERVED), ``jupiter`` (DERIVED mount,
    CLEAR), ``life`` (DERIVED line role, NOT_EVALUABLE), ``heart`` (OBSERVED, PARTIAL),
    ``weak`` (DERIVED, CLEAR, low confidence), ``left`` (OBSERVED, LEFT, CLEAR).
    Rules: ``trig`` (TRIGGERED, tag AMBITION_INDICATED), ``nottrig``, ``ne`` (NOT_EVALUABLE),
    ``benham`` and ``cheiro`` (TRIGGERED, different sources, one shared conflict),
    ``left_rule`` (TRIGGERED, left hand),
    ``on_partial`` (TRIGGERED over a PARTIAL fact), ``on_unevaluable`` (TRIGGERED over a fact that
    is NOT_EVALUABLE).
    """
    prov = _provenance()
    quality = _quality()
    analysis_id = make_analysis_id(IMAGE, prov)

    def fact(**kw: Any) -> PalmFact:
        fields: dict[str, Any] = {
            "analysis_id": analysis_id,
            "fact_class": FactClass.OBSERVED,
            "fact_type": FactType.HAND_SIDE,
            "hand_side": HandSide.RIGHT,
            "value": FactValue(kind="ENUM", v="RIGHT"),
            "confidence": ConfidenceScore(score_bp=9000),
            "visibility": Visibility(state=VisibilityState.CLEAR),
            "quality_ref": quality.quality_ref,
            "provenance": prov.provenance_id,
            "image_ref": IMAGE,
        }
        fields.update(kw)
        return build_palm_fact(**fields)

    hand = fact(region_id="HAND")
    left = fact(hand_side=HandSide.LEFT, value=FactValue(kind="ENUM", v="LEFT"), region_id="HAND")
    landmarks = fact(
        fact_type=FactType.LANDMARK_SET,
        value=FactValue(kind="ENUM", v="NOT_MIRRORED"),
        region_id="LANDMARKS.HAND_21",
    )
    derivation = Derivation(method_id="PROJECT_REGION", method_version="1")
    jupiter = fact(
        fact_class=FactClass.DERIVED,
        fact_type=FactType.MOUNT_REGION,
        value=FactValue(kind="ENUM", v="PROJECT_DERIVED_POSITION_ONLY"),
        region_id="MOUNT.JUPITER",
        confidence=ConfidenceScore(score_bp=9800),
        derived_from=(landmarks.fact_id,),
        derivation=derivation,
    )
    life = fact(
        fact_class=FactClass.DERIVED,
        fact_type=FactType.LINE_ROLE_CANDIDATE,
        value=FactValue(),
        region_id="ROLE.LIFE",
        confidence=ConfidenceScore(score_bp=0),
        visibility=Visibility(state=VisibilityState.NOT_EVALUABLE, reason="ROLE_UNVALIDATED"),
        derived_from=(landmarks.fact_id,),
        derivation=derivation,
    )
    heart = fact(
        fact_type=FactType.LINE_ATTRIBUTE,
        value=FactValue(kind="ENUM", v="START_REGION:MOUNT.JUPITER"),
        region_id="ROLE.HEART",
        visibility=Visibility(state=VisibilityState.PARTIAL),
    )
    weak = fact(
        fact_class=FactClass.DERIVED,
        fact_type=FactType.MOUNT_REGION,
        value=FactValue(kind="ENUM", v="PROJECT_DERIVED_POSITION_ONLY"),
        region_id="MOUNT.SATURN",
        confidence=ConfidenceScore(score_bp=1000),
        derived_from=(landmarks.fact_id,),
        derivation=derivation,
    )
    facts = [hand, left, landmarks, jupiter, life, heart, weak]
    fact_set = build_palm_fact_set(
        analysis_id=analysis_id,
        image_ref=IMAGE,
        quality_result=quality,
        facts=facts,
        provenance_blocks=[prov],
    )
    ids = {
        "hand": hand.fact_id,
        "left": left.fact_id,
        "landmarks": landmarks.fact_id,
        "jupiter": jupiter.fact_id,
        "life": life.fact_id,
        "heart": heart.fact_id,
        "weak": weak.fact_id,
    }
    benham = dict(
        source_profile="PALM_BE_HANDS_359",
        source_id="SRC-BENHAM-SCIENTIFIC-HAND-READING-1901",
        source_location="p. 359",
    )
    cheiro = dict(
        source_profile="PALM_CH_LINES_PART1",
        source_id="SRC-CHEIRO-PALMISTRY-FOR-ALL-1916",
        source_location="part 1",
    )
    rules = [
        _rule(
            "PALMR_TRIG",
            RuleStatus.TRIGGERED,
            fact_refs=(hand.fact_id,),
            interpretation_tags=("AMBITION_INDICATED",),
        ),
        _rule("PALMR_NOTTRIG", RuleStatus.NOT_TRIGGERED, reason="CONDITIONS_NOT_MET"),
        _rule("PALMR_NE", RuleStatus.NOT_EVALUABLE, reason="REQUIRED_FACT_NOT_EVALUABLE"),
        _rule(
            "PALMR_BENHAM",
            RuleStatus.TRIGGERED,
            fact_refs=(hand.fact_id,),
            interpretation_tags=("RIGHT_HAND_ALTERED_MAP",),
            conflict_ids=("PALM_CROSS_SOURCE.HANDS",),
            **benham,
        ),
        _rule(
            "PALMR_CHEIRO",
            RuleStatus.TRIGGERED,
            fact_refs=(hand.fact_id,),
            interpretation_tags=("RIGHT_HAND_DEVELOPED_QUALITIES",),
            conflict_ids=("PALM_CROSS_SOURCE.HANDS",),
            **cheiro,
        ),
        _rule(
            "PALMR_LEFT_HAND",
            RuleStatus.TRIGGERED,
            fact_refs=(left.fact_id,),
            interpretation_tags=("LEFT_HAND_INHERITED_TENDENCIES",),
        ),
        _rule(
            "PALMR_ON_PARTIAL",
            RuleStatus.TRIGGERED,
            fact_refs=(heart.fact_id,),
            interpretation_tags=("AMBITION_INDICATED",),
        ),
        _rule(
            "PALMR_ON_UNEVALUABLE",
            RuleStatus.TRIGGERED,
            fact_refs=(life.fact_id,),
            interpretation_tags=("AMBITION_INDICATED",),
        ),
    ]
    for rule in rules:
        ids[rule.rule_id.removeprefix("PALMR_").lower()] = rule.rule_id
    bundle = build_palm_evidence_bundle(
        fact_set=fact_set, rule_evaluations=rules, knowledge_version=KV
    )
    return PalmWorld(bundle=bundle, ids=ids)


# -- astrology ---------------------------------------------------------------------------------


class _M(BaseModel):
    model_config = {"frozen": True}


class _Body(str, Enum):
    MARS = "mars"
    VENUS = "venus"
    SATURN = "saturn"
    SUN = "sun"


class _Sign(str, Enum):
    ARIES = "aries"
    LIBRA = "libra"
    CAPRICORN = "capricorn"
    CANCER = "cancer"
    LEO = "leo"


class _Dignity(str, Enum):
    EXALTED = "exalted"
    OWN_SIGN = "own_sign"
    NEUTRAL = "neutral"
    DEBILITATED = "debilitated"


class _Planet(_M):
    body: _Body
    sign: _Sign
    house: int
    dignity: _Dignity | None
    retrograde: bool


class _Snapshot(_M):
    zodiac: str = "sidereal"
    ayanamsa: str = "lahiri"
    house_system: str = "whole_sign"
    node_convention: str = "mean"
    calculation_engine_version: str = "1"


class _Chart(_M):
    lagna_sign: _Sign
    planets: tuple[_Planet, ...]
    calculation: _Snapshot = _Snapshot()


class _Versions(_M):
    ruleset_id: str = "PANDIT_JI_VEDIC"
    ruleset_version: str = "1.0.0"
    ruleset_content_hash: str = RULESET_HASH


class _Prov(_M):
    source: str
    source_id: str
    source_location: str


class _Reading(_M):
    unresolved_dependencies: tuple[str, ...] = ()


class _Tags(_M):
    domain: tuple[str, ...] = ()
    signification: tuple[str, ...] = ()
    effect_class: str = "supportive"


class _Result(_M):
    rule_id: str
    rule_version: str = "1"
    profile: str
    status: str
    provenance: _Prov
    readings: tuple[_Reading, ...] = (_Reading(),)
    interpretation_tags: _Tags | None = None


class _Group(_M):
    group_id: str
    rule_ids: tuple[str, ...]


class AstroBundle(_M):
    """The structure of the Phase 6 ``EvidenceBundle`` that the verifier reads."""

    bundle_version: str = "1"
    versions: _Versions = _Versions()
    chart: _Chart
    results: tuple[_Result, ...]
    conflicts: tuple[_Group, ...] = ()
    bundle_hash: str = ""


def _seal(bundle: AstroBundle) -> AstroBundle:
    body = bundle.model_dump(mode="json", exclude={"bundle_hash"})
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return bundle.model_copy(update={"bundle_hash": hashlib.sha256(text.encode()).hexdigest()})


def make_astro_bundle(*, ruleset_hash: str = RULESET_HASH, mars_sign: str = "aries") -> AstroBundle:
    bphs = _Prov(
        source="Brihat Parasara Hora Sastra",
        source_id="BPHS_KAPOOR_1987",
        source_location="ch. 75",
    )
    other = _Prov(
        source="Phaladeepika", source_id="PHALADEEPIKA_SUBRAMANIA_1992", source_location="ch. 6"
    )
    results = (
        _Result(
            rule_id="ASTRO_RAJA",
            profile="BPHS",
            status="TRIGGERED",
            provenance=bphs,
            interpretation_tags=_Tags(
                domain=("career", "status"),
                signification=("yoga.raja_yoga",),
                effect_class="supportive",
            ),
        ),
        _Result(
            rule_id="ASTRO_DOSHA",
            profile="BPHS",
            status="TRIGGERED",
            provenance=bphs,
            interpretation_tags=_Tags(
                domain=("marriage",),
                signification=("dosha.kuja",),
                effect_class="challenging",
            ),
        ),
        _Result(
            rule_id="ASTRO_MIXED",
            profile="BPHS",
            status="TRIGGERED",
            provenance=bphs,
            interpretation_tags=_Tags(
                domain=("general",),
                signification=("yoga.sunapha",),
                effect_class="context_dependent",
            ),
        ),
        _Result(rule_id="ASTRO_NOTTRIG", profile="BPHS", status="NOT_TRIGGERED", provenance=bphs),
        _Result(rule_id="ASTRO_NE", profile="BPHS", status="NOT_EVALUABLE", provenance=bphs),
        _Result(rule_id="ASTRO_CANCELLED", profile="BPHS", status="CANCELLED", provenance=bphs),
        _Result(
            rule_id="ASTRO_PHAL",
            profile="PHAL",
            status="TRIGGERED",
            provenance=other,
            interpretation_tags=_Tags(
                domain=("career",), signification=("yoga.raja_yoga",), effect_class="supportive"
            ),
        ),
        _Result(
            rule_id="ASTRO_DEPS",
            profile="BPHS",
            status="TRIGGERED",
            provenance=bphs,
            readings=(_Reading(unresolved_dependencies=("dasha",)),),
            interpretation_tags=_Tags(
                domain=("wealth",), signification=("dhana.yoga",), effect_class="supportive"
            ),
        ),
    )
    bundle = AstroBundle(
        versions=_Versions(ruleset_content_hash=ruleset_hash),
        chart=_Chart(
            lagna_sign=_Sign.CANCER,
            planets=(
                _Planet(
                    body=_Body.MARS,
                    sign=_Sign(mars_sign),
                    house=1,
                    dignity=_Dignity.OWN_SIGN,
                    retrograde=False,
                ),
                _Planet(
                    body=_Body.VENUS,
                    sign=_Sign.LIBRA,
                    house=7,
                    dignity=_Dignity.NEUTRAL,
                    retrograde=False,
                ),
                _Planet(
                    body=_Body.SATURN,
                    sign=_Sign.CAPRICORN,
                    house=10,
                    dignity=_Dignity.OWN_SIGN,
                    retrograde=True,
                ),
            ),
        ),
        results=results,
        conflicts=(
            _Group(group_id="CROSS_SOURCE_RAJA", rule_ids=("ASTRO_RAJA", "ASTRO_PHAL")),
            _Group(group_id="SINGLE_AMBIGUITY", rule_ids=("ASTRO_MIXED",)),
        ),
    )
    return _seal(bundle)


# -- claims and responses ----------------------------------------------------------------------


@dataclass
class World:
    palm: PalmWorld
    astro: AstroBundle
    evidence: TrustedEvidence

    @property
    def palm_ref(self) -> str:
        return self.palm.bundle.bundle_hash

    @property
    def astro_ref(self) -> str:
        return str(self.astro.bundle_hash)

    def item(self, evidence_id: str) -> EvidenceItem:
        for bundle in self.evidence.bundles.values():
            if evidence_id in bundle.items:
                return bundle.items[evidence_id]
        raise KeyError(evidence_id)

    def verifier(self, config: VerifierConfig | None = None, **kw: Any) -> Verifier:
        return Verifier(self.evidence, config, **kw)


def make_world() -> World:
    palm = make_palm_world()
    astro = make_astro_bundle()
    evidence = TrustedEvidence().add_palm(palm.bundle).add_astrology(astro)
    return World(palm=palm, astro=astro, evidence=evidence)


def make_claim(
    world: World,
    claim_id: str,
    text: str,
    claim_type: ClaimType,
    evidence_ids: list[str],
    *,
    domain: Domain | None = None,
    **overrides: Any,
) -> NarrationClaim:
    """A claim whose copied provenance is exactly what a correct Phase 15 would have written."""
    items = [world.item(i) for i in evidence_ids]
    dom = domain or (items[0].domain if items else Domain.ASTROLOGY)
    confidences = [i.confidence_bp for i in items if i.confidence_bp is not None]
    fields: dict[str, Any] = {
        "claim_id": claim_id,
        "text": text,
        "claim_type": claim_type,
        "domain": dom,
        "references": tuple(
            EvidenceReference(
                evidence_id=i.evidence_id,
                domain=i.domain,
                kind=i.reference_kind,
                bundle_ref=i.bundle_ref,
            )
            for i in items
        ),
        "source_profiles": tuple(sorted({i.source_profile for i in items if i.source_profile})),
        "source_locations": tuple(sorted({i.source_location for i in items if i.source_location})),
        "version_refs": tuple(sorted({i.version_ref for i in items if i.version_ref})),
        "min_confidence_bp": min(confidences) if confidences else None,
        "uncertainty": (),
    }
    fields.update(overrides)
    return NarrationClaim(**fields)


def make_response(
    *claims: NarrationClaim, status: AgentStatus = AgentStatus.COMPLETED
) -> NarrationResponse:
    return NarrationResponse(
        request_id="req-1",
        language=LLMLanguage.EN,
        status=status,
        sections=(NarrationSection(heading="Reading", claims=tuple(claims)),) if claims else (),
        trace=AgentTrace(agent_version="0.3.0"),
    )


def flags(*names: str) -> tuple[UncertaintyFlag, ...]:
    return tuple(UncertaintyFlag(n) for n in names)
