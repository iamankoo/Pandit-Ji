"""Helpers for the Phase 17 agent tests: domain results built from the contracts only.

The agent package depends on ``pandit-contracts`` and not on the rule engine, so these results are
constructed directly with the contract types (the rule engine has its own evaluator tests).
"""

from __future__ import annotations

from pandit_contracts.domain import (
    DomainAnalysisResult,
    DomainFact,
    DomainFactKind,
    DomainInputs,
    DomainInterpretation,
    DomainReason,
    DomainReasonRecord,
    DomainRuleKind,
    DomainRuleResult,
    DomainStatus,
    DomainSupport,
    DomainVersions,
    LifeDomain,
    PolicyClass,
    with_hash,
)

DOMAIN_KV = "KV-0123456789abcdef"
VERSIONS = DomainVersions(
    knowledge_version=DOMAIN_KV,
    methodology_version="1",
    ruleset_id="PANDIT_JI_DOMAIN_PHASE17",
    ruleset_version="1.0.0",
    ruleset_hash="a" * 64,
    evaluator_version="1.0.0",
)


def fact(
    domain: LifeDomain = LifeDomain.CAREER, fact_id: str = "dom_career_house_10.state"
) -> DomainFact:
    return DomainFact(
        fact_id=fact_id,
        kind=DomainFactKind.HOUSE_STATE,
        domain=domain,
        mapping_id=f"MAP.{domain.value}.HOUSE.10.P11",
        subject="house:10",
        attributes=(("house", "10"), ("house_sign", "capricorn"), ("lord", "saturn")),
        chart_refs=("astro.lagna", "astro.planet.saturn"),
        house_refs=(10,),
        source_profile="KB_BPHS_SAN_HOUSE_SIGNIFICATION_11_2_13",
        source_location="Ch. 11 v. 2-13",
        support=DomainSupport.SOURCE_SUPPORTED,
    )


def rule(
    domain: LifeDomain = LifeDomain.CAREER,
    rule_id: str = "DOM_CAREER_HOUSE_10_P11",
    *,
    fact_id: str = "dom_career_house_10.state",
    status: DomainStatus = DomainStatus.TRIGGERED,
    reason: DomainReason | None = None,
    flags: tuple[PolicyClass, ...] = (),
) -> DomainRuleResult:
    blocked = status is DomainStatus.POLICY_BLOCKED
    return DomainRuleResult(
        rule_id=rule_id,
        rule_version="1",
        kind=DomainRuleKind.HOUSE_RELEVANCE if not blocked else DomainRuleKind.POLICY_WITHHELD,
        status=status,
        reason=reason,
        source_profile="KB_BPHS_SAN_HOUSE_SIGNIFICATION_11_2_13",
        source_id="BPHS_SANTHANAM_1984",
        source_location="Ch. 11 v. 2-13",
        verification_level="IMAGE-TRANSLATION",
        support=DomainSupport.SOURCE_SUPPORTED,
        fact_refs=() if blocked else (fact_id,),
        interpretation=(
            DomainInterpretation(
                domain_tags=("career",),
                signification_tags=("career.house_10",),
                effect_class="neutral",
            )
            if status is DomainStatus.TRIGGERED
            else None
        ),
        policy_flags=flags,
    )


def evaluated(
    domain: LifeDomain = LifeDomain.CAREER,
    *,
    policy: tuple[PolicyClass, ...] = (),
    dasha: bool = False,
    transit: bool = False,
    extra_rules: tuple[DomainRuleResult, ...] = (),
) -> DomainAnalysisResult:
    return with_hash(
        analysis_id="an-1",
        domain=domain,
        parent_domain=None,
        support=DomainSupport.SOURCE_SUPPORTED,
        status=DomainStatus.EVALUATED,
        reasons=(),
        facts=(fact(domain),),
        rules=(rule(domain), *extra_rules),
        policy_flags=policy,
        versions=VERSIONS,
        inputs=DomainInputs(dasha_available=dasha, transit_available=transit),
    )


def refused(
    domain: LifeDomain,
    status: DomainStatus,
    reason: DomainReason,
    *,
    support: DomainSupport = DomainSupport.NOT_EVALUABLE,
    policy: tuple[PolicyClass, ...] = (),
) -> DomainAnalysisResult:
    return with_hash(
        analysis_id="an-2",
        domain=domain,
        parent_domain=None,
        support=support,
        status=status,
        reasons=(DomainReasonRecord(code=reason),),
        facts=(),
        rules=(),
        policy_flags=policy,
        versions=VERSIONS,
        inputs=DomainInputs(),
    )
