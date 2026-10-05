"""Phase 16 over Phases 6, 13, 14 and 15: real bundles, the real agent, the real verifier.

Palmistry: image -> quality -> hand -> facts -> palm rules -> PalmEvidenceBundle -> agent -> verifier.
Astrology: the real Phase 6 Vedic ruleset on a chart -> EvidenceBundle -> agent -> verifier.
The model behind the agent is the Phase 14 service over the scripted test runtime: a test double.
Nothing here says anything about real model quality, and a VERIFIED result means only that a claim
is supported by the application's encoded evidence and rule model.
"""

from __future__ import annotations

import ast
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
from pandit_agent.orchestration import policy as agent_policy
from pandit_contracts.agent import (
    AgentRequest,
    Domain,
    NarrationResponse,
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
from pandit_contracts.verification import (
    OverallStatus,
    ReleaseAction,
    VerificationStatus,
)
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
from pandit_verification import (
    TrustedEvidence,
    Verifier,
    VerifierConfig,
    verify_narration,
)
from pandit_verification import policy as verification_policy

S = VerificationStatus
REPO = Path(__file__).resolve().parents[2]
PALM_RULES = REPO / "services" / "rule-engine" / "palm_rules"
VEDIC_RULES = REPO / "services" / "knowledge" / "rules"
PHASE6_HASH = "8d29a18ccd5e57c5d5ec7c70854a9e45997226f5540eb2d3c1a0bc6099b77209"
PALM_KV = "KV-a21c2c040abe9663"


def _load_chart_builder() -> Any:
    path = REPO / "services" / "rule-engine" / "tests" / "chart_builder.py"
    spec = importlib.util.spec_from_file_location("pj_rule_chart_builder_p16", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def palm_inputs() -> tuple[PalmEvidenceBundle, Any, Any]:
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
    bundle = build_palm_evidence_bundle(
        fact_set=outcome.fact_set,
        rule_evaluations=list(
            evaluate_palm_rules(ruleset, outcome.fact_set, built.version_id)
        ),
        knowledge_version=built.version_id,
    )
    return bundle, ruleset, built.version_id


@pytest.fixture(scope="module")
def palm_bundle(palm_inputs: tuple[PalmEvidenceBundle, Any, Any]) -> PalmEvidenceBundle:
    return palm_inputs[0]


@pytest.fixture(scope="module")
def astro_engine_and_facts() -> tuple[Any, Any]:
    builder = _load_chart_builder()
    engine = RuleEngine.from_directory(VEDIC_RULES)
    facts = builder.chart("aries", builder.full_placements(jupiter="leo", sun="aries"))
    return engine, facts


@pytest.fixture(scope="module")
def astro_bundle(astro_engine_and_facts: tuple[Any, Any]) -> Any:
    engine, facts = astro_engine_and_facts
    return engine.evaluate(facts)


def _agent(script: list[str], *tools: Any) -> AgentOrchestrator:
    runtime = MockRuntime(script)
    settings = LLMSettings(
        manifest_name="mock-deterministic-test.json", allow_test_fixture=True
    )
    service: LLMService = create_service(
        settings, runtime, schemas=narration_schema_registry()
    )
    service.start()
    return AgentOrchestrator(
        service, ToolRegistry(tools), config=AgentConfig(max_evidence_items=40)
    )


def _req(text: str, domain: Domain) -> AgentRequest:
    return AgentRequest(
        request_id="p16-1", language=LLMLanguage.EN, user_text=text, domain=domain
    )


def _script(*claims: dict[str, Any]) -> str:
    return json.dumps({"sections": [{"heading": "Reading", "claims": list(claims)}]})


def _claim(text: str, ctype: str, ids: list[str]) -> dict[str, Any]:
    return {"text": text, "claim_type": ctype, "evidence_ids": ids}


def _trusted(palm: PalmEvidenceBundle, astro: Any) -> TrustedEvidence:
    return TrustedEvidence().add_palm(palm).add_astrology(astro)


# -- palmistry: the real bundle ------------------------------------------------------------------


def test_real_palm_claims_through_the_real_agent_are_verified_or_honestly_not(
    palm_bundle: PalmEvidenceBundle, astro_bundle: Any
) -> None:
    hand = next(
        f
        for f in palm_bundle.fact_set.facts
        if f.fact_class is FactClass.OBSERVED and f.fact_type.value == "HAND_SIDE"
    )
    benham = next(
        r
        for r in palm_bundle.rule_evaluations
        if r.rule_id.startswith("PALMR_BE_RIGHT")
    )
    agent = _agent(
        [
            _script(
                _claim(
                    "The right hand was observed.", "OBSERVED_FEATURE", [hand.fact_id]
                ),
                _claim(
                    "According to Benham, the right hand shows how the map has been altered.",
                    "TRADITIONAL_INTERPRETATION",
                    [benham.rule_id],
                ),
                _claim(
                    "One tradition reads the right hand as showing how the map has been altered.",
                    "TRADITIONAL_INTERPRETATION",
                    [benham.rule_id],
                ),
            )
        ],
        PalmBundleTool(palm_bundle),
    )
    narration = agent.run(_req("What does my hand show?", Domain.PALMISTRY))
    # Phase 15 ends UNVERIFIED and never names a verifier
    assert all(c.verification is VerificationState.UNVERIFIED for c in narration.claims)
    assert all(c.verified_by is None for c in narration.claims)
    assert (
        narration.verification is VerificationState.UNVERIFIED
        and narration.verified_by is None
    )

    report = Verifier(_trusted(palm_bundle, astro_bundle)).verify(narration)
    by_id = {c.claim_id: c for c in report.claims}
    non_limitation = [c for c in narration.claims if c.claim_type.value != "LIMITATION"]
    statuses = [by_id[c.claim_id].status for c in non_limitation]
    assert statuses[:2] == [S.VERIFIED, S.VERIFIED], [
        (r.code.value, r.detail) for c in report.claims for r in c.reasons
    ]
    # the conflicted source is cited without being named: Phase 15 allowed it, Phase 16 does not
    assert statuses[2] is S.CONFLICTING_EVIDENCE
    assert report.trace.bundle_refs == (palm_bundle.bundle_hash,)
    assert report.trace.version_refs == (PALM_KV,)
    assert (
        report.release_action is ReleaseAction.REGENERATE
    )  # a conflicting claim is present
    # drop the offending claim and the rest is released with VERIFIED set by the verifier
    narration_ok = narration.model_copy(
        update={
            "sections": tuple(
                s.model_copy(
                    update={
                        "claims": tuple(
                            c
                            for c in s.claims
                            if by_id[c.claim_id].status is not S.CONFLICTING_EVIDENCE
                        )
                    }
                )
                for s in narration.sections
            )
        }
    )
    outcome = verify_narration(
        narration_ok, Verifier(_trusted(palm_bundle, astro_bundle))
    )
    assert outcome.response is not None
    released = [
        c
        for c in outcome.response.claims
        if c.verification is VerificationState.VERIFIED
    ]
    assert len(released) == 2 and all(c.verified_by for c in released)


def test_a_not_evaluable_real_palm_rule_is_insufficient_evidence(
    palm_bundle: PalmEvidenceBundle, astro_bundle: Any
) -> None:
    rule = next(
        r for r in palm_bundle.rule_evaluations if r.status is RuleStatus.NOT_EVALUABLE
    )
    agent = _agent(
        [
            _script(
                _claim(
                    "This rule could not be evaluated.", "LIMITATION", [rule.rule_id]
                )
            )
        ],
        PalmBundleTool(palm_bundle),
    )
    narration = agent.run(_req("What does my hand show?", Domain.PALMISTRY))
    report = Verifier(_trusted(palm_bundle, astro_bundle)).verify(narration)
    stated = report.claims[0]
    assert (
        stated.status is S.VERIFIED
    )  # the limitation is true: the rule is not evaluable
    # the same rule used for an interpretation is not supported (Phase 15 would have refused it;
    # a forged narration that reaches the verifier is judged on the evidence)
    forged = narration.model_copy(
        update={
            "sections": (
                narration.sections[0].model_copy(
                    update={
                        "claims": (
                            narration.claims[0].model_copy(
                                update={
                                    "claim_type": narration.claims[
                                        0
                                    ].claim_type.__class__(
                                        "TRADITIONAL_INTERPRETATION"
                                    ),
                                    "text": "One tradition reads this as significant.",
                                }
                            ),
                        )
                    }
                ),
            )
        }
    )
    again = Verifier(_trusted(palm_bundle, astro_bundle)).verify(forged)
    assert again.claims[0].status is S.INSUFFICIENT_EVIDENCE


def test_the_real_palm_rules_are_reproduced_by_independent_recomputation(
    palm_inputs: tuple[PalmEvidenceBundle, Any, Any], astro_bundle: Any
) -> None:
    bundle, ruleset, _kv = palm_inputs
    evidence = TrustedEvidence().add_palm(
        bundle,
        recompute=lambda fact_set, version: evaluate_palm_rules(
            ruleset, fact_set, version
        ),
    )
    trusted = evidence.bundle(bundle.bundle_hash)
    assert trusted is not None and trusted.ok
    wrong = TrustedEvidence().add_palm(
        bundle,
        recompute=lambda fact_set, version: evaluate_palm_rules(
            ruleset, fact_set, "KV-x"
        ),
    )
    assert not wrong.bundle(bundle.bundle_hash).ok  # type: ignore[union-attr]


def test_palm_knowledge_version_is_the_locked_one(
    palm_bundle: PalmEvidenceBundle,
) -> None:
    assert palm_bundle.knowledge_version == PALM_KV
    config = VerifierConfig(expected_knowledge_versions=frozenset({PALM_KV}))
    assert config.expected_knowledge_versions == frozenset({PALM_KV})


# -- astrology: the real Phase 6 bundle ----------------------------------------------------------


def test_the_phase_6_ruleset_hash_is_unchanged_by_phase_16(astro_bundle: Any) -> None:
    assert astro_bundle.versions.ruleset_content_hash == PHASE6_HASH


def test_the_real_astrology_bundle_hash_is_reproduced_by_the_verifier(
    astro_bundle: Any, astro_engine_and_facts: tuple[Any, Any]
) -> None:
    engine, facts = astro_engine_and_facts
    evidence = TrustedEvidence().add_astrology(
        astro_bundle, recompute=lambda: engine.evaluate(facts)
    )
    trusted = evidence.bundle(astro_bundle.bundle_hash)
    assert trusted is not None and trusted.ok, trusted.problems if trusted else None
    assert trusted.ruleset_hash == PHASE6_HASH


def test_real_astrology_claims_through_the_real_agent(
    palm_bundle: PalmEvidenceBundle, astro_bundle: Any
) -> None:
    triggered = next(r for r in astro_bundle.results if r.status.value == "TRIGGERED")
    agent = _agent(
        [
            _script(
                _claim(
                    "Jupiter is placed in Leo.",
                    "CALCULATION_FACT",
                    ["astro.planet.jupiter"],
                ),
                _claim(
                    "Sun is placed in Aries and is exalted.",
                    "CALCULATION_FACT",
                    ["astro.planet.sun"],
                ),
                _claim(
                    "Jupiter is placed in Pisces.",
                    "CALCULATION_FACT",
                    ["astro.planet.jupiter"],
                ),
                _claim(
                    "This rule is traditionally read as significant.",
                    "TRADITIONAL_INTERPRETATION",
                    [str(triggered.rule_id)],
                ),
            )
        ],
        AstrologyBundleTool(astro_bundle),
    )
    narration = agent.run(_req("Tell me about my chart.", Domain.ASTROLOGY))
    evidence = _trusted(palm_bundle, astro_bundle)
    config = VerifierConfig(expected_ruleset_hashes=frozenset({PHASE6_HASH}))
    report = Verifier(evidence, config).verify(narration)
    facts = [
        c
        for c in report.claims
        if c.claim_type is not None and c.claim_type.value == "CALCULATION_FACT"
    ]
    assert [c.status for c in facts] == [S.VERIFIED, S.VERIFIED, S.CONFLICTING_EVIDENCE]
    assert all(c.provenance.bundle_refs == (astro_bundle.bundle_hash,) for c in facts)
    interpretation = next(c for c in report.claims if c.rule_refs)
    assert (
        interpretation.status is not S.VERIFIED
        or interpretation.provenance.ruleset_hashes == (PHASE6_HASH,)
    )
    assert report.trace.ruleset_hashes == (PHASE6_HASH,)
    assert report.overall_status in {
        OverallStatus.PARTIALLY_VERIFIED,
        OverallStatus.NONE_VERIFIED,
    }


def test_a_wrong_ruleset_pin_makes_the_real_bundle_invalid(
    palm_bundle: PalmEvidenceBundle, astro_bundle: Any
) -> None:
    agent = _agent(
        [
            _script(
                _claim(
                    "Jupiter is placed in Leo.",
                    "CALCULATION_FACT",
                    ["astro.planet.jupiter"],
                )
            )
        ],
        AstrologyBundleTool(astro_bundle),
    )
    narration = agent.run(_req("Tell me about my chart.", Domain.ASTROLOGY))
    config = VerifierConfig(expected_ruleset_hashes=frozenset({"0" * 64}))
    report = Verifier(_trusted(palm_bundle, astro_bundle), config).verify(narration)
    assert report.claims[0].status is S.INVALID_REFERENCE


# -- boundaries ----------------------------------------------------------------------------------


def test_the_hindi_supplement_is_identical_in_the_agent_and_the_verifier() -> None:
    assert verification_policy.SUPPLEMENT == agent_policy._SUPPLEMENT
    assert (
        verification_policy.PALM_RESTRICTED
        == agent_policy.PALM_POLICY.output_restrictions
    )
    assert (
        verification_policy.ASTROLOGY_RESTRICTED
        == agent_policy.ASTROLOGY_POLICY.output_restrictions
    )


def test_the_verifier_does_not_import_the_agent_or_a_model() -> None:
    src = REPO / "services" / "verification" / "src" / "pandit_verification"
    forbidden = {
        "pandit_agent",
        "openai",
        "anthropic",
        "google",
        "httpx",
        "requests",
        "socket",
    }
    for path in src.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert name.split(".")[0] not in forbidden, (path.name, name)


def test_the_agent_package_still_never_sets_verified() -> None:
    agent_src = REPO / "services" / "agent" / "src" / "pandit_agent" / "orchestration"
    for path in agent_src.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "VerificationState.VERIFIED" not in text, path.name
        assert "verified_by=" not in text, path.name


def test_narration_response_equality_survives_verification(
    palm_bundle: PalmEvidenceBundle, astro_bundle: Any
) -> None:
    """Verification returns new objects; it never edits the narration it was given."""
    agent = _agent(
        [
            _script(
                _claim(
                    "Jupiter is placed in Leo.",
                    "CALCULATION_FACT",
                    ["astro.planet.jupiter"],
                )
            )
        ],
        AstrologyBundleTool(astro_bundle),
    )
    narration: NarrationResponse = agent.run(
        _req("Tell me about my chart.", Domain.ASTROLOGY)
    )
    before = narration.model_dump_json()
    outcome = verify_narration(narration, Verifier(_trusted(palm_bundle, astro_bundle)))
    assert narration.model_dump_json() == before
    assert outcome.response is not None
    assert outcome.response.claims[0].verification is VerificationState.VERIFIED
