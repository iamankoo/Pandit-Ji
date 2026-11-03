"""Phase 17 over Phases 6, 12, 13, 15 and 16: the life-domain layer end to end.

A real chart -> the real domain ruleset -> ``DomainAnalysisResult`` -> the real Phase 15 agent
(model: the scripted test runtime, a test double) -> the real Phase 16 verifier. The verifier is
not modified: it cannot resolve a domain result by itself, so a composition layer (here the test,
in production Phase 18) registers the result through the verifier's public ``TrustedBundle`` and
``EvidenceItem`` types. An unregistered domain result is never VERIFIED.
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
    ToolRegistry,
    narration_schema_registry,
)
from pandit_agent.orchestration.domain import DomainAnalysisTool
from pandit_contracts.agent import (
    AgentRequest,
    Domain,
    EvidenceClass,
    NarrationResponse,
    VerificationState,
)
from pandit_contracts.domain import (
    DomainAnalysisRequest,
    DomainAnalysisResult,
    DomainStatus,
    LifeDomain,
)
from pandit_contracts.llm import LLMLanguage
from pandit_contracts.verification import VerificationStatus
from pandit_knowledge.domain_content import (
    DOMAIN_KNOWLEDGE_STANDARDS_VERSION,
    load_domain_content,
)
from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import KnowledgeBuilder
from pandit_knowledge.palm_content import (
    PALM_KNOWLEDGE_STANDARDS_VERSION,
    load_palm_content,
)
from pandit_knowledge.store import InMemoryKnowledgeStore
from pandit_rule_engine.domain import (
    evaluate_domain,
    load_domain_ruleset,
    varga_from_kundli,
)
from pandit_rule_engine.loader import load_ruleset
from pandit_verification import TrustedEvidence, Verifier
from pandit_verification.evidence import EvidenceItem, TrustedBundle

S = VerificationStatus
REPO = Path(__file__).resolve().parents[2]
DOMAIN_RULES = REPO / "services" / "rule-engine" / "domain_rules"
VEDIC_RULES = REPO / "services" / "knowledge" / "rules"
PHASE6_HASH = "8d29a18ccd5e57c5d5ec7c70854a9e45997226f5540eb2d3c1a0bc6099b77209"
PHASE12_KV = "KV-06361d7aba28c1ce"
PALM_KV = "KV-a21c2c040abe9663"
MARRIAGE_RULE = "DOM_MARRIAGE_HOUSE_07_P11"
CAREER_RULE = "DOM_CAREER_HOUSE_10_P11"


def _load_chart_builder() -> Any:
    path = REPO / "services" / "rule-engine" / "tests" / "chart_builder.py"
    spec = importlib.util.spec_from_file_location("pj_rule_chart_builder_p17", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def domain_kv() -> str:
    return (
        KnowledgeBuilder(
            InMemoryKnowledgeStore(),
            HashingEmbeddingProvider(),
            DOMAIN_KNOWLEDGE_STANDARDS_VERSION,
        )
        .build(load_domain_content())
        .version_id
    )


@pytest.fixture(scope="module")
def chart() -> tuple[Any, dict[str, Any]]:
    builder = _load_chart_builder()
    placements = builder.full_placements(jupiter="leo", sun="aries")
    facts = builder.chart("aries", placements)
    divisional = {
        n: {b: "taurus" for b in placements} for n in (2, 3, 7, 9, 10, 12, 20, 24)
    }
    kundli = builder.kundli_dict("aries", dict(placements))
    kundli["charts"] = {
        str(n): {
            "varga": n,
            "ascendant_rashi": "aries",
            "planets": [{"body": b, "rashi": s} for b, s in signs.items()],
        }
        for n, signs in divisional.items()
    }
    return facts, kundli


def _analyse(
    domain: LifeDomain,
    chart: tuple[Any, dict[str, Any]],
    kv: str,
    adult: bool | None = True,
) -> DomainAnalysisResult:
    facts, kundli = chart
    ruleset = load_domain_ruleset(DOMAIN_RULES)
    phase6 = (
        None  # the Phase 6 results are optional; their absence is INSUFFICIENT_EVIDENCE
    )
    return evaluate_domain(
        ruleset,
        DomainAnalysisRequest(
            analysis_id="p17-1", domain=domain, subject_adult_confirmed=adult
        ),
        facts,
        knowledge_version=kv,
        varga=varga_from_kundli(kundli),
        phase6_results=phase6,
    )


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
        service, ToolRegistry(tools), config=AgentConfig(max_evidence_items=30)
    )


def _req(text: str) -> AgentRequest:
    return AgentRequest(
        request_id="p17-1",
        language=LLMLanguage.EN,
        user_text=text,
        domain=Domain.ASTROLOGY,
    )


def _script(*claims: dict[str, Any]) -> str:
    return json.dumps({"sections": [{"heading": "Reading", "claims": list(claims)}]})


def _register(result: DomainAnalysisResult) -> TrustedEvidence:
    """The composition step (Phase 18 in production): a result becomes a trusted bundle."""
    ref = result.result_hash
    version_ref = result.versions.ruleset_ref
    bundle = TrustedBundle(
        bundle_ref=ref,
        domain=Domain.ASTROLOGY,
        version_refs=(version_ref,),
        production_ready=None,
        ruleset_hash=result.versions.ruleset_hash,
        knowledge_version=result.versions.knowledge_version,
    )
    for fact in result.facts:
        bundle.items[fact.fact_id] = EvidenceItem(
            evidence_id=fact.fact_id,
            domain=Domain.ASTROLOGY,
            evidence_class=EvidenceClass.CALCULATED_FACT,
            kind=fact.kind.value,
            bundle_ref=ref,
            version_ref=version_ref,
            source_profile=fact.source_profile,
            source_location=fact.source_location,
        )
    for rule in result.rules:
        if rule.status is DomainStatus.POLICY_BLOCKED:
            continue
        bundle.items[rule.rule_id] = EvidenceItem(
            evidence_id=rule.rule_id,
            domain=Domain.ASTROLOGY,
            evidence_class=EvidenceClass.RULE_EVALUATION,
            kind="DOMAIN_RULE",
            bundle_ref=ref,
            status=rule.status.value,
            version_ref=version_ref,
            source_profile=rule.source_profile,
            source_id=rule.source_id,
            source_location=rule.source_location,
            rule_version=rule.rule_version,
            fact_refs=tuple(rule.fact_refs),
            basis_ids=tuple(rule.fact_refs),
            conflict_ids=tuple(rule.conflict_ids),
            tags=rule.interpretation.signification_tags if rule.interpretation else (),
        )
    trusted = TrustedEvidence()
    trusted.bundles[ref] = bundle
    return trusted


# ---- the pipeline --------------------------------------------------------------------------------


def test_a_real_domain_result_flows_through_the_agent_to_the_verifier(
    chart: tuple[Any, dict[str, Any]], domain_kv: str
) -> None:
    result = _analyse(LifeDomain.CAREER, chart, domain_kv)
    assert result.status is DomainStatus.EVALUATED
    assert result.versions.knowledge_version == domain_kv
    claim = {
        "text": "The tenth house of the chart is traditionally relevant to career.",
        "claim_type": "TRADITIONAL_INTERPRETATION",
        "evidence_ids": [CAREER_RULE],
    }
    agent = _agent([_script(claim)], DomainAnalysisTool(result))
    narration = agent.run(_req("Tell me about my career"))
    assert narration.error is None, narration.error
    assert all(c.verification is VerificationState.UNVERIFIED for c in narration.claims)
    assert narration.verified_by is None
    refs = [r for c in narration.claims for r in c.references]
    assert {r.evidence_id for r in refs} >= {CAREER_RULE}
    assert {r.bundle_ref for r in refs} == {result.result_hash}

    report = Verifier(_register(result)).verify(narration)
    by_id = {c.claim_id: c.status for c in report.claims}
    first = narration.claims[0].claim_id
    assert by_id[first] is S.VERIFIED, by_id
    assert report.trace.version_refs == (result.versions.ruleset_ref,)
    assert report.trace.bundle_refs == (result.result_hash,)
    # the gap claims need a trusted record of the gap; recording gaps is composition work (Phase 18)
    assert all(s is S.UNVERIFIABLE for cid, s in by_id.items() if cid != first), by_id


def test_an_unregistered_domain_result_is_never_verified(
    chart: tuple[Any, dict[str, Any]], domain_kv: str
) -> None:
    result = _analyse(LifeDomain.CAREER, chart, domain_kv)
    claim = {
        "text": "The tenth house of the chart is traditionally relevant to career.",
        "claim_type": "TRADITIONAL_INTERPRETATION",
        "evidence_ids": [CAREER_RULE],
    }
    narration = _agent([_script(claim)], DomainAnalysisTool(result)).run(
        _req("Tell me about my career")
    )
    report = Verifier(TrustedEvidence()).verify(narration)
    assert all(c.status is not S.VERIFIED for c in report.claims)
    first = next(c for c in report.claims if c.claim_id == narration.claims[0].claim_id)
    assert first.status is S.UNVERIFIABLE
    assert [r.code.value for r in first.reasons] == ["EVIDENCE_UNAVAILABLE"]


def test_a_forged_domain_rule_reference_is_refused(
    chart: tuple[Any, dict[str, Any]], domain_kv: str
) -> None:
    result = _analyse(LifeDomain.CAREER, chart, domain_kv)
    forged = {
        "text": "A traditional reading.",
        "claim_type": "TRADITIONAL_INTERPRETATION",
        "evidence_ids": ["DOM_CAREER_FORGED"],
    }
    narration = _agent([_script(forged)] * 4, DomainAnalysisTool(result)).run(
        _req("Tell me about my career")
    )
    assert all(
        r.evidence_id != "DOM_CAREER_FORGED"
        for c in narration.claims
        for r in c.references
    )


def test_adult_confirmation_is_the_callers_statement_and_blocks_without_the_model(
    chart: tuple[Any, dict[str, Any]], domain_kv: str
) -> None:
    result = _analyse(LifeDomain.MARRIAGE, chart, domain_kv, adult=None)
    assert result.status is DomainStatus.POLICY_BLOCKED and result.facts == ()
    runtime_agent = _agent([], DomainAnalysisTool(result))
    narration: NarrationResponse = runtime_agent.run(_req("Tell me about my marriage"))
    assert narration.error is not None and narration.claims == ()
    assert narration.status.value == "REFUSED"


def test_not_evaluable_domains_stay_not_evaluable_end_to_end(
    chart: tuple[Any, dict[str, Any]], domain_kv: str
) -> None:
    result = _analyse(LifeDomain.STARTUP, chart, domain_kv)
    assert result.status is DomainStatus.NOT_EVALUABLE
    narration = _agent([], DomainAnalysisTool(result)).run(
        _req("Tell me about my startup")
    )
    assert narration.error is not None
    assert narration.error.code.value == "INSUFFICIENT_EVIDENCE"


def test_the_domain_result_is_deterministic_across_runs(
    chart: tuple[Any, dict[str, Any]], domain_kv: str
) -> None:
    a = _analyse(LifeDomain.WEALTH, chart, domain_kv)
    b = _analyse(LifeDomain.WEALTH, chart, domain_kv)
    assert a == b and a.result_hash == b.result_hash


# ---- repository integrity -------------------------------------------------------------------------


def test_phase_6_phase_12_and_phase_13_artifacts_are_unchanged(domain_kv: str) -> None:
    assert load_ruleset(VEDIC_RULES).content_hash == PHASE6_HASH
    assert len(load_ruleset(VEDIC_RULES).rules) == 51
    from pandit_knowledge.content import load_content

    phase12 = KnowledgeBuilder(
        InMemoryKnowledgeStore(), HashingEmbeddingProvider()
    ).build(load_content())
    palm = KnowledgeBuilder(
        InMemoryKnowledgeStore(),
        HashingEmbeddingProvider(),
        PALM_KNOWLEDGE_STANDARDS_VERSION,
    ).build(load_palm_content().knowledge)
    assert phase12.version_id == PHASE12_KV and palm.version_id == PALM_KV
    assert domain_kv not in {PHASE12_KV, PALM_KV}


def test_phase_17_adds_no_service_and_no_later_phase_code() -> None:
    services = {p.name for p in (REPO / "services").iterdir() if p.is_dir()}
    assert services == {
        "agent",
        "astro-engine",
        "knowledge",
        "palm-vision",
        "rule-engine",
        "verification",
    }
    src = [
        p
        for root in (REPO / "services", REPO / "packages")
        for p in root.rglob("*.py")
        if "tests" not in p.parts
        and ".venv" not in p.parts
        and "site-packages" not in p.parts
    ]
    names = {p.name.lower() for p in src}
    assert not {n for n in names if "vastu" in n or "regenerat" in n or "report" in n}
    text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore").lower() for p in src
    )
    assert "vastu" not in text.replace("vastu is not implemented", "")


# ---- the agent's static presets agree with the domain ruleset -------------------------------------


def test_every_preset_agrees_with_the_domain_ruleset() -> None:
    from pandit_agent.orchestration.domain import PRESETS
    from pandit_contracts.domain import DomainRuleKind
    from pandit_rule_engine.domain.schema import VargaParams

    ruleset = load_domain_ruleset(DOMAIN_RULES)
    for domain, preset in PRESETS.items():
        rules = ruleset.rules_for(domain)
        vargas = {r.params.varga for r in rules if isinstance(r.params, VargaParams)}
        assert set(preset.varga_facts) == vargas, domain
        has_dasha = any(r.kind is DomainRuleKind.MARRIAGE_DASHA_METHOD for r in rules)
        assert preset.dasha == has_dasha, domain
        # no rule reads transit evidence (the bhava transit records are non-evaluating)
        assert preset.transit is False, domain
        assert (
            preset.adult_confirmation_required
            == ruleset.adult_confirmation_required(domain)
        )
        assert set(preset.safety) == set(ruleset.effective_policy(domain)), domain


def test_the_final_phase_17_identifiers_are_pinned(domain_kv: str) -> None:
    ruleset = load_domain_ruleset(DOMAIN_RULES)
    assert domain_kv == "KV-4da4248a7fb5589c"
    assert ruleset.manifest.ruleset_version == "1.0.1"
    assert ruleset.manifest.methodology_version == "DOMAIN_METHODOLOGY_P17_1"
    assert (
        ruleset.content_hash
        == "63d807503249da14f0aa61acc20aedaf08e74a1037da5562bcab55c17177070f"
    )
    assert len(ruleset.rules) == 108


def test_marriage_without_a_dasha_section_carries_the_phase_18_dependency(
    chart: tuple[Any, dict[str, Any]], domain_kv: str
) -> None:
    result = _analyse(LifeDomain.MARRIAGE, chart, domain_kv)
    dasha_rule = next(r for r in result.rules if r.rule_id.endswith("DASHA_7TH_PX13"))
    assert dasha_rule.status is DomainStatus.INSUFFICIENT_EVIDENCE
    assert (
        dasha_rule.reason is not None
        and dasha_rule.reason.value == "PHASE_18_DEPENDENCY"
    )
    transit = [r for r in result.rules if "PXVI31" in r.rule_id]
    assert transit and all(r.status is DomainStatus.NOT_EVALUABLE for r in transit)
    assert all(r.interpretation is None for r in transit)
