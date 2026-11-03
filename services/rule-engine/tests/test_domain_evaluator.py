"""The Phase 17 domain evaluator over synthetic charts (ADR-012; LD-01 to LD-27).

Every expected status below is a *designed* outcome: a domain without a source-backed method is
``NOT_EVALUABLE``, a missing input is ``INSUFFICIENT_EVIDENCE``, a policy gate is
``POLICY_BLOCKED`` and an unresolved source conflict is ``CONFLICTING_EVIDENCE``.
"""

from __future__ import annotations

import pytest
from pandit_contracts.domain import (
    DomainAnalysisRequest,
    DomainReason,
    DomainRuleKind,
    DomainStatus,
    DomainSupport,
    LifeDomain,
    PolicyClass,
)
from pydantic import ValidationError

from pandit_rule_engine.domain import evaluate_domain, varga_from_kundli
from tests.domain_helpers import (
    BASE,
    KV,
    dasha,
    evaluate,
    facts,
    ruleset,
    transit,
    varga_of,
)

L = LifeDomain
S = DomainStatus

SOURCE_SUPPORTED = {L.EDUCATION, L.CAREER, L.FINANCE, L.WEALTH, L.MARRIAGE, L.FAMILY, L.CHILDREN}
PARTIAL = {
    L.PERSONALITY, L.SUBJECTS, L.JOB, L.BUSINESS, L.LOVE, L.RELATIONSHIP, L.SPOUSE, L.TRAVEL,
    L.FOREIGN_TRAVEL, L.FOREIGN_SETTLEMENT, L.SPIRITUALITY,
}  # fmt: skip
NOT_EVALUABLE = {
    L.BIRTH, L.COLLEGE, L.CORPORATE_LIFE, L.STARTUP, L.GF_BF, L.FOREIGN_EDUCATION, L.PERSONAL_LIFE,
}  # fmt: skip
MINORS_BLOCKED = {L.CHILDHOOD, L.SCHOOL}
ADULT_GATED = {
    L.LOVE, L.RELATIONSHIP, L.MARRIAGE, L.SPOUSE, L.FAMILY, L.CHILDREN, L.PARENTS, L.SIBLINGS,
}  # fmt: skip
RULE_BY_ID = ruleset().rules


# ---- the 27 domains and the 9 extensions: designed statuses -------------------------------------


@pytest.mark.parametrize("domain", sorted(SOURCE_SUPPORTED | PARTIAL, key=lambda d: d.value))
def test_supported_and_partial_domains_are_evaluated_with_facts(domain: LifeDomain) -> None:
    result = evaluate(domain, varga=varga_of())
    assert result.status is S.EVALUATED
    assert result.facts, "an evaluated domain exposes structured facts"
    expected = (
        DomainSupport.SOURCE_SUPPORTED
        if domain in SOURCE_SUPPORTED
        else DomainSupport.PARTIALLY_SUPPORTED
    )
    assert result.support is expected


@pytest.mark.parametrize("domain", sorted(NOT_EVALUABLE, key=lambda d: d.value))
def test_unsupported_domains_are_not_evaluable_without_facts_or_rules(domain: LifeDomain) -> None:
    result = evaluate(domain, varga=varga_of())
    assert result.status is S.NOT_EVALUABLE
    assert result.support is DomainSupport.NOT_EVALUABLE
    assert result.facts == () and result.rules == ()
    assert result.reasons, "a typed reason is always present"


@pytest.mark.parametrize("domain", sorted(MINORS_BLOCKED, key=lambda d: d.value))
def test_childhood_and_school_stay_policy_blocked_even_for_a_confirmed_adult(
    domain: LifeDomain,
) -> None:
    for adult in (True, False, None):
        result = evaluate(domain, adult=adult)
        assert result.status is S.POLICY_BLOCKED
        assert result.reasons[0].code is DomainReason.MINORS_POLICY_UNRESOLVED
        assert result.facts == ()


