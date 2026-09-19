"""Condition evaluator (Phase 6C): three-valued (Kleene) evaluation of the
typed condition language over chart facts.

Every condition evaluates to `True`, `False` or *unknown with a structured
reason*. Unknown is never turned into false: `all` is false if any argument
is false, otherwise unknown if any is unknown; `any` is true if any is true,
otherwise unknown if any is unknown; `not` keeps unknown as unknown. This is
what lets a rule return `NOT_EVALUABLE(reason)` instead of guessing.

Sets whose membership is uncertain (nodes when the source is silent, a
Mercury or Moon whose natural nature cannot be fixed, a planet missing from
the chart) are handled by evaluating the quantified condition under every
possible membership and comparing: equal results stand, different results
are unknown with the reason of the uncertain member.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from itertools import product
from typing import Protocol

from pandit_rule_engine.facts import ChartFacts, PlanetFact
from pandit_rule_engine.schema import (
    IT,
    OUTER,
    AllOf,
    AnyOf,
    AspectedBy,
    Condition,
    CountAtLeast,
    DistinctSigns,
    Exists,
    ForAll,
    NaturalNature,
    Not,
    PlanetDignity,
    PlanetFlag,
    PlanetHouse,
    PlanetModality,
    PlanetMoolatrikona,
    PlanetSet,
    RuleResultIs,
    SameSign,
    SignLordRelation,
)
from pandit_rule_engine.vocab import (
    ALL_BODIES,
    CLASSICAL_BODIES,
    NODES,
    SIGN_MODALITY,
    Body,
    Reason,
    Sign,
    Status,
    house_from,
)

#: Houses from an aspecting planet on which BPHS Ch. 26 v. 2-5 gives a
#: partial (1/4, 1/2, 3/4) aspect; a partial aspect can exist only there.
PARTIAL_ASPECT_OFFSETS = frozenset({3, 4, 5, 8, 9, 10})

# --------------------------------------------------------------------------
# Three-valued result
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Tri:
    """True, False, or unknown (`value is None`) with a structured reason."""

    value: bool | None
    reason: Reason | None = None
    detail: str | None = None

    @property
    def unknown(self) -> bool:
        return self.value is None


TRUE = Tri(True)
FALSE = Tri(False)


def unknown(reason: Reason, detail: str | None = None) -> Tri:
    return Tri(None, reason, detail)


def tri_all(items: list[Tri]) -> Tri:
    if any(item.value is False for item in items):
        return FALSE
    first_unknown = next((item for item in items if item.unknown), None)
    return first_unknown if first_unknown is not None else TRUE


def tri_any(items: list[Tri]) -> Tri:
    if any(item.value is True for item in items):
        return TRUE
    first_unknown = next((item for item in items if item.unknown), None)
    return first_unknown if first_unknown is not None else FALSE


def tri_not(item: Tri) -> Tri:
    if item.value is None:
        return item
    return FALSE if item.value else TRUE


# --------------------------------------------------------------------------
# Derived facts interface (implemented in `derived.py`)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class NatureValue:
    """Natural benefic/malefic of a body: `benefic`, `malefic`, or a value
    that cannot be fixed (`mixed`, `boundary`, `unavailable`) with a reason."""

    value: str
    reason: Reason | None = None
    detail: str | None = None


@dataclass(frozen=True)
class RelationValue:
    """Relationship between two bodies, or why it cannot be evaluated."""

    kind: str | None
    reason: Reason | None = None
    detail: str | None = None


@dataclass(frozen=True)
class MoolatrikonaValue:
    """Whether a planet is in its Moolatrikona, or why that is unavailable."""

    value: bool | None
    reason: Reason | None = None
    detail: str | None = None


class DerivedFacts(Protocol):
    def natural_nature(self, body: Body) -> NatureValue: ...

    def moolatrikona(self, body: Body) -> MoolatrikonaValue: ...

    def relationship(self, basis: str, a: Body, b: Body) -> RelationValue: ...


# --------------------------------------------------------------------------
# Context
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleOutcome:
    """The outcome of an already-evaluated rule, readable through
    `rule_result` conditions."""

    status: Status
    reason: Reason | None = None
    detail: str | None = None


@dataclass
class EvalContext:
    facts: ChartFacts
    derived: DerivedFacts
    rule_results: Mapping[str, RuleOutcome] = field(default_factory=dict)
    binding: Body | None = None
    outer: Body | None = None
    recording: bool = True
    evidence: list[str] = field(default_factory=list)

    def note(self, message: str) -> None:
        if self.recording:
            self.evidence.append(message)

    def scratch(self) -> EvalContext:
        """A copy that records nothing (used when comparing memberships)."""
        return EvalContext(
            facts=self.facts,
            derived=self.derived,
            rule_results=self.rule_results,
            binding=self.binding,
            outer=self.outer,
            recording=False,
        )


# --------------------------------------------------------------------------
# Planet resolution
# --------------------------------------------------------------------------


def _resolve(ctx: EvalContext, name: str) -> Body | None:
    if name == IT:
        return ctx.binding
    if name == OUTER:
        return ctx.outer
    return Body(name)


def _fact(ctx: EvalContext, body: Body | None) -> tuple[PlanetFact | None, Tri | None]:
    if body is None:
        return None, unknown(Reason.MISSING_DEPENDENCY, "binding.unbound")
    planet = ctx.facts.planet(body)
    if planet is None:
        return None, unknown(Reason.MISSING_DEPENDENCY, f"planet.{body.value}")
    return planet, None


def _base_sign(ctx: EvalContext, reference: str) -> tuple[Sign | None, Tri | None]:
    if reference == "lagna":
        return ctx.facts.lagna_sign, None
    planet, problem = _fact(ctx, _resolve(ctx, reference))
    if planet is None:
        return None, problem
    return planet.sign, None


# --------------------------------------------------------------------------
# Membership uncertainty
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Group:
    """A set of bodies whose membership in a set is uncertain together."""

    reason: Reason
    detail: str
    bodies: tuple[Body, ...]


def _members(ctx: EvalContext, over: PlanetSet) -> tuple[list[Body], list[_Group]]:
    """Definite members and uncertain groups of a `PlanetSet`."""
    definite: list[Body] = []
    groups: list[_Group] = []
    nodes_pending = False
    if over.bodies is not None:
        candidates: tuple[Body, ...] = over.bodies
    elif over.nature is not None:
        candidates = ALL_BODIES
    else:
        candidates = CLASSICAL_BODIES + NODES
    for body in candidates:
        if body in over.exclude:
            continue
        if over.bodies is None and body in NODES:
            # Node participation follows the set's node policy; a benefic-only
            # selection never contains nodes (Ch. 3 v. 11 lists them malefic).
            if over.nature == "benefic":
                continue
            if over.nodes == "excluded":
                continue
            if over.nodes == "unspecified":
                nodes_pending = True
                continue
        if ctx.facts.planet(body) is None:
            groups.append(_Group(Reason.MISSING_DEPENDENCY, f"planet.{body.value}", (body,)))
            continue
        if over.nature is not None and body not in NODES:
            nature = ctx.derived.natural_nature(body)
            if nature.value == over.nature:
                definite.append(body)
            elif nature.value in ("benefic", "malefic"):
                continue
            else:
                reason = nature.reason or Reason.READING_AMBIGUOUS
                groups.append(_Group(reason, nature.detail or f"nature.{body.value}", (body,)))
            continue
        definite.append(body)
    if nodes_pending:
        present = tuple(node for node in NODES if ctx.facts.planet(node) is not None)
        if present:
            groups.insert(0, _Group(Reason.NODE_PARTICIPATION_UNSPECIFIED, "nodes", present))
    return definite, groups


def _with_membership(
    ctx: EvalContext,
    over: PlanetSet,
    evaluate: Callable[[EvalContext, list[Body]], Tri],
) -> Tri:
    """Evaluate `evaluate` over the set under every possible membership."""
    definite, groups = _members(ctx, over)
    baseline = evaluate(ctx, definite)
    if not groups:
        return baseline
    scratch = ctx.scratch()
    results: list[Tri] = []
    for choice in product((False, True), repeat=len(groups)):
        members = list(definite)
        for include, group in zip(choice, groups, strict=True):
            if include:
                members.extend(group.bodies)
        results.append(evaluate(scratch, members))
    if all(_same(results[0], other) for other in results[1:]):
        return baseline if _same(baseline, results[0]) else results[0]
    # Different memberships give different answers: report the first group
    # whose inclusion alone changes the all-excluded outcome.
    excluded = results[0]
    for group in groups:
        members = list(definite) + list(group.bodies)
        if not _same(evaluate(scratch, members), excluded):
            return unknown(group.reason, group.detail)
    return unknown(Reason.READING_AMBIGUOUS, "membership")


def _same(a: Tri, b: Tri) -> bool:
    return a.value == b.value and (a.value is not None or a.reason == b.reason)


# --------------------------------------------------------------------------
# Atoms
# --------------------------------------------------------------------------


def _planet_house(ctx: EvalContext, cond: PlanetHouse) -> Tri:
    planet, problem = _fact(ctx, _resolve(ctx, cond.planet))
    if planet is None:
        assert problem is not None
        return problem
    base, problem = _base_sign(ctx, cond.reference)
    if base is None:
        assert problem is not None
        return problem
    house = house_from(base, planet.sign)
    ctx.note(f"planet_house({planet.body.value} from {cond.reference}) = {house}")
    return TRUE if house in cond.houses else FALSE


def _planet_dignity(ctx: EvalContext, cond: PlanetDignity) -> Tri:
    planet, problem = _fact(ctx, _resolve(ctx, cond.planet))
    if planet is None:
        assert problem is not None
        return problem
    if planet.dignity is None:
        return unknown(Reason.NOT_SPECIFIED_BY_SOURCE, f"dignity.{planet.body.value}")
    ctx.note(f"planet_dignity({planet.body.value}) = {planet.dignity.value}")
    return TRUE if planet.dignity in cond.in_ else FALSE


def _planet_flag(ctx: EvalContext, cond: PlanetFlag) -> Tri:
    planet, problem = _fact(ctx, _resolve(ctx, cond.planet))
    if planet is None:
        assert problem is not None
        return problem
    if cond.flag == "retrograde":
        actual: bool | None = planet.retrograde
    elif planet.combust is None:
        # The standards state the Sun is never combust; the nodes are not
        # evaluated for combustion (docs/ASTROLOGY_STANDARDS.md §Combustion).
        if planet.body is Body.SUN:
            actual = False
        else:
            return unknown(Reason.NOT_SPECIFIED_BY_SOURCE, f"combust.{planet.body.value}")
    else:
        actual = planet.combust
    ctx.note(f"planet_flag({planet.body.value}.{cond.flag}) = {actual}")
    return TRUE if actual == cond.value else FALSE


def _planet_modality(ctx: EvalContext, cond: PlanetModality) -> Tri:
    planet, problem = _fact(ctx, _resolve(ctx, cond.planet))
    if planet is None:
        assert problem is not None
        return problem
    modality = SIGN_MODALITY[planet.sign]
    ctx.note(f"planet_modality({planet.body.value}) = {modality.value}")
    return TRUE if modality in cond.in_ else FALSE


def _planet_moolatrikona(ctx: EvalContext, cond: PlanetMoolatrikona) -> Tri:
    body = _resolve(ctx, cond.planet)
    if body is None:
        return unknown(Reason.MISSING_DEPENDENCY, "binding.unbound")
    fact = ctx.derived.moolatrikona(body)
    if fact.value is None:
        return unknown(fact.reason or Reason.REQUIRES_MOOLATRIKONA, fact.detail)
    ctx.note(f"planet_moolatrikona({body.value}) = {fact.value}")
    return TRUE if fact.value == cond.value else FALSE


def _same_sign(ctx: EvalContext, cond: SameSign) -> Tri:
    first, problem = _fact(ctx, _resolve(ctx, cond.a))
    if first is None:
        assert problem is not None
        return problem
    second, problem = _fact(ctx, _resolve(ctx, cond.b))
    if second is None:
        assert problem is not None
        return problem
    if first.body is second.body:
        return FALSE
    ctx.note(f"same_sign({first.body.value},{second.body.value}) = {first.sign is second.sign}")
    return TRUE if first.sign is second.sign else FALSE


def _aspected_by(ctx: EvalContext, cond: AspectedBy) -> Tri:
    target, problem = _fact(ctx, _resolve(ctx, cond.planet))
    if target is None:
        assert problem is not None
        return problem
    source, problem = _fact(ctx, _resolve(ctx, cond.by))
    if source is None:
        assert problem is not None
        return problem
    if source.body is target.body:
        return FALSE
    if target.house in source.aspected_houses:
        ctx.note(f"aspected_by({target.body.value} by {source.body.value}) = full-sign aspect")
        return TRUE
    # Absence of a full-sign aspect does not prove absence of a partial
    # aspect: BPHS Ch. 26 v. 2-5 gives quarter, half and three-quarter aspects
    # on the 3rd/10th, 5th/9th and 4th/8th from the aspecting planet, and
    # partial drishti is a Phase 9 dependency. From any other house there is
    # no aspect at all (the 7th is always a full aspect), so the answer is
    # definitely false there.
    offset = house_from(source.sign, target.sign)
    if offset in PARTIAL_ASPECT_OFFSETS:
        return unknown(Reason.REQUIRES_PARTIAL_DRISHTI, f"{source.body.value}->{target.body.value}")
    ctx.note(
        f"aspected_by({target.body.value} by {source.body.value}) = no aspect (offset {offset})"
    )
    return FALSE


def _natural_nature(ctx: EvalContext, cond: NaturalNature) -> Tri:
    body = _resolve(ctx, cond.planet)
    if body is None:
        return unknown(Reason.MISSING_DEPENDENCY, "binding.unbound")
    nature = ctx.derived.natural_nature(body)
    if nature.value in ("benefic", "malefic"):
        ctx.note(f"natural_nature({body.value}) = {nature.value}")
        return TRUE if nature.value == cond.is_ else FALSE
    return unknown(nature.reason or Reason.READING_AMBIGUOUS, nature.detail)


def _sign_lord_relation(ctx: EvalContext, cond: SignLordRelation) -> Tri:
    planet, problem = _fact(ctx, _resolve(ctx, cond.planet))
    if planet is None:
        assert problem is not None
        return problem
    lord = ctx.facts.sign_lords.get(planet.sign)
    if lord is None:
        return unknown(Reason.MISSING_DEPENDENCY, f"sign_lord.{planet.sign.value}")
    if lord is planet.body:
        return FALSE
    relation = ctx.derived.relationship(cond.basis, planet.body, lord)
    if relation.kind is None:
        return unknown(relation.reason or Reason.NOT_SPECIFIED_BY_SOURCE, relation.detail)
    ctx.note(f"sign_lord_relation({planet.body.value} in {planet.sign.value}) = {relation.kind}")
    return TRUE if relation.kind in cond.kinds else FALSE


def _distinct_signs(ctx: EvalContext, cond: DistinctSigns) -> Tri:
    def evaluate(inner: EvalContext, members: list[Body]) -> Tri:
        signs: set[Sign] = set()
        for body in members:
            planet = inner.facts.planet(body)
            if planet is None:
                return unknown(Reason.MISSING_DEPENDENCY, f"planet.{body.value}")
            signs.add(planet.sign)
        inner.note(f"distinct_signs = {len(signs)}")
        return TRUE if len(signs) == cond.count else FALSE

    return _with_membership(ctx, cond.over, evaluate)


def _rule_result(ctx: EvalContext, cond: RuleResultIs) -> Tri:
    outcome = ctx.rule_results.get(cond.rule_id)
    if outcome is None:
        return unknown(Reason.MISSING_DEPENDENCY, f"rule.{cond.rule_id}")
    if outcome.status in cond.in_:
        ctx.note(f"rule_result({cond.rule_id}) = {outcome.status.value}")
        return TRUE
    if outcome.status is Status.NOT_EVALUABLE:
        return unknown(outcome.reason or Reason.READING_AMBIGUOUS, f"rule.{cond.rule_id}")
    return FALSE


def _quantified(
    ctx: EvalContext,
    over: PlanetSet,
    where: Condition,
    combine: Callable[[list[Tri]], Tri],
) -> Tri:
    def evaluate(inner: EvalContext, members: list[Body]) -> Tri:
        results: list[Tri] = []
        previous, previous_outer = inner.binding, inner.outer
        for body in members:
            inner.outer, inner.binding = previous, body
            results.append(evaluate_condition(inner, where))
        inner.binding, inner.outer = previous, previous_outer
        return combine(results)

    return _with_membership(ctx, over, evaluate)


def _count(ctx: EvalContext, cond: CountAtLeast) -> Tri:
    def combine(results: list[Tri]) -> Tri:
        true_count = sum(1 for item in results if item.value is True)
        unknown_items = [item for item in results if item.unknown]
        if true_count >= cond.at_least:
            return TRUE
        if true_count + len(unknown_items) >= cond.at_least:
            return unknown_items[0]
        return FALSE

    def evaluate(inner: EvalContext, members: list[Body]) -> Tri:
        results: list[Tri] = []
        previous, previous_outer = inner.binding, inner.outer
        for body in members:
            inner.outer, inner.binding = previous, body
            results.append(evaluate_condition(inner, cond.where))
        inner.binding, inner.outer = previous, previous_outer
        result = combine(results)
        inner.note(f"count = {sum(1 for item in results if item.value is True)}")
        return result

    return _with_membership(ctx, cond.over, evaluate)


def evaluate_condition(ctx: EvalContext, condition: Condition) -> Tri:
    """Evaluate one typed condition to a three-valued result."""
    if isinstance(condition, AllOf):
        return tri_all([evaluate_condition(ctx, arg) for arg in condition.args])
    if isinstance(condition, AnyOf):
        return tri_any([evaluate_condition(ctx, arg) for arg in condition.args])
    if isinstance(condition, Not):
        return tri_not(evaluate_condition(ctx, condition.arg))
    if isinstance(condition, PlanetHouse):
        return _planet_house(ctx, condition)
    if isinstance(condition, PlanetDignity):
        return _planet_dignity(ctx, condition)
    if isinstance(condition, PlanetFlag):
        return _planet_flag(ctx, condition)
    if isinstance(condition, PlanetModality):
        return _planet_modality(ctx, condition)
    if isinstance(condition, PlanetMoolatrikona):
        return _planet_moolatrikona(ctx, condition)
    if isinstance(condition, SameSign):
        return _same_sign(ctx, condition)
    if isinstance(condition, AspectedBy):
        return _aspected_by(ctx, condition)
    if isinstance(condition, NaturalNature):
        return _natural_nature(ctx, condition)
    if isinstance(condition, SignLordRelation):
        return _sign_lord_relation(ctx, condition)
    if isinstance(condition, DistinctSigns):
        return _distinct_signs(ctx, condition)
    if isinstance(condition, RuleResultIs):
        return _rule_result(ctx, condition)
    if isinstance(condition, Exists):
        return _quantified(ctx, condition.over, condition.where, tri_any)
    if isinstance(condition, ForAll):
        return _quantified(ctx, condition.over, condition.where, tri_all)
    return _count(ctx, condition)
