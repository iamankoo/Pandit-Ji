"""Phase 17 in the agent: routing, presets, the domain tool, short-circuits and policy screens."""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest
from agent_helpers import astro_tool, claim, make_agent, narration, palm_tool, request
from domain_agent_helpers import DOMAIN_KV, evaluated, refused, rule
from pandit_contracts.agent import (
    AgentErrorCode,
    AgentRequest,
    AgentStatus,
    Domain,
    EvidenceCapability,
    EvidenceClass,
    Intent,
)
from pandit_contracts.domain import (
    DomainAnalysisResult,
    DomainReason,
    DomainStatus,
    DomainSupport,
    LifeDomain,
    PolicyClass,
)
from pandit_contracts.llm import LLMLanguage

from pandit_agent.orchestration.domain import (
    PRESETS,
    DomainAnalysisTool,
    classify_life_domain,
    domain_for_intent,
    preset_for,
    resolve_life_domain,
    screen_domain_claim,
    screen_domain_request,
)
from pandit_agent.orchestration.planner import build_plan
from pandit_agent.orchestration.tools import ToolRegistry

L = LifeDomain
C = EvidenceCapability
GOOD = narration(
    (
        "Reading",
        [
            claim(
                "The tenth house of the chart is traditionally relevant to career.",
                "TRADITIONAL_INTERPRETATION",
                ["DOM_CAREER_HOUSE_10_P11"],
            )
        ],
    )
)


def _run(
    result: DomainAnalysisResult,
    text: str = "Tell me about my career",
    script: list[Any] | None = None,
    **kw: Any,
) -> tuple[Any, Any]:
    agent, runtime, _ = make_agent(
        [GOOD] if script is None else script, tools=[DomainAnalysisTool(result)]
    )
    return agent.run(request(text, domain=Domain.ASTROLOGY, **kw)), runtime


# ---- presets: one per domain, static, deterministic --------------------------------------------


def test_every_one_of_the_36_domains_has_a_static_preset() -> None:
    assert set(PRESETS) == set(LifeDomain) and len(PRESETS) == 36
    for domain, preset in PRESETS.items():
        assert preset.life_domain is domain
        assert preset.required == (C.ASTRO_DOMAIN,)
        assert preset_for(domain) is preset


def test_presets_request_only_the_researched_sections() -> None:
    assert PRESETS[L.MARRIAGE].dasha and not PRESETS[L.CAREER].dasha
    assert [d for d, p in PRESETS.items() if p.dasha] == [L.MARRIAGE]
    for domain, preset in PRESETS.items():
        assert 4 not in preset.varga_facts, domain  # D4 is never a Phase 17 mapping
        assert set(preset.varga_facts) <= {2, 3, 7, 9, 10, 12, 20, 24}


def test_presets_carry_the_safety_metadata() -> None:
    assert PolicyClass.FINANCE_INTERPRETIVE_ONLY in PRESETS[L.FINANCE].safety
    assert PolicyClass.PROFESSIONAL_ADVICE_DISCLAIMER in PRESETS[L.WEALTH].safety
    assert PolicyClass.CHILDREN_STRUCTURAL_ONLY in PRESETS[L.CHILDREN].safety
    assert PolicyClass.FERTILITY_PREDICTION_BLOCKED in PRESETS[L.CHILDREN].safety
    assert PolicyClass.HEALTH_INTERPRETATION_ONLY in PRESETS[L.HEALTH].safety
    assert PolicyClass.MINORS_SENSITIVE in PRESETS[L.CHILDHOOD].safety
    assert PRESETS[L.MARRIAGE].adult_confirmation_required
    assert not PRESETS[L.CAREER].adult_confirmation_required


def test_a_preset_has_no_arbitrary_tool_arguments_and_is_immutable() -> None:
    names = {f.name for f in dataclasses.fields(PRESETS[L.CAREER])}
    assert not names & {"tool", "tools", "tool_name", "url", "path", "sql", "args", "arguments"}
    with pytest.raises(dataclasses.FrozenInstanceError):
        PRESETS[L.CAREER].dasha = True  # type: ignore[misc]


