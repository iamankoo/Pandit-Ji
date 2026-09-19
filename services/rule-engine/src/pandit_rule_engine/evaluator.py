"""Rule evaluator (Phase 6C/6D): reading evaluation, cancellations,
dependencies and the ambiguity-preserving rule-level result.

Per reading: evaluate the conditions; if detected, evaluate exceptions and
cancellations (unknown ones make the reading `NOT_EVALUABLE`, never
"not cancelled"); then apply unresolved dependencies declared
`not_evaluable_if_detected`. Per rule: if every reading gives the same
status and reason, that common result is returned with every reading kept;
otherwise the result is `NOT_EVALUABLE(reading_ambiguous)`. Priority is never
consulted here -- it only orders evaluation (see `loader.Ruleset`).
"""

from __future__ import annotations

from collections.abc import Sequence

from pandit_rule_engine.conditions import (
    DerivedFacts,
    EvalContext,
    RuleOutcome,
    Tri,
    evaluate_condition,
    tri_all,
)
from pandit_rule_engine.facts import ChartFacts
from pandit_rule_engine.loader import Ruleset
from pandit_rule_engine.results import Provenance, ReadingResult, RuleResult
from pandit_rule_engine.schema import Reading, Rule
from pandit_rule_engine.vocab import Reason, Status


def _detection(ctx: EvalContext, rule: Rule, reading: Reading) -> Tri:
    parts = [evaluate_condition(ctx, reading.conditions)]
    if rule.conditions is not None:
        parts.insert(0, evaluate_condition(ctx, rule.conditions))
    return tri_all(parts)


def _not_evaluable(
    reading: Reading,
    rule: Rule,
    tri: Tri,
    detected: Status,
    evidence: Sequence[str],
) -> ReadingResult:
    return ReadingResult(
        reading_id=reading.reading_id,
        source_id=reading.source_id or rule.source_id,
        status=Status.NOT_EVALUABLE,
        reason=tri.reason or Reason.READING_AMBIGUOUS,
        detail=tri.detail,
        detected_status=detected,
        evidence=tuple(evidence),
    )


def evaluate_reading(ctx: EvalContext, rule: Rule, reading: Reading) -> ReadingResult:
    """Evaluate one reading of `rule` against the context's facts."""
    ctx.evidence = []
    source_id = reading.source_id or rule.source_id
    detection = _detection(ctx, rule, reading)
    if detection.value is None:
        return _not_evaluable(reading, rule, detection, Status.NOT_EVALUABLE, ctx.evidence)
    if detection.value is False:
        return ReadingResult(
            reading_id=reading.reading_id,
            source_id=source_id,
            status=Status.NOT_TRIGGERED,
            detected_status=Status.NOT_TRIGGERED,
            evidence=tuple(ctx.evidence),
        )

    exceptions_applied: list[str] = []
    for exception in rule.exceptions:
        outcome = evaluate_condition(ctx, exception.when)
        if outcome.value is None:
            return _not_evaluable(reading, rule, outcome, Status.TRIGGERED, ctx.evidence)
        if outcome.value:
            exceptions_applied.append(exception.exception_id)
    if exceptions_applied:
        return ReadingResult(
            reading_id=reading.reading_id,
            source_id=source_id,
            status=Status.NOT_TRIGGERED,
            detected_status=Status.TRIGGERED,
            exceptions_applied=tuple(exceptions_applied),
            evidence=tuple(ctx.evidence),
        )

    full: list[str] = []
    partial: list[str] = []
    first_unknown: Tri | None = None
    for cancellation in rule.cancellations:
        outcome = evaluate_condition(ctx, cancellation.when)
        if outcome.value is None:
            first_unknown = first_unknown or outcome
        elif outcome.value:
            (full if cancellation.effect == "full" else partial).append(
                cancellation.cancellation_id
            )
    if full:
        status = Status.CANCELLED
    elif first_unknown is not None:
        return _not_evaluable(reading, rule, first_unknown, Status.TRIGGERED, ctx.evidence)
    elif partial:
        status = Status.PARTIALLY_CANCELLED
    else:
        status = Status.TRIGGERED

    if status in (Status.TRIGGERED, Status.PARTIALLY_CANCELLED):
        blocking = [
            dependency
            for dependency in rule.dependencies
            if dependency.unresolved_effect == "not_evaluable_if_detected"
        ]
        if blocking:
            first = blocking[0]
            return ReadingResult(
                reading_id=reading.reading_id,
                source_id=source_id,
                status=Status.NOT_EVALUABLE,
                reason=first.reason,
                detail=first.dependency_id,
                detected_status=Status.TRIGGERED,
                cancellations_applied=tuple(full + partial),
                unresolved_dependencies=tuple(dep.dependency_id for dep in blocking),
                evidence=tuple(ctx.evidence),
            )
    return ReadingResult(
        reading_id=reading.reading_id,
        source_id=source_id,
        status=status,
        detected_status=Status.TRIGGERED,
        cancellations_applied=tuple(full + partial),
        evidence=tuple(ctx.evidence),
    )


def evaluate_rule(ctx: EvalContext, rule: Rule) -> RuleResult:
    """Evaluate every reading of `rule` and combine them without choosing one."""
    readings = tuple(evaluate_reading(ctx, rule, reading) for reading in rule.readings)
    first = readings[0]
    agree = all(
        reading.status is first.status and reading.reason == first.reason
        for reading in readings[1:]
    )
    if agree:
        status, reason, detail = first.status, first.reason, first.detail
    else:
        status, reason, detail = Status.NOT_EVALUABLE, Reason.READING_AMBIGUOUS, rule.rule_id
    tags = (
        rule.interpretation_tags
        if status in (Status.TRIGGERED, Status.PARTIALLY_CANCELLED)
        else None
    )
    return RuleResult(
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        profile=rule.profile,
        standards_version=rule.standards_version,
        status=status,
        reason=reason,
        detail=detail,
        readings_agree=agree,
        readings=readings,
        provenance=Provenance.of(rule),
        priority=rule.priority,
        conflict_group=rule.conflict_group,
        ambiguity_group=rule.ambiguity_group,
        interpretation_tags=tags,
    )


def outcome_of(result: RuleResult) -> RuleOutcome:
    return RuleOutcome(status=result.status, reason=result.reason, detail=result.detail)


def evaluate_ruleset(
    ruleset: Ruleset, facts: ChartFacts, derived: DerivedFacts
) -> tuple[RuleResult, ...]:
    """Evaluate every active rule in the ruleset's deterministic order.

    Results of earlier rules are visible to later rules through
    `rule_result` conditions (the loader orders rules after their
    dependencies). Only `evaluation_order` is influenced by `priority`.
    """
    outcomes: dict[str, RuleOutcome] = {}
    results: list[RuleResult] = []
    for rule_id in ruleset.evaluation_order:
        context = EvalContext(facts=facts, derived=derived, rule_results=outcomes)
        result = evaluate_rule(context, ruleset.rules[rule_id])
        outcomes[rule_id] = outcome_of(result)
        results.append(result)
    return tuple(results)