def test_a_subdomain_never_inherits_the_support_of_its_parent() -> None:
    rs = ruleset()
    for child, parent in [(L.JOB, L.CAREER), (L.SCHOOL, L.EDUCATION), (L.GF_BF, L.MARRIAGE)]:
        assert rs.entry(parent).support is DomainSupport.SOURCE_SUPPORTED
        assert rs.entry(child).support is not DomainSupport.SOURCE_SUPPORTED
    # Job has its own two rules; it does not execute any Career rule.
    job = evaluate(L.JOB, varga=varga_of())
    assert {r.rule_id for r in job.rules}.isdisjoint({r.rule_id for r in evaluate(L.CAREER).rules})
    assert all(RULE_BY_ID[r.rule_id].domain is L.JOB for r in job.rules)


def test_every_result_rule_belongs_to_the_requested_domain() -> None:
    for domain in L:
        result = evaluate(domain, varga=varga_of())
        assert all(RULE_BY_ID[r.rule_id].domain is domain for r in result.rules)


# ---- adulthood gate and the absent sex field ---------------------------------------------------


@pytest.mark.parametrize("domain", sorted(ADULT_GATED, key=lambda d: d.value))
@pytest.mark.parametrize("adult", [None, False])
def test_relationship_family_and_children_need_explicit_adult_confirmation(
    domain: LifeDomain, adult: bool | None
) -> None:
    result = evaluate(domain, adult=adult)
    assert result.status is S.POLICY_BLOCKED
    assert result.reasons[0].code is DomainReason.ADULT_CONFIRMATION_REQUIRED
    assert result.facts == () and result.rules == ()


@pytest.mark.parametrize("domain", sorted(ADULT_GATED - {L.GF_BF}, key=lambda d: d.value))
def test_explicit_adult_confirmation_unlocks_the_evaluation(domain: LifeDomain) -> None:
    assert evaluate(domain, adult=True).status is S.EVALUATED


def test_the_request_contract_has_no_sex_age_or_minor_field() -> None:
    names = set(DomainAnalysisRequest.model_fields)
    assert not {n for n in names if any(w in n for w in ("sex", "gender", "age", "minor", "dob"))}
    assert "subject_adult_confirmed" in names
    with pytest.raises(ValidationError):
        DomainAnalysisRequest.model_validate({"analysis_id": "x", "domain": "CAREER", "sex": "f"})


def test_sex_specific_methods_are_not_evaluable_never_guessed() -> None:
    result = evaluate(L.SPOUSE)
    sex = [r for r in result.rules if r.reason is DomainReason.SEX_SPECIFIC_METHOD]
    assert sex and all(r.status is S.NOT_EVALUABLE for r in sex)
    assert PolicyClass.SEX_SPECIFIC_SOURCE in result.policy_flags


# ---- policy: spouse longevity, children, fertility, finance, health -----------------------------


def test_spouse_longevity_is_permanently_blocked_and_exposes_nothing() -> None:
    blocked = [
        rule
        for rule in RULE_BY_ID.values()
        if getattr(rule.params, "phase6_signification", None) == "marriage.spouse_longevity"
    ]
    assert blocked
    for rule in blocked:
        assert rule.params.blocked is True  # type: ignore[union-attr]
    result = evaluate(
        L.MARRIAGE, phase6_results={r.params.phase6_rule_id: "TRIGGERED" for r in blocked}
    )  # type: ignore[union-attr]
    for rule in blocked:
        got = next(r for r in result.rules if r.rule_id == rule.rule_id)
        assert got.status is S.POLICY_BLOCKED
        assert got.reason is DomainReason.SPOUSE_LONGEVITY_BLOCKED
        assert got.interpretation is None
    dumped = result.model_dump_json()
    assert "marriage.spouse_longevity" not in dumped.replace('"phase6_signification"', "")