# ---- routing -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "domain"),
    [
        ("how is my career going", L.CAREER),
        ("will my marriage be happy", L.MARRIAGE),
        ("tell me about my wealth", L.WEALTH),
        ("my education prospects", L.EDUCATION),
        ("what about my business", L.BUSINESS),
    ],
)
def test_keyword_routing_is_deterministic(text: str, domain: LifeDomain) -> None:
    assert classify_life_domain(text) is domain
    assert classify_life_domain(text) is classify_life_domain(text)


def test_an_unrelated_text_names_no_domain() -> None:
    assert classify_life_domain("what is the weather like") is None


def test_intents_map_to_exactly_one_domain_each() -> None:
    assert domain_for_intent(Intent.CAREER) is L.CAREER
    assert domain_for_intent(Intent.MARRIAGE) is L.MARRIAGE
    assert domain_for_intent(Intent.LOVE_RELATIONSHIP) is L.RELATIONSHIP
    assert domain_for_intent(Intent.PALM_OVERVIEW) is None


def test_an_explicit_intent_hint_wins_over_the_keywords() -> None:
    got = resolve_life_domain("tell me about my career", Intent.CAREER, intent_hint=Intent.MARRIAGE)
    assert got is L.MARRIAGE
    assert resolve_life_domain("something", Intent.CAREER) is L.CAREER


def test_the_registry_serves_only_the_tool_of_the_requested_domain() -> None:
    registry = ToolRegistry([DomainAnalysisTool(evaluated(L.CAREER))])
    assert registry.tools_for(C.ASTRO_DOMAIN, Domain.ASTROLOGY, L.CAREER)
    assert not registry.tools_for(C.ASTRO_DOMAIN, Domain.ASTROLOGY, L.MARRIAGE)
    assert registry.has_life_domain_tools


# ---- the planner -------------------------------------------------------------------------------


def test_a_domain_plan_is_deterministic_bounded_and_allow_listed() -> None:
    registry = ToolRegistry([DomainAnalysisTool(evaluated(L.CAREER)), astro_tool()])
    a = build_plan(Domain.ASTROLOGY, Intent.CAREER, registry, L.CAREER)
    b = build_plan(Domain.ASTROLOGY, Intent.CAREER, registry, L.CAREER)
    assert a == b and a.plan_hash == b.plan_hash
    assert a.life_domain is L.CAREER
    assert len(a.steps) <= 8
    assert {s.tool_name for s in a.steps if s.tool_name} <= {"domain.career", "astro.static"}


def test_a_plan_without_a_life_domain_is_the_phase_15_plan() -> None:
    plan = build_plan(Domain.ASTROLOGY, Intent.CAREER, ToolRegistry([astro_tool()]))
    assert plan.life_domain is None
    assert not ToolRegistry([astro_tool()]).has_life_domain_tools


# ---- the evidence tool -------------------------------------------------------------------------


def test_the_tool_serves_a_status_record_facts_and_rules_with_provenance() -> None:
    result = evaluated(L.CAREER, transit=True)
    out = DomainAnalysisTool(result).invoke(frozenset({C.ASTRO_DOMAIN, C.ASTRO_TRANSIT}))
    kinds = [r.kind for r in out.records]
    assert kinds[0] == "DOMAIN_STATUS" and "HOUSE_STATE" in kinds and "DOMAIN_RULE" in kinds
    for record in out.records:
        assert record.bundle_ref == result.result_hash
        assert record.version_ref == result.versions.ruleset_ref
        if record.evidence_class is not EvidenceClass.CONTEXT_STATUS:
            assert record.source_profile and record.source_location
    assert out.provided is not None
    assert C.ASTRO_TRANSIT in out.provided and C.ASTRO_DASHA not in out.provided
    assert DOMAIN_KV in out.records[0].text


def test_missing_dasha_or_transit_sections_are_not_reported_as_provided() -> None:
    out = DomainAnalysisTool(evaluated(L.MARRIAGE)).invoke(
        frozenset({C.ASTRO_DOMAIN, C.ASTRO_DASHA, C.ASTRO_TRANSIT})
    )
    assert out.provided == frozenset({C.ASTRO_DOMAIN})


