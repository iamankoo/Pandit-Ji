"""Deterministic evaluation of the Phase 17 domain ruleset over facts that already exist.

``evaluate_domain`` turns one request, one D1 chart and the optional sections of a supplied
evidence bundle into a :class:`DomainAnalysisResult`. It computes no astronomy, reads no clock,
no file and no network, calls no model and invents no methodology:

* a domain without an approved, source-backed mapping is ``NOT_EVALUABLE`` with a typed reason;
* a policy gate (a static block, or adulthood not stated by the caller) is ``POLICY_BLOCKED``
  and nothing else is produced;
* a required input that was not supplied (a divisional chart, the dasha section, the Phase 6 rule
  results, ``as_of_utc``) makes that rule ``INSUFFICIENT_EVIDENCE`` and is never replaced by a
  default; an absent dasha section carries the typed reason ``PHASE_18_DEPENDENCY`` (LD-14), a
  present but unusable one ``MISSING_DASHA_EVIDENCE``;
* no rule reads the transit section: the six Phaladeepika XVI sl. 31-32 records are non-evaluating
  (``NOT_EVALUABLE``, ``RESEARCH_PENDING``) because the owner did not approve applying a general
  bhava method to a domain's mapped house; the section is only recorded as present or absent;
* a mapping with an unresolved source conflict is ``CONFLICTING_EVIDENCE``, with the conflict
  named and no tags exposed;
* facts are structural (a house's sign and lord, a karaka's placement, a divisional placement, a
  relation of a dasha lord to the 7th house);
  none states an effect or a prediction. The interpretation tags of a triggered rule are the
  structured significations the source assigns, never prose.

The result is identical for identical inputs (no randomness, no time). Whole-sign counting
arithmetic on supplied facts is the only computation.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone

from pandit_contracts.domain import (
    DomainAnalysisRequest,
    DomainAnalysisResult,
    DomainFact,
    DomainFactKind,
    DomainInputs,
    DomainInterpretation,
    DomainReason,
    DomainReasonRecord,
    DomainRuleResult,
    DomainStatus,
    DomainSupport,
    DomainVersions,
    PolicyClass,
    with_hash,
)

from pandit_rule_engine.dasha_evidence import DashaEvidence
from pandit_rule_engine.domain.inputs import VargaPlacements
from pandit_rule_engine.domain.loader import DomainRuleset
from pandit_rule_engine.domain.schema import (
    DomainRuleDocument,
    HouseParams,
    KarakaParams,
    MarriageDashaParams,
    Phase6Params,
    SubjectParams,
    VargaParams,
    WithheldParams,
)
from pandit_rule_engine.facts import ChartFacts, PlanetFact
from pandit_rule_engine.transit_evidence import TransitEvidence
from pandit_rule_engine.vocab import SIGN_INDEX, SIGN_ORDER, Body, Sign

EVALUATOR_VERSION = "1.0.0"

_USABLE_DASHA = frozenset({"success", "approximate"})


class _Insufficient(Exception):
    """A rule's required input is missing (typed; never a default)."""

    def __init__(self, reason: DomainReason, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def _house_sign(facts: ChartFacts, house: int) -> Sign:
    return SIGN_ORDER[(SIGN_INDEX[facts.lagna_sign] + house - 1) % 12]


def _lord(facts: ChartFacts, sign: Sign) -> Body:
    return facts.sign_lords[sign]


def _planet(facts: ChartFacts, body: Body) -> PlanetFact:
    planet = facts.planet(body)
    if planet is None:
        raise _Insufficient(DomainReason.MISSING_FACT, f"planet.{body.value}")
    return planet


def _astro_ref(body: Body) -> str:
    return f"astro.planet.{body.value}"


def _pairs(**values: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(values.items()))


def _tags(rule: DomainRuleDocument) -> DomainInterpretation:
    return DomainInterpretation(
        domain_tags=rule.tags.domain_tags,
        signification_tags=rule.tags.signification_tags,
        effect_class=rule.tags.effect_class,
    )


def _parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fact_base(rule: DomainRuleDocument) -> dict[str, object]:
    return {
        "domain": rule.domain,
        "mapping_id": rule.mapping_id,
        "source_profile": rule.profile,
        "source_location": rule.source_location,
        "support": rule.support,
        "policy_flags": rule.policy_flags,
    }


def _result(
    rule: DomainRuleDocument,
    status: DomainStatus,
    *,
    reason: DomainReason | None = None,
    detail: str | None = None,
    fact_refs: tuple[str, ...] = (),
    interpretation: DomainInterpretation | None = None,
    phase6_rule_id: str | None = None,
    phase6_status: str | None = None,
) -> DomainRuleResult:
    return DomainRuleResult(
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        kind=rule.kind,
        status=status,
        reason=reason,
        source_profile=rule.profile,
        source_id=rule.source_id,
        source_location=rule.source_location,
        verification_level=rule.verification_level,
        support=rule.support,
        fact_refs=fact_refs,
        interpretation=interpretation,
        phase6_rule_id=phase6_rule_id,
        phase6_status=phase6_status,
        conflict_ids=rule.conflict_ids,
        policy_flags=rule.policy_flags,
        detail=detail,
    )


def _applied(
    rule: DomainRuleDocument, fact: DomainFact, *, holds: bool = True
) -> tuple[DomainFact, DomainRuleResult]:
    """The outcome of a rule that produced a fact: conflicting, triggered or not triggered."""
    if rule.support is DomainSupport.UNRESOLVED_CONFLICT:
        return fact, _result(
            rule,
            DomainStatus.CONFLICTING_EVIDENCE,
            reason=DomainReason.SOURCE_CONFLICT,
            detail=",".join(rule.conflict_ids),
            fact_refs=(fact.fact_id,),
        )
    if holds:
        return fact, _result(
            rule, DomainStatus.TRIGGERED, fact_refs=(fact.fact_id,), interpretation=_tags(rule)
        )
    return fact, _result(rule, DomainStatus.NOT_TRIGGERED, fact_refs=(fact.fact_id,))


# -- the rule kinds ----------------------------------------------------------------------------


def _house_rule(
    rule: DomainRuleDocument, params: HouseParams, facts: ChartFacts
) -> tuple[DomainFact, DomainRuleResult]:
    sign = _house_sign(facts, params.house)
    lord = _lord(facts, sign)
    lord_fact = _planet(facts, lord)
    attrs: dict[str, str] = {
        "house": str(params.house),
        "house_sign": sign.value,
        "lord": lord.value,
    }
    refs = ["astro.lagna", _astro_ref(lord)]
    if params.detail == "FULL":
        occupants = sorted(b.value for b, p in facts.planets.items() if p.house == params.house)
        aspected_by = sorted(
            b.value for b, p in facts.planets.items() if params.house in p.aspected_houses
        )
        attrs.update(
            {
                "lord_house": str(lord_fact.house),
                "lord_sign": lord_fact.sign.value,
                "lord_dignity": lord_fact.dignity.value if lord_fact.dignity else "not_evaluated",
                "occupants": ",".join(occupants) or "none",
                "aspected_by_full_sign_drishti": ",".join(aspected_by) or "none",
            }
        )
        refs.extend(_astro_ref(Body(o)) for o in occupants)
    fact = DomainFact(
        fact_id=f"{rule.rule_id.lower()}.state",
        kind=DomainFactKind.HOUSE_STATE,
        subject=f"house:{params.house}",
        attributes=tuple(sorted(attrs.items())),
        chart_refs=tuple(dict.fromkeys(refs)),
        house_refs=(params.house,),
        **_fact_base(rule),  # type: ignore[arg-type]
    )
    return _applied(rule, fact)


def _karaka_rule(
    rule: DomainRuleDocument, params: KarakaParams, facts: ChartFacts
) -> tuple[DomainFact, DomainRuleResult]:
    planet = _planet(facts, params.planet)
    attrs: dict[str, str] = {
        "planet": planet.body.value,
        "planet_sign": planet.sign.value,
        "planet_house": str(planet.house),
    }
    if params.for_house is not None:
        attrs["karaka_of_house"] = str(params.for_house)
    if params.detail == "FULL":
        attrs["dignity"] = planet.dignity.value if planet.dignity else "not_evaluated"
        attrs["retrograde"] = str(planet.retrograde).lower()
        attrs["combust"] = (
            "not_evaluated" if planet.combust is None else str(planet.combust).lower()
        )
    fact = DomainFact(
        fact_id=f"{rule.rule_id.lower()}.state",
        kind=DomainFactKind.KARAKA_STATE,
        subject=f"karaka:{planet.body.value}",
        attributes=tuple(sorted(attrs.items())),
        chart_refs=(_astro_ref(planet.body),),
        house_refs=(params.for_house,) if params.for_house is not None else (),
        karaka_refs=(planet.body.value,),
        **_fact_base(rule),  # type: ignore[arg-type]
    )
    return _applied(rule, fact)


def _varga_rule(
    rule: DomainRuleDocument,
    params: VargaParams,
    facts: ChartFacts,
    varga: VargaPlacements | None,
) -> tuple[DomainFact, DomainRuleResult]:
    if varga is None:
        raise _Insufficient(DomainReason.MISSING_VARGA_EVIDENCE, "no divisional charts supplied")
    chart = varga.chart(params.varga)
    if chart is None:
        raise _Insufficient(DomainReason.MISSING_VARGA_EVIDENCE, f"D{params.varga} not supplied")
    attrs: dict[str, str] = {
        "varga": f"D{params.varga}",
        "varga_ascendant": chart.ascendant.value,
        "varga_scheme": varga.scheme,
    }
    refs: list[str] = []
    karakas: list[str] = []
    for number in params.show_house_lords:
        lord = _lord(facts, _house_sign(facts, number))
        placed = chart.planets.get(lord)
        if placed is None:
            raise _Insufficient(
                DomainReason.MISSING_VARGA_EVIDENCE, f"D{params.varga}.{lord.value}"
            )
        attrs[f"lord_of_house_{number}"] = f"{lord.value}@{placed.value}"
        refs.append(_astro_ref(lord))
    for body in params.show_karakas:
        placed = chart.planets.get(body)
        if placed is None:
            raise _Insufficient(
                DomainReason.MISSING_VARGA_EVIDENCE, f"D{params.varga}.{body.value}"
            )
        attrs[f"karaka_{body.value}"] = f"{body.value}@{placed.value}"
        refs.append(_astro_ref(body))
        karakas.append(body.value)
    if params.show_lagna_lord:
        lord = _lord(facts, facts.lagna_sign)
        placed = chart.planets.get(lord)
        if placed is None:
            raise _Insufficient(
                DomainReason.MISSING_VARGA_EVIDENCE, f"D{params.varga}.{lord.value}"
            )
        attrs["lagna_lord"] = f"{lord.value}@{placed.value}"
        refs.append(_astro_ref(lord))
    fact = DomainFact(
        fact_id=f"{rule.rule_id.lower()}.placement",
        kind=DomainFactKind.VARGA_PLACEMENT,
        subject=f"varga:D{params.varga}",
        attributes=tuple(sorted(attrs.items())),
        chart_refs=tuple(dict.fromkeys(refs)),
        karaka_refs=tuple(karakas),
        varga_refs=(params.varga,),
        **_fact_base(rule),  # type: ignore[arg-type]
    )
    return _applied(rule, fact)


def _phase6_rule(
    rule: DomainRuleDocument,
    params: Phase6Params,
    phase6: Mapping[str, str] | None,
) -> DomainRuleResult:
    if params.blocked:
        reason = (
            DomainReason.SPOUSE_LONGEVITY_BLOCKED
            if params.phase6_signification == "marriage.spouse_longevity"
            else DomainReason.HISTORICAL_STATEMENT_WITHHELD
        )
        return _result(
            rule,
            DomainStatus.POLICY_BLOCKED,
            reason=reason,
            detail=params.phase6_rule_id,
            phase6_rule_id=params.phase6_rule_id,
        )
    if phase6 is None:
        raise _Insufficient(DomainReason.MISSING_FACT, "phase 6 rule results not supplied")
    status = phase6.get(params.phase6_rule_id)
    if status is None:
        raise _Insufficient(DomainReason.MISSING_FACT, params.phase6_rule_id)
    if rule.support is DomainSupport.UNRESOLVED_CONFLICT:
        return _result(
            rule,
            DomainStatus.CONFLICTING_EVIDENCE,
            reason=DomainReason.SOURCE_CONFLICT,
            detail=",".join(rule.conflict_ids),
            phase6_rule_id=params.phase6_rule_id,
            phase6_status=status,
        )
    if status == "TRIGGERED":
        return _result(
            rule,
            DomainStatus.TRIGGERED,
            interpretation=_tags(rule),
            phase6_rule_id=params.phase6_rule_id,
            phase6_status=status,
        )
    if status == "NOT_EVALUABLE":
        return _result(
            rule,
            DomainStatus.NOT_EVALUABLE,
            reason=DomainReason.MISSING_FACT,
            detail=f"{params.phase6_rule_id}: phase 6 result is not evaluable",
            phase6_rule_id=params.phase6_rule_id,
            phase6_status=status,
        )
    return _result(
        rule,
        DomainStatus.NOT_TRIGGERED,
        phase6_rule_id=params.phase6_rule_id,
        phase6_status=status,
    )


def _marriage_dasha_rule(
    rule: DomainRuleDocument,
    params: MarriageDashaParams,
    facts: ChartFacts,
    dasha: DashaEvidence | None,
    as_of_utc: str | None,
) -> tuple[DomainFact, DomainRuleResult]:
    if dasha is None:
        raise _Insufficient(DomainReason.PHASE_18_DEPENDENCY, "no dasha section supplied")
    if dasha.status not in _USABLE_DASHA:
        raise _Insufficient(DomainReason.MISSING_DASHA_EVIDENCE, f"dasha status {dasha.status}")
    if as_of_utc is None:
        raise _Insufficient(DomainReason.MISSING_FACT, "as_of_utc")
    instant = _parse_utc(as_of_utc)
    current = None
    for period in dasha.periods:
        if period.level.lower() != "mahadasha":
            continue
        if _parse_utc(period.start_utc) <= instant < _parse_utc(period.end_utc):
            current = period
            break
    if current is None:
        raise _Insufficient(
            DomainReason.MISSING_DASHA_EVIDENCE, "as_of_utc is outside the timeline"
        )
    house_sign = _house_sign(facts, params.house)
    owner = _lord(facts, house_sign)
    lord_fact = _planet(facts, current.lord)
    relations = {
        "occupies": lord_fact.house == params.house,
        "aspects": params.house in lord_fact.aspected_houses,
        "owns": owner is current.lord,
    }
    holds = any(relations[name] for name in params.relations)
    attrs = {
        "dasha_level": "mahadasha",
        "dasha_lord": current.lord.value,
        "period_start_utc": current.start_utc,
        "period_end_utc": current.end_utc,
        "house": str(params.house),
        "house_sign": house_sign.value,
        "house_lord": owner.value,
        "aspect_basis": "full_sign_drishti",
    }
    for name in ("occupies", "aspects", "owns"):
        attrs[f"relation_{name}"] = str(relations[name]).lower()
    fact = DomainFact(
        fact_id=f"{rule.rule_id.lower()}.relation",
        kind=DomainFactKind.DASHA_RELATION,
        subject=f"dasha:{current.lord.value}",
        attributes=tuple(sorted(attrs.items())),
        chart_refs=("astro.lagna", _astro_ref(current.lord)),
        house_refs=(params.house,),
        dasha_refs=(current.period_id,),
        **_fact_base(rule),  # type: ignore[arg-type]
    )
    return _applied(rule, fact, holds=holds)


def _subject_rule(
    rule: DomainRuleDocument, params: SubjectParams, facts: ChartFacts
) -> tuple[DomainFact, DomainRuleResult]:
    house_sign = _house_sign(facts, params.house)
    second_lord = _lord(facts, house_sign)
    lord_fact = _planet(facts, second_lord)
    other = _planet(facts, params.associated_planet)
    associated = second_lord is not params.associated_planet and lord_fact.sign is other.sign
    fact = DomainFact(
        fact_id=f"{rule.rule_id.lower()}.association",
        kind=DomainFactKind.SUBJECT_ASSOCIATION,
        subject=f"house:{params.house}",
        attributes=_pairs(
            house=str(params.house),
            house_sign=house_sign.value,
            second_lord=second_lord.value,
            second_lord_sign=lord_fact.sign.value,
            associated_planet=params.associated_planet.value,
            associated_planet_sign=other.sign.value,
            association_basis="same_sign",
            associated=str(associated).lower(),
        ),
        chart_refs=("astro.lagna", _astro_ref(second_lord), _astro_ref(params.associated_planet)),
        house_refs=(params.house,),
        **_fact_base(rule),  # type: ignore[arg-type]
    )
    return _applied(rule, fact, holds=associated)


def _withheld_rule(rule: DomainRuleDocument, params: WithheldParams) -> DomainRuleResult:
    status = (
        DomainStatus.POLICY_BLOCKED
        if params.outcome == "POLICY_BLOCKED"
        else DomainStatus.NOT_EVALUABLE
    )
    return _result(rule, status, reason=params.reason, detail=rule.mapping_id)


# -- the analysis ----------------------------------------------------------------------------


def _empty(
    *,
    request: DomainAnalysisRequest,
    ruleset: DomainRuleset,
    versions: DomainVersions,
    inputs: DomainInputs,
    status: DomainStatus,
    reasons: tuple[DomainReasonRecord, ...],
    policy: tuple[PolicyClass, ...],
    rules: tuple[DomainRuleResult, ...] = (),
) -> DomainAnalysisResult:
    entry = ruleset.entry(request.domain)
    return with_hash(
        analysis_id=request.analysis_id,
        domain=request.domain,
        parent_domain=entry.parent,
        support=entry.support,
        status=status,
        reasons=reasons,
        facts=(),
        rules=rules,
        policy_flags=policy,
        versions=versions,
        inputs=inputs,
    )


def evaluate_domain(
    ruleset: DomainRuleset,
    request: DomainAnalysisRequest,
    facts: ChartFacts,
    *,
    knowledge_version: str,
    varga: VargaPlacements | None = None,
    dasha: DashaEvidence | None = None,
    transit: TransitEvidence | None = None,
    phase6_results: Mapping[str, str] | None = None,
) -> DomainAnalysisResult:
    """Evaluate one domain for one chart. Never raises for an expected condition."""
    versions = DomainVersions(
        knowledge_version=knowledge_version,
        methodology_version=ruleset.manifest.methodology_version,
        ruleset_id=ruleset.manifest.ruleset_id,
        ruleset_version=ruleset.manifest.ruleset_version,
        ruleset_hash=ruleset.content_hash,
        evaluator_version=EVALUATOR_VERSION,
    )
    inputs = DomainInputs(
        varga_available=varga is not None,
        dasha_available=dasha is not None,
        transit_available=transit is not None,
        phase6_results_available=phase6_results is not None,
        varga_facts_hash=varga.facts_hash if varga is not None else None,
        dasha_facts_hash=dasha.facts_hash if dasha is not None else None,
        transit_facts_hash=transit.facts_hash if transit is not None else None,
        phase6_bundle_ref=request.chart_bundle_ref,
    )
    entry = ruleset.entry(request.domain)
    policy = ruleset.effective_policy(request.domain)
    common = {"request": request, "ruleset": ruleset, "versions": versions, "inputs": inputs}

    # 0. version pins (the caller can require the exact methodology)
    if (
        request.expected_knowledge_version is not None
        and request.expected_knowledge_version != knowledge_version
    ):
        return _empty(
            **common,  # type: ignore[arg-type]
            status=DomainStatus.NOT_EVALUABLE,
            reasons=(DomainReasonRecord(code=DomainReason.KNOWLEDGE_VERSION_MISMATCH),),
            policy=policy,
        )
    if (
        request.expected_ruleset_hash is not None
        and request.expected_ruleset_hash != ruleset.content_hash
    ):
        return _empty(
            **common,  # type: ignore[arg-type]
            status=DomainStatus.NOT_EVALUABLE,
            reasons=(DomainReasonRecord(code=DomainReason.RULESET_VERSION_MISMATCH),),
            policy=policy,
        )

    # 1. policy gates come before any methodology
    if entry.blocked_reason is not None:
        return _empty(
            **common,  # type: ignore[arg-type]
            status=DomainStatus.POLICY_BLOCKED,
            reasons=(DomainReasonRecord(code=entry.blocked_reason),),
            policy=policy,
        )
    if ruleset.adult_confirmation_required(request.domain) and (
        request.subject_adult_confirmed is not True
    ):
        return _empty(
            **common,  # type: ignore[arg-type]
            status=DomainStatus.POLICY_BLOCKED,
            reasons=(DomainReasonRecord(code=DomainReason.ADULT_CONFIRMATION_REQUIRED),),
            policy=policy,
        )

    # 2. a domain with no approved methodology is NOT_EVALUABLE, never a generic reading
    rules = ruleset.rules_for(request.domain)
    if entry.support is DomainSupport.NOT_EVALUABLE or not rules:
        return _empty(
            **common,  # type: ignore[arg-type]
            status=DomainStatus.NOT_EVALUABLE,
            reasons=(
                DomainReasonRecord(code=entry.not_evaluable_reason or DomainReason.NO_SOURCE_READ),
            ),
            policy=policy,
        )

    facts_out: list[DomainFact] = []
    results: list[DomainRuleResult] = []
    for rule in sorted(rules, key=lambda r: r.rule_id):
        params = rule.params
        try:
            if isinstance(params, HouseParams):
                fact, result = _house_rule(rule, params, facts)
            elif isinstance(params, KarakaParams):
                fact, result = _karaka_rule(rule, params, facts)
            elif isinstance(params, VargaParams):
                fact, result = _varga_rule(rule, params, facts, varga)
            elif isinstance(params, Phase6Params):
                results.append(_phase6_rule(rule, params, phase6_results))
                continue
            elif isinstance(params, MarriageDashaParams):
                fact, result = _marriage_dasha_rule(rule, params, facts, dasha, request.as_of_utc)
            elif isinstance(params, SubjectParams):
                fact, result = _subject_rule(rule, params, facts)
            else:
                assert isinstance(params, WithheldParams)
                results.append(_withheld_rule(rule, params))
                continue
        except _Insufficient as missing:
            results.append(
                _result(
                    rule,
                    DomainStatus.INSUFFICIENT_EVIDENCE,
                    reason=missing.reason,
                    detail=missing.detail,
                )
            )
            continue
        facts_out.append(fact)
        results.append(result)

    reasons = _reasons(results)
    statuses = {r.status for r in results}
    substantive = bool(facts_out) or bool(
        statuses & {DomainStatus.TRIGGERED, DomainStatus.NOT_TRIGGERED}
    )
    if substantive:
        status = DomainStatus.EVALUATED
    elif DomainStatus.CONFLICTING_EVIDENCE in statuses:
        status = DomainStatus.CONFLICTING_EVIDENCE
    elif DomainStatus.INSUFFICIENT_EVIDENCE in statuses:
        status = DomainStatus.INSUFFICIENT_EVIDENCE
    elif DomainStatus.POLICY_BLOCKED in statuses:
        status = DomainStatus.POLICY_BLOCKED
    else:
        status = DomainStatus.NOT_EVALUABLE
    if status in {DomainStatus.NOT_EVALUABLE, DomainStatus.POLICY_BLOCKED}:
        facts_out = []
    if not reasons and status is not DomainStatus.EVALUATED:
        reasons = (DomainReasonRecord(code=DomainReason.NO_SOURCE_READ),)
    return with_hash(
        analysis_id=request.analysis_id,
        domain=request.domain,
        parent_domain=entry.parent,
        support=entry.support,
        status=status,
        reasons=reasons,
        facts=tuple(sorted(facts_out, key=lambda f: f.fact_id)),
        rules=tuple(sorted(results, key=lambda r: r.rule_id)),
        policy_flags=policy,
        versions=versions,
        inputs=inputs,
    )


def _reasons(results: list[DomainRuleResult]) -> tuple[DomainReasonRecord, ...]:
    seen: dict[tuple[DomainReason, str | None], DomainReasonRecord] = {}
    for result in sorted(results, key=lambda r: r.rule_id):
        if result.reason is None:
            continue
        key = (result.reason, None)
        seen.setdefault(key, DomainReasonRecord(code=result.reason, detail=result.rule_id))
    return tuple(seen.values())