def test_children_exposes_only_structural_significations_and_blocks_outcomes() -> None:
    result = evaluate(L.CHILDREN, varga=varga_of())
    reasons = {r.reason for r in result.rules}
    assert DomainReason.PREDICTIVE_FERTILITY_BLOCKED in reasons
    for r in result.rules:
        if r.reason in {
            DomainReason.PREDICTIVE_FERTILITY_BLOCKED,
            DomainReason.HISTORICAL_STATEMENT_WITHHELD,
        }:
            assert r.status in {S.POLICY_BLOCKED, S.NOT_EVALUABLE}
            assert r.interpretation is None
    exposed = " ".join(
        [f"{k}={v}" for f in result.facts for k, v in f.attributes]
        + [t for r in result.rules if r.interpretation for t in r.interpretation.signification_tags]
    ).lower()
    for forbidden in (
        "number_of_children",
        "fertility",
        "pregnan",
        "legitima",
        "miscarr",
        "loss_of",
    ):
        assert forbidden not in exposed


def test_finance_and_wealth_carry_the_professional_advice_policy() -> None:
    for domain in (L.FINANCE, L.WEALTH, L.INCOME):
        flags = evaluate(domain, varga=varga_of()).policy_flags
        assert PolicyClass.FINANCE_INTERPRETIVE_ONLY in flags


def test_health_is_not_evaluable_and_carries_the_medical_policy() -> None:
    result = evaluate(L.HEALTH)
    assert result.status is S.NOT_EVALUABLE
    assert result.facts == () and result.rules == ()
    assert PolicyClass.HEALTH_INTERPRETATION_ONLY in result.policy_flags


def test_withheld_historical_statements_are_never_triggered_or_given_tags() -> None:
    for domain in (L.CHILDREN, L.SUBJECTS, L.SPIRITUALITY):
        result = evaluate(domain, varga=varga_of())
        for rule in result.rules:
            if RULE_BY_ID[rule.rule_id].kind is DomainRuleKind.POLICY_WITHHELD:
                assert rule.status in {S.POLICY_BLOCKED, S.NOT_EVALUABLE}
                assert rule.interpretation is None


# ---- missing inputs are INSUFFICIENT_EVIDENCE, never defaults ----------------------------------


def test_missing_varga_makes_varga_rules_insufficient_and_never_fakes_a_placement() -> None:
    result = evaluate(L.CHILDREN, varga=None)
    d7 = next(r for r in result.rules if r.rule_id == "DOM_CHILDREN_VARGA_D7_B7")
    assert d7.status is S.INSUFFICIENT_EVIDENCE
    assert d7.reason is DomainReason.MISSING_VARGA_EVIDENCE
    assert not any(f.varga_refs for f in result.facts)
    assert result.inputs.varga_available is False


def test_a_missing_single_varga_chart_is_insufficient() -> None:
    result = evaluate(L.CHILDREN, varga=varga_of(numbers=(9,)))
    d7 = next(r for r in result.rules if r.rule_id == "DOM_CHILDREN_VARGA_D7_B7")
    assert d7.status is S.INSUFFICIENT_EVIDENCE


def test_varga_present_gives_a_placement_fact_for_exactly_the_locked_varga() -> None:
    result = evaluate(L.CHILDREN, varga=varga_of())
    fact = next(f for f in result.facts if f.varga_refs)
    assert fact.varga_refs == (7,)
    assert dict(fact.attributes)["varga"] == "D7"