def test_a_policy_blocked_rule_reaches_the_model_as_nothing() -> None:
    blocked = rule(
        L.CAREER,
        "DOM_CAREER_WITHHELD_X",
        status=DomainStatus.POLICY_BLOCKED,
        reason=DomainReason.HISTORICAL_STATEMENT_WITHHELD,
    )
    out = DomainAnalysisTool(evaluated(L.CAREER, extra_rules=(blocked,))).invoke(
        frozenset({C.ASTRO_DOMAIN})
    )
    assert "DOM_CAREER_WITHHELD_X" not in {r.evidence_id for r in out.records}
    assert "withheld_by_policy=1" in out.records[0].text


def test_a_not_evaluable_result_serves_only_its_status() -> None:
    result = refused(L.STARTUP, DomainStatus.NOT_EVALUABLE, DomainReason.NO_SOURCE_READ)
    out = DomainAnalysisTool(result).invoke(frozenset({C.ASTRO_DOMAIN}))
    assert [r.kind for r in out.records] == ["DOMAIN_STATUS"]
    assert out.records[0].status == "NOT_EVALUABLE"


# ---- end to end through the orchestrator --------------------------------------------------------


def test_an_evaluated_domain_reaches_narration_with_resolvable_references() -> None:
    response, runtime = _run(evaluated(L.CAREER))
    assert response.domain is Domain.ASTROLOGY and response.intent is Intent.CAREER
    assert response.status in {AgentStatus.COMPLETED, AgentStatus.DEGRADED}
    first = response.claims[0]
    assert [r.evidence_id for r in first.references] == ["DOM_CAREER_HOUSE_10_P11"]
    assert len(runtime.calls) == 1
    assert all(c.verification.value == "UNVERIFIED" for c in response.claims)
    assert response.verified_by is None


def test_a_policy_blocked_domain_never_calls_the_model() -> None:
    result = refused(
        L.MARRIAGE,
        DomainStatus.POLICY_BLOCKED,
        DomainReason.ADULT_CONFIRMATION_REQUIRED,
        support=DomainSupport.SOURCE_SUPPORTED,
    )
    response, runtime = _run(result, "Tell me about my marriage", script=[])
    assert response.status is AgentStatus.REFUSED
    assert response.error is not None and response.error.code is AgentErrorCode.UNSAFE_REQUEST
    assert "adult" in (response.user_message or "")
    assert runtime.calls == []


def test_the_minors_policy_message_is_distinct() -> None:
    result = refused(
        L.CHILDHOOD, DomainStatus.POLICY_BLOCKED, DomainReason.MINORS_POLICY_UNRESOLVED
    )
    response, runtime = _run(result, "Tell me about my childhood", script=[])
    assert response.status is AgentStatus.REFUSED and runtime.calls == []
    assert "minor" in (response.user_message or "").lower()


def test_a_not_evaluable_domain_is_a_structured_insufficiency_without_the_model() -> None:
    result = refused(L.STARTUP, DomainStatus.NOT_EVALUABLE, DomainReason.NO_SOURCE_READ)
    response, runtime = _run(result, "Tell me about my startup", script=[])
    assert response.error is not None
    assert response.error.code is AgentErrorCode.INSUFFICIENT_EVIDENCE
    assert runtime.calls == []
    assert response.verification.value == "UNVERIFIED"


def test_the_domain_messages_are_localised() -> None:
    result = refused(
        L.MARRIAGE, DomainStatus.POLICY_BLOCKED, DomainReason.ADULT_CONFIRMATION_REQUIRED
    )
    texts = {
        lang: _run(result, "Tell me about my marriage", script=[], language=lang)[0].user_message
        for lang in LLMLanguage
    }
    assert len(set(texts.values())) == len(texts) and all(texts.values())


def test_a_high_impact_domain_reading_carries_a_no_guarantee_disclaimer() -> None:
    finance = evaluated(
        L.FINANCE,
        policy=(PolicyClass.FINANCE_INTERPRETIVE_ONLY, PolicyClass.PROFESSIONAL_ADVICE_DISCLAIMER),
    )
    response, _ = _run(finance, "Tell me about my finance")
    assert response.disclaimers
    assert "NO_GUARANTEED_OUTCOME" in {d.code.value for d in response.disclaimers}


