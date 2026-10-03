"""Phase 15 over Phases 6, 13 and 14: real bundles in, grounded narration out.

Palmistry: image -> quality -> hand -> facts -> palm rules -> PalmEvidenceBundle -> agent.
Astrology: the real Phase 6 Vedic ruleset evaluated on a chart -> EvidenceBundle -> agent.
The model behind the agent is the Phase 14 service over the scripted test runtime: a test double.
Nothing here says anything about real model quality.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from pandit_agent.llm.mock_runtime import MockRuntime
from pandit_agent.llm.service import LLMService, create_service
from pandit_agent.llm.settings import LLMSettings
from pandit_agent.orchestration import (
    AgentConfig,
    AgentOrchestrator,
    AstrologyBundleTool,
    PalmBundleTool,
    ToolRegistry,
    narration_schema_registry,
)
from pandit_contracts.agent import (
    AgentErrorCode,
    AgentRequest,
    AgentStatus,
    ClaimType,
    Domain,
    EvidenceClass,
    Intent,
    UncertaintyFlag,
    VerificationState,
)
from pandit_contracts.llm import LLMLanguage
from pandit_contracts.palm import (
    FactClass,
    HandSide,
    PalmEvidenceBundle,
    RuleStatus,
    build_palm_evidence_bundle,
)
from pandit_contracts.palm_coverage import PalmSourceCoverage
from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import KnowledgeBuilder
from pandit_knowledge.palm_content import load_palm_content
from pandit_knowledge.store import InMemoryKnowledgeStore
from pandit_palm_vision.hand import StaticHandDetector
from pandit_palm_vision.image_input import CaptureContext
from pandit_palm_vision.pipeline import PalmPipeline
from pandit_palm_vision.quality import fixture_quality_config
from pandit_palm_vision.synthetic import make_synthetic_palm
from pandit_rule_engine.engine import RuleEngine
from pandit_rule_engine.palm import evaluate_palm_rules, load_palm_ruleset

REPO = Path(__file__).resolve().parents[2]
PALM_RULES = REPO / "services" / "rule-engine" / "palm_rules"
VEDIC_RULES = REPO / "services" / "knowledge" / "rules"
PHASE6_HASH = "8d29a18ccd5e57c5d5ec7c70854a9e45997226f5540eb2d3c1a0bc6099b77209"
MOCK = "pandit-mock-deterministic"


def _load_chart_builder() -> Any:
    path = REPO / "services" / "rule-engine" / "tests" / "chart_builder.py"
    spec = importlib.util.spec_from_file_location("pj_rule_chart_builder", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def palm_bundle() -> PalmEvidenceBundle:
    palm = load_palm_content()
    built = KnowledgeBuilder(
        InMemoryKnowledgeStore(), HashingEmbeddingProvider(), "1.28.0"
    ).build(palm.knowledge)
    coverage: PalmSourceCoverage = palm.coverage
    sample = make_synthetic_palm(HandSide.RIGHT, seed=3)
    pipeline = PalmPipeline(
        StaticHandDetector((sample.candidate(False),), False),
        quality_config=fixture_quality_config(),
    )
    outcome = pipeline.run(
        sample.image, CaptureContext(mirrored=False, palm_facing=True)
    )
    ruleset = load_palm_ruleset(PALM_RULES, coverage)
    return build_palm_evidence_bundle(
        fact_set=outcome.fact_set,
        rule_evaluations=list(
            evaluate_palm_rules(ruleset, outcome.fact_set, built.version_id)
        ),
        knowledge_version=built.version_id,
    )


@pytest.fixture(scope="module")
def astro_bundle() -> Any:
    builder = _load_chart_builder()
    engine = RuleEngine.from_directory(VEDIC_RULES)
    facts = builder.chart("aries", builder.full_placements(jupiter="leo", sun="aries"))
    return engine.evaluate(facts)


def _agent(script: list[str], *tools: Any) -> tuple[AgentOrchestrator, MockRuntime]:
    runtime = MockRuntime(script)
    settings = LLMSettings(
        manifest_name="mock-deterministic-test.json", allow_test_fixture=True
    )
    service: LLMService = create_service(
        settings, runtime, schemas=narration_schema_registry()
    )
    service.start()
    # The scripted test model has a 4096-token window (the real manifest allows 32768), so the
    # evidence budget is small here: the priority trimming path runs on every real bundle.
    config = AgentConfig(max_evidence_items=16)
    return AgentOrchestrator(service, ToolRegistry(tools), config=config), runtime


def _req(text: str, domain: Domain, **kw: Any) -> AgentRequest:
    return AgentRequest(
        request_id=kw.pop("request_id", "p15-1"),
        language=kw.pop("language", LLMLanguage.EN),
        user_text=text,
        domain=domain,
        **kw,
    )


def _claim(text: str, ctype: str, ids: list[str]) -> dict[str, Any]:
    return {"text": text, "claim_type": ctype, "evidence_ids": ids}


def _script(*claims: dict[str, Any]) -> str:
    return json.dumps({"sections": [{"heading": "Reading", "claims": list(claims)}]})


# -- palmistry ---------------------------------------------------------------------------------


def test_the_real_palm_bundle_flows_into_a_grounded_unverified_narration(
    palm_bundle: PalmEvidenceBundle,
) -> None:
    observed = next(
        f for f in palm_bundle.fact_set.facts if f.fact_class is FactClass.OBSERVED
    )
    triggered = next(
        r for r in palm_bundle.rule_evaluations if r.status is RuleStatus.TRIGGERED
    )
    agent, runtime = _agent(
        [
            _script(
                _claim(
                    "A feature was observed.", "OBSERVED_FEATURE", [observed.fact_id]
                ),
                _claim(
                    "One named tradition reads this as a traditional indication.",
                    "TRADITIONAL_INTERPRETATION",
                    [triggered.rule_id],
                ),
            )
        ],
        PalmBundleTool(palm_bundle),
    )
    response = agent.run(_req("What does my hand show?", Domain.PALMISTRY))
    # the real bundle exceeds the small budget: the trim is recorded and the status is DEGRADED
    assert response.status is AgentStatus.DEGRADED and response.error is None
    assert any(c.claim_type is ClaimType.LIMITATION for c in response.claims)
    assert UncertaintyFlag.EVIDENCE_TRIMMED in response.claims[0].uncertainty
    interpretation = response.claims[1]
    assert interpretation.claim_type is ClaimType.TRADITIONAL_INTERPRETATION
    assert interpretation.source_profiles == (triggered.source_profile,)
    assert interpretation.source_locations == (triggered.source_location,)
    assert interpretation.version_refs == (triggered.knowledge_version,)
    assert [r.evidence_id for r in interpretation.references] == [triggered.rule_id]
    assert all(
        r.bundle_ref == palm_bundle.bundle_hash
        for c in response.claims
        for r in c.references
    )
    assert all(c.verification is VerificationState.UNVERIFIED for c in response.claims)
    assert response.trace.bundle_refs == (palm_bundle.bundle_hash,)
    assert response.trace.version_refs == (palm_bundle.knowledge_version,)
    assert UncertaintyFlag.BUNDLE_NOT_PRODUCTION_READY in response.claims[0].uncertainty
    assert "EVIDENCE_NOT_PRODUCTION_READY" in [
        d.code.value for d in response.disclaimers
    ]
    assert runtime.calls and len(runtime.calls) == 1


def test_semantic_classes_survive_the_adapter_and_the_prompt(
    palm_bundle: PalmEvidenceBundle,
) -> None:
    tool = PalmBundleTool(palm_bundle)
    from pandit_contracts.agent import EvidenceCapability as C

    records = tool.invoke(frozenset({C.PALM_FACTS, C.PALM_RULES})).records
    by_id = {r.evidence_id: r for r in records}
    for fact in palm_bundle.fact_set.facts:
        expected = (
            EvidenceClass.OBSERVED_FACT
            if fact.fact_class is FactClass.OBSERVED
            else EvidenceClass.DERIVED_FACT
        )
        record = by_id[fact.fact_id]
        assert record.evidence_class is expected
        assert record.confidence_bp == fact.confidence.score_bp
        assert record.confidence_calibrated == fact.confidence.calibrated
        assert record.status == fact.visibility.state.value
    for rule in palm_bundle.rule_evaluations:
        record = by_id[rule.rule_id]
        assert record.evidence_class is EvidenceClass.RULE_EVALUATION
        assert record.status == rule.status.value
        assert record.source_profile == rule.source_profile
        assert record.version_ref == rule.knowledge_version
    assert not any(r.domain is not Domain.PALMISTRY for r in records)


def test_no_pixels_geometry_or_image_identity_reach_the_model(
    palm_bundle: PalmEvidenceBundle,
) -> None:
    observed = next(
        f for f in palm_bundle.fact_set.facts if f.fact_class is FactClass.OBSERVED
    )
    agent, runtime = _agent(
        [_script(_claim("x", "OBSERVED_FEATURE", [observed.fact_id]))],
        PalmBundleTool(palm_bundle),
    )
    agent.run(_req("What does my hand show?", Domain.PALMISTRY))
    prompt = runtime.calls[0].prompt
    assert palm_bundle.image_ref.image_id not in prompt
    assert palm_bundle.image_ref.content_sha256 not in prompt
    assert "PCF-1" not in prompt and "coords" not in prompt
    # geometry is a structural property of the contract, not just filtered text
    from pandit_contracts.agent import EvidenceRecord

    assert (
        "geometry" not in EvidenceRecord.model_fields
        and "image_ref" not in EvidenceRecord.model_fields
    )


def test_a_not_evaluable_palm_rule_cannot_back_an_interpretation(
    palm_bundle: PalmEvidenceBundle,
) -> None:
    not_evaluable = next(
        r for r in palm_bundle.rule_evaluations if r.status is RuleStatus.NOT_EVALUABLE
    )
    forced = _script(
        _claim(
            "A confident reading.",
            "TRADITIONAL_INTERPRETATION",
            [not_evaluable.rule_id],
        )
    )
    agent, _ = _agent([forced], PalmBundleTool(palm_bundle))
    response = agent.run(_req("What does my hand show?", Domain.PALMISTRY))
    assert response.status is AgentStatus.FAILED
    assert response.error is not None
    assert response.error.code is AgentErrorCode.NARRATION_GROUNDING_FAILURE
    # the same rule can be stated honestly as a limitation, with the uncertainty carried
    honest = _script(
        _claim(
            "This rule could not be evaluated.", "LIMITATION", [not_evaluable.rule_id]
        )
    )
    agent2, _ = _agent([honest], PalmBundleTool(palm_bundle))
    ok = agent2.run(_req("What does my hand show?", Domain.PALMISTRY))
    assert UncertaintyFlag.NOT_EVALUABLE in ok.claims[0].uncertainty


def test_the_agent_cannot_change_the_bundle(palm_bundle: PalmEvidenceBundle) -> None:
    before, digest = palm_bundle.model_dump_json(), palm_bundle.bundle_hash
    observed = next(
        f for f in palm_bundle.fact_set.facts if f.fact_class is FactClass.OBSERVED
    )
    agent, _ = _agent(
        [_script(_claim("x", "OBSERVED_FEATURE", [observed.fact_id]))],
        PalmBundleTool(palm_bundle),
    )
    agent.run(_req("What does my hand show?", Domain.PALMISTRY))
    assert palm_bundle.model_dump_json() == before and palm_bundle.bundle_hash == digest


def test_prohibited_palm_requests_are_refused_with_the_real_tools(
    palm_bundle: PalmEvidenceBundle,
) -> None:
    agent, runtime = _agent([], PalmBundleTool(palm_bundle))
    for text in (
        "Does my palm show a disease?",
        "How long is my lifespan from my hand?",
    ):
        response = agent.run(_req(text, Domain.PALMISTRY))
        assert response.status is AgentStatus.REFUSED
    assert runtime.calls == []


# -- astrology ---------------------------------------------------------------------------------


def test_the_phase_6_ruleset_hash_is_unchanged_by_phase_15(astro_bundle: Any) -> None:
    assert astro_bundle.versions.ruleset_content_hash == PHASE6_HASH


def test_the_real_astrology_bundle_flows_into_a_grounded_narration(
    astro_bundle: Any,
) -> None:
    triggered = next(r for r in astro_bundle.results if r.status.value == "TRIGGERED")
    agent, runtime = _agent(
        [
            _script(
                _claim(
                    "Jupiter is placed in Leo.",
                    "CALCULATION_FACT",
                    ["astro.planet.jupiter"],
                ),
                _claim(
                    "A traditional rule is triggered.",
                    "TRADITIONAL_INTERPRETATION",
                    [triggered.rule_id],
                ),
            )
        ],
        AstrologyBundleTool(astro_bundle),
    )
    response = agent.run(
        _req("Describe my chart", Domain.ASTROLOGY, intent_hint=Intent.GENERAL)
    )
    assert response.status in {AgentStatus.COMPLETED, AgentStatus.DEGRADED}
    first, second = response.claims[0], response.claims[1]
    assert (
        first.claim_type is ClaimType.CALCULATION_FACT
        and first.domain is Domain.ASTROLOGY
    )
    assert second.source_profiles == (triggered.profile,)
    assert second.source_locations == (triggered.provenance.source_location,)
    ruleset_ref = (
        f"{astro_bundle.versions.ruleset_id}@{astro_bundle.versions.ruleset_version}"
    )
    assert second.version_refs == (ruleset_ref,)
    assert response.trace.bundle_refs == (astro_bundle.bundle_hash,)
    system = runtime.calls[0].prompt.split("<|im_end|>")[0]
    # birth date, time and coordinates are never passed to the model
    for secret in (
        "2000-01-01",
        "28.61",
        "77.2",
        "latitude",
        "longitude",
        "utc_datetime",
    ):
        assert secret not in system


def test_the_astrology_adapter_keeps_rules_and_calculated_facts_distinct(
    astro_bundle: Any,
) -> None:
    from pandit_contracts.agent import EvidenceCapability as C

    records = (
        AstrologyBundleTool(astro_bundle)
        .invoke(frozenset({C.ASTRO_CHART, C.ASTRO_RULES}))
        .records
    )
    classes = {r.evidence_class for r in records}
    assert classes == {
        EvidenceClass.CALCULATED_FACT,
        EvidenceClass.RULE_EVALUATION,
        EvidenceClass.CONTEXT_STATUS,
    }
    rule_ids = {r.rule_id for r in astro_bundle.results}
    assert {
        r.evidence_id
        for r in records
        if r.evidence_class is EvidenceClass.RULE_EVALUATION
    } == rule_ids
    assert all(r.domain is Domain.ASTROLOGY for r in records)


def test_a_palmistry_request_never_touches_astrology_evidence_and_vice_versa(
    palm_bundle: PalmEvidenceBundle, astro_bundle: Any
) -> None:
    observed = next(
        f for f in palm_bundle.fact_set.facts if f.fact_class is FactClass.OBSERVED
    )
    agent, runtime = _agent(
        [_script(_claim("x", "OBSERVED_FEATURE", [observed.fact_id]))],
        PalmBundleTool(palm_bundle),
        AstrologyBundleTool(astro_bundle),
    )
    response = agent.run(_req("What does my hand show?", Domain.PALMISTRY))
    system = runtime.calls[0].prompt.split("<|im_end|>")[0]
    assert "astro.planet" not in system and "astro.lagna" not in system
    assert {c.domain for c in response.claims} == {Domain.PALMISTRY}
    assert response.trace.bundle_refs == (palm_bundle.bundle_hash,)


def test_phase_16_receives_a_verification_ready_claim_list(
    palm_bundle: PalmEvidenceBundle,
) -> None:
    observed = next(
        f for f in palm_bundle.fact_set.facts if f.fact_class is FactClass.OBSERVED
    )
    agent, _ = _agent(
        [_script(_claim("x", "OBSERVED_FEATURE", [observed.fact_id]))],
        PalmBundleTool(palm_bundle),
    )
    response = agent.run(_req("What does my hand show?", Domain.PALMISTRY))
    for c in response.claims:
        assert c.claim_id and c.verification is VerificationState.UNVERIFIED
        if (
            c.claim_type is not ClaimType.LIMITATION
        ):  # agent-authored limits cite nothing
            assert c.references
        assert all(r.evidence_id and r.bundle_ref and r.kind for r in c.references)
    assert (
        response.verification is VerificationState.UNVERIFIED
        and response.verified_by is None
    )