def test_the_marriage_dasha_method_needs_a_dasha_section_and_as_of() -> None:
    rule_id = "DOM_MARRIAGE_METHOD_PX13_DASHA_7TH_PX13"
    absent = evaluate(L.MARRIAGE)
    got = next(r for r in absent.rules if r.rule_id == rule_id)
    assert (
        got.status is S.INSUFFICIENT_EVIDENCE and got.reason is DomainReason.MISSING_DASHA_EVIDENCE
    )
    timeline = dasha(
        [("mahadasha", "venus", "2020-01-01T00:00:00+00:00", "2040-01-01T00:00:00+00:00")]
    )
    no_clock = evaluate(L.MARRIAGE, dasha=timeline)
    assert next(r for r in no_clock.rules if r.rule_id == rule_id).status is S.INSUFFICIENT_EVIDENCE
    outside = evaluate(L.MARRIAGE, dasha=timeline, as_of="2050-01-01T00:00:00+00:00")
    assert next(r for r in outside.rules if r.rule_id == rule_id).status is S.INSUFFICIENT_EVIDENCE


def test_the_marriage_dasha_method_is_the_phaladeepika_7th_house_relation_only() -> None:
    rule_id = "DOM_MARRIAGE_METHOD_PX13_DASHA_7TH_PX13"
    # BASE (Aries lagna): Venus owns and occupies the 7th (Libra); the Sun (5th) does not touch it.
    venus = dasha(
        [("mahadasha", "venus", "2020-01-01T00:00:00+00:00", "2040-01-01T00:00:00+00:00")]
    )
    sun = dasha([("mahadasha", "sun", "2020-01-01T00:00:00+00:00", "2040-01-01T00:00:00+00:00")])
    on = evaluate(L.MARRIAGE, dasha=venus, as_of="2026-06-01T00:00:00+00:00")
    off = evaluate(L.MARRIAGE, dasha=sun, as_of="2026-06-01T00:00:00+00:00")
    assert next(r for r in on.rules if r.rule_id == rule_id).status is S.TRIGGERED
    assert next(r for r in off.rules if r.rule_id == rule_id).status is S.NOT_TRIGGERED
    fact = next(f for f in on.facts if f.dasha_refs)
    assert dict(fact.attributes)["relation_owns"] == "true"
    assert on.inputs.dasha_available is True


def test_the_rejected_occupant_owner_aspector_analogy_is_not_used_for_other_domains() -> None:
    for domain in L:
        if domain is L.MARRIAGE:
            continue
        assert all(
            r.kind is not DomainRuleKind.MARRIAGE_DASHA_METHOD for r in ruleset().rules_for(domain)
        )
        result = evaluate(
            domain,
            varga=varga_of(),
            dasha=dasha(
                [("mahadasha", "venus", "2020-01-01T00:00:00+00:00", "2040-01-01T00:00:00+00:00")]
            ),
            as_of="2026-06-01T00:00:00+00:00",
        )
        assert not any(f.dasha_refs for f in result.facts)


def test_an_unusable_dasha_status_is_insufficient() -> None:
    bad = dasha([], status="failed")
    result = evaluate(L.MARRIAGE, dasha=bad, as_of="2026-06-01T00:00:00+00:00")
    rule = next(r for r in result.rules if r.rule_id == "DOM_MARRIAGE_METHOD_PX13_DASHA_7TH_PX13")
    assert rule.status is S.INSUFFICIENT_EVIDENCE


def _transit_rules(domain: LifeDomain) -> list[str]:
    return [
        r.rule_id
        for r in ruleset().rules_for(domain)
        if r.kind is DomainRuleKind.BHAVA_TRANSIT_METHOD
    ]


def test_transit_rules_are_insufficient_without_a_transit_section() -> None:
    ids = _transit_rules(L.CAREER)
    assert ids
    result = evaluate(L.CAREER, varga=varga_of())
    for rule_id in ids:
        got = next(r for r in result.rules if r.rule_id == rule_id)
        assert got.status is S.INSUFFICIENT_EVIDENCE
        assert got.reason is DomainReason.MISSING_TRANSIT_EVIDENCE
    assert result.inputs.transit_available is False


def test_a_failed_transit_section_is_insufficient_not_defaulted() -> None:
    bad = transit({"jupiter": "leo"}, status="failed")
    result = evaluate(L.CAREER, varga=varga_of(), transit=bad)
    for rule_id in _transit_rules(L.CAREER):
        assert (
            next(r for r in result.rules if r.rule_id == rule_id).status is S.INSUFFICIENT_EVIDENCE
        )