# ---- request and claim screens (policy cannot be bypassed by the model) -------------------------


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("will I ever have a baby", "PREDICTIVE_FERTILITY"),
        ("how many children will I have", "PREDICTIVE_FERTILITY"),
        ("kitne bachche honge", "PREDICTIVE_FERTILITY"),
        ("how long will my husband live", "SPOUSE_LONGEVITY"),
        ("when will my wife die", "SPOUSE_LONGEVITY"),
        ("which stocks should I buy", "FINANCE_ADVICE"),
        ("guaranteed profit please", "FINANCE_ADVICE"),
    ],
)
def test_prohibited_requests_are_screened(text: str, label: str) -> None:
    assert label in screen_domain_request(text)


def test_ordinary_requests_are_not_screened() -> None:
    for text in ("how is my career", "what does the tenth house mean", "tell me about marriage"):
        assert screen_domain_request(text) == ()


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("You will have no children.", "fertility_outcome"),
        ("The child may be illegitimate.", "legitimacy"),
        ("Your husband will die early.", "spouse_longevity"),
        ("You will definitely become rich.", "finance_certainty"),
        ("I diagnose a disease here.", "medical_claim"),
        ("A sinful and wicked person.", "moral_or_stigma_label"),
    ],
)
def test_harmful_generated_claims_are_screened(text: str, label: str) -> None:
    assert label in screen_domain_claim(text)


def test_neutral_traditional_wording_is_not_screened() -> None:
    assert screen_domain_claim("The tenth house is traditionally linked to profession.") == ()


@pytest.mark.parametrize(
    "text",
    [
        "will I ever have a baby? career",
        "how long will my husband live? career",
        "which stocks should I buy? career",
    ],
)
def test_a_prohibited_domain_request_is_refused_before_any_tool_or_model(text: str) -> None:
    response, runtime = _run(evaluated(L.CAREER), text, script=[])
    assert response.status is AgentStatus.REFUSED
    assert response.error is not None and response.error.code is AgentErrorCode.UNSAFE_REQUEST
    assert runtime.calls == []


def test_a_model_claim_that_states_a_prohibited_outcome_is_not_released() -> None:
    bad = narration(
        (
            "Reading",
            [
                claim(
                    "You will have no children.",
                    "TRADITIONAL_INTERPRETATION",
                    ["DOM_CAREER_HOUSE_10_P11"],
                )
            ],
        )
    )
    response, _ = _run(evaluated(L.CAREER), script=[bad, bad, bad, bad])
    assert all("no children" not in c.text.lower() for c in response.claims)


def test_the_model_cannot_cite_evidence_it_was_not_given() -> None:
    forged = narration(
        ("Reading", [claim("A claim.", "TRADITIONAL_INTERPRETATION", ["DOM_FORGED_RULE"])])
    )
    response, _ = _run(evaluated(L.CAREER), script=[forged, forged, forged, forged])
    assert all(r.evidence_id != "DOM_FORGED_RULE" for c in response.claims for r in c.references)


# ---- Phase 15 behaviour is unchanged -------------------------------------------------------------


def test_a_palm_request_is_unaffected_by_a_registered_domain_tool() -> None:
    agent, _, _ = make_agent(
        [], tools=[palm_tool(), astro_tool(), DomainAnalysisTool(evaluated(L.CAREER))]
    )
    plan = build_plan(
        Domain.PALMISTRY,
        Intent.PALM_OVERVIEW,
        ToolRegistry([palm_tool(), DomainAnalysisTool(evaluated(L.CAREER))]),
    )
    assert plan.life_domain is None and agent is not None


def test_the_agent_request_has_no_sex_age_or_adult_field_the_model_could_set() -> None:
    names = set(AgentRequest.model_fields)
    assert not names & {
        "sex",
        "gender",
        "age",
        "minor",
        "is_minor",
        "adult",
        "subject_adult_confirmed",
    }


def test_no_preset_asks_for_transit_evidence_because_no_domain_reads_it() -> None:
    assert not any(p.transit for p in PRESETS.values())
    assert not any(C.ASTRO_TRANSIT in p.desired for p in PRESETS.values())
    plan = build_plan(
        Domain.ASTROLOGY,
        Intent.CAREER,
        ToolRegistry([DomainAnalysisTool(evaluated(L.CAREER))]),
        L.CAREER,
    )
    assert all(C.ASTRO_TRANSIT not in step.capabilities for step in plan.steps)