def test_transit_rules_use_supplied_transit_and_label_unevaluated_alternatives() -> None:
    signs = {b: s for b, s in BASE.items() if b != "ketu"}
    result = evaluate(
        L.CAREER, varga=varga_of(), transit=transit(signs), as_of="2026-09-21T12:00:00+00:00"
    )
    for rule_id in _transit_rules(L.CAREER):
        got = next(r for r in result.rules if r.rule_id == rule_id)
        assert got.status in {S.TRIGGERED, S.NOT_TRIGGERED, S.CONFLICTING_EVIDENCE}
    fact = next(f for f in result.facts if f.transit_refs)
    attrs = dict(fact.attributes)
    assert attrs["aspect_alternative"] == "not_evaluated"
    assert attrs["moon_reckoning"] == "not_evaluated"
    assert result.inputs.transit_available is True


def test_without_d9_the_amsa_alternative_is_never_invented() -> None:
    signs = {b: s for b, s in BASE.items() if b != "ketu"}
    result = evaluate(L.CAREER, transit=transit(signs))
    for rule_id in _transit_rules(L.CAREER):
        got = next(r for r in result.rules if r.rule_id == rule_id)
        if got.status is S.INSUFFICIENT_EVIDENCE:
            assert got.reason is DomainReason.MISSING_VARGA_EVIDENCE
        else:
            assert got.status in {S.TRIGGERED, S.CONFLICTING_EVIDENCE}
    for fact in result.facts:
        if fact.transit_refs:
            assert dict(fact.attributes)["amsa_alternative"] == "not_evaluated_missing_d9"


def test_phase6_dependent_rules_need_the_phase6_results() -> None:
    result = evaluate(L.MARRIAGE)
    p6 = [r for r in result.rules if r.kind is DomainRuleKind.PHASE6_RULE_APPLICABILITY]
    assert p6
    for r in p6:
        if (
            r.reason is not DomainReason.SPOUSE_LONGEVITY_BLOCKED
            and r.status is not S.POLICY_BLOCKED
        ):
            assert r.status is S.INSUFFICIENT_EVIDENCE
    assert result.inputs.phase6_results_available is False


# ---- source conflicts are preserved, never resolved --------------------------------------------


def test_unresolved_conflict_rules_report_conflicting_evidence_without_tags() -> None:
    conflicted = [r for r in RULE_BY_ID.values() if r.support is DomainSupport.UNRESOLVED_CONFLICT]
    assert conflicted
    seen = 0
    for rule in conflicted:
        if rule.domain in {L.CHILDHOOD, L.SCHOOL}:
            continue
        result = evaluate(
            rule.domain,
            varga=varga_of(),
            phase6_results={
                getattr(r.params, "phase6_rule_id", ""): "TRIGGERED" for r in RULE_BY_ID.values()
            },
            transit=transit({b: s for b, s in BASE.items() if b != "ketu"}),
            dasha=dasha(
                [("mahadasha", "venus", "2020-01-01T00:00:00+00:00", "2040-01-01T00:00:00+00:00")]
            ),
            as_of="2026-06-01T00:00:00+00:00",
        )
        got = next(r for r in result.rules if r.rule_id == rule.rule_id)
        assert got.status in {S.CONFLICTING_EVIDENCE, S.INSUFFICIENT_EVIDENCE, S.POLICY_BLOCKED}
        assert got.interpretation is None
        assert got.conflict_ids
        seen += 1
    assert seen


def test_conflicting_sources_keep_distinct_profiles() -> None:
    parents = evaluate(L.PARENTS)
    profiles = {r.source_profile for r in parents.rules}
    assert len(profiles) > 1
    assert any(r.status is S.CONFLICTING_EVIDENCE for r in parents.rules)
    assert all(
        r.interpretation is None for r in parents.rules if r.status is S.CONFLICTING_EVIDENCE
    )


def test_conflict_registry_holds_dc01_to_dc05_and_the_kuja_group() -> None:
    ids = set(ruleset().conflicts)
    assert {"DC-01", "DC-02", "DC-03", "DC-04", "DC-05"} <= ids


# ---- provenance, versions, determinism ---------------------------------------------------------


def test_every_fact_and_rule_result_carries_provenance() -> None:
    for domain in SOURCE_SUPPORTED | PARTIAL:
        result = evaluate(domain, varga=varga_of())
        for rule in result.rules:
            assert rule.source_profile and rule.source_location and rule.source_id
            assert rule.rule_version
        for fact in result.facts:
            assert fact.source_profile and fact.source_location and fact.mapping_id
            assert fact.domain is domain
            assert fact.chart_refs or fact.varga_refs


def test_versions_are_recorded_and_the_hash_is_deterministic() -> None:
    rs = ruleset()
    a = evaluate(L.CAREER, varga=varga_of())
    b = evaluate(L.CAREER, varga=varga_of())
    assert a == b and a.result_hash == b.result_hash
    assert a.versions.knowledge_version == KV
    assert a.versions.ruleset_hash == rs.content_hash
    assert a.versions.ruleset_id == rs.manifest.ruleset_id
    changed = evaluate(L.CAREER, chart=facts("taurus"), varga=varga_of())
    assert changed.result_hash != a.result_hash


def test_dict_order_of_inputs_does_not_change_the_result() -> None:
    forward = dict(BASE)
    reverse = dict(reversed(list(BASE.items())))
    assert (
        evaluate(L.WEALTH, chart=facts("aries", forward)).result_hash
        == evaluate(L.WEALTH, chart=facts("aries", reverse)).result_hash
    )


def test_a_pinned_knowledge_or_ruleset_version_that_differs_is_not_evaluable() -> None:
    rs = ruleset()
    base = {"analysis_id": "t", "domain": L.CAREER}
    k = evaluate_domain(
        rs,
        DomainAnalysisRequest(**base, expected_knowledge_version="KV-ffffffffffffffff"),
        facts(),
        knowledge_version=KV,
    )
    assert (
        k.status is S.NOT_EVALUABLE and k.reasons[0].code is DomainReason.KNOWLEDGE_VERSION_MISMATCH
    )
    h = evaluate_domain(
        rs,
        DomainAnalysisRequest(**base, expected_ruleset_hash="0" * 64),
        facts(),
        knowledge_version=KV,
    )
    assert (
        h.status is S.NOT_EVALUABLE and h.reasons[0].code is DomainReason.RULESET_VERSION_MISMATCH
    )
    ok = evaluate_domain(
        rs,
        DomainAnalysisRequest(
            **base, expected_knowledge_version=KV, expected_ruleset_hash=rs.content_hash
        ),
        facts(),
        knowledge_version=KV,
    )
    assert ok.status is S.EVALUATED


# ---- the Varga adapter reads the existing Kundli JSON only --------------------------------------


def test_varga_from_kundli_is_none_without_charts() -> None:
    from tests.domain_helpers import kundli

    assert varga_from_kundli(kundli()) is None


def test_varga_from_kundli_reads_signs_and_hashes_deterministically() -> None:
    first, second = varga_of(), varga_of()
    assert first.facts_hash == second.facts_hash
    assert first.chart(9) is not None and first.chart(4) is None
    assert varga_of(signs={b: "leo" for b in BASE}).facts_hash != first.facts_hash


def test_no_unlocked_varga_is_ever_requested_by_a_rule() -> None:
    from pandit_rule_engine.domain.schema import VargaParams

    used = {r.params.varga for r in RULE_BY_ID.values() if isinstance(r.params, VargaParams)}
    assert used <= {2, 3, 7, 9, 10, 12, 20, 24}
    assert 4 not in used
