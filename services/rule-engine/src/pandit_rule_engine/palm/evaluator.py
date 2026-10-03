"""Evaluate the palm ruleset over a :class:`PalmFactSet` (Phase 13).

Facts flow one direction: the evaluator reads palm facts and produces
:class:`PalmRuleEvaluation` records (INTERPRETED layer). It never reads pixels, never calls a
model, never produces prose and never changes a fact.

Status of a rule, deterministically:

* ``NOT_EVALUABLE`` when a required fact is absent or is itself ``NOT_EVALUABLE`` (for example
  every line-role fact while no role assignment is validated): the reason names the fact;
* ``NOT_TRIGGERED`` when the facts are evaluable but the conditions do not hold;
* ``TRIGGERED`` when every requirement is matched; ``fact_refs`` lists the matching facts and
  ``interpretation_tags`` the rule's tags.

Rules of different source profiles are evaluated independently: two profiles may both trigger on
the same facts, and the recorded conflict ids travel with each evaluation. No winner is chosen
and no tags are merged.
"""

from __future__ import annotations

from collections.abc import Sequence

from pandit_contracts.palm import (
    PalmFact,
    PalmFactSet,
    PalmRuleEvaluation,
    RuleStatus,
    VisibilityState,
)

from pandit_rule_engine.palm.loader import PalmRuleset
from pandit_rule_engine.palm.schema import PalmRule, Requirement


def _matches(fact: PalmFact, req: Requirement) -> bool:
    if req.hand_side is not None and fact.hand_side.value != req.hand_side:
        return False
    if req.labelling_profile is not None and (
        fact.labelling is None or fact.labelling.source_profile != req.labelling_profile
    ):
        return False
    if req.value_kind is not None and (
        fact.value.kind != req.value_kind or fact.value.v != req.value_equals
    ):
        return False
    return True


def _requirement_state(
    facts: Sequence[PalmFact], req: Requirement
) -> tuple[str, PalmFact | None, str | None]:
    """("MATCH" | "NO_MATCH" | "NOT_EVALUABLE", the matching fact, the reason)."""
    candidates = [
        f
        for f in facts
        if f.fact_type.value == req.fact_type
        and (req.region_id is None or f.region_id == req.region_id)
    ]
    where = f"{req.fact_type}/{req.region_id or '*'}"
    if not candidates:
        return "NOT_EVALUABLE", None, f"REQUIRED_FACT_ABSENT:{where}"
    evaluable = [f for f in candidates if f.visibility.state is not VisibilityState.NOT_EVALUABLE]
    if not evaluable:
        reason = candidates[0].visibility.reason or "UNKNOWN"
        return "NOT_EVALUABLE", None, f"REQUIRED_FACT_NOT_EVALUABLE:{where}:{reason}"
    matched = sorted((f for f in evaluable if _matches(f, req)), key=lambda f: f.fact_id)
    if not matched:
        return "NO_MATCH", None, None
    return "MATCH", matched[0], None


def evaluate_rule(
    rule: PalmRule, fact_set: PalmFactSet, knowledge_version: str, ruleset: PalmRuleset
) -> PalmRuleEvaluation:
    refs: list[str] = []
    not_evaluable: str | None = None
    no_match = False
    for req in rule.requires:
        state, fact, reason = _requirement_state(fact_set.facts, req)
        if state == "NOT_EVALUABLE" and not_evaluable is None:
            not_evaluable = reason
        elif state == "NO_MATCH":
            no_match = True
        elif fact is not None:
            refs.append(fact.fact_id)
    status = RuleStatus.TRIGGERED
    status_reason: str | None = None
    tags: tuple[str, ...] = tuple(sorted(rule.interpretation_tags))
    cited: tuple[str, ...] = tuple(sorted(set(refs)))
    if not_evaluable is not None:
        status, status_reason, tags, cited = RuleStatus.NOT_EVALUABLE, not_evaluable, (), ()
    elif no_match:
        status, status_reason, tags, cited = RuleStatus.NOT_TRIGGERED, "CONDITIONS_NOT_MET", (), ()
    return PalmRuleEvaluation(
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        source_profile=rule.source_profile,
        source_location=rule.source_location,
        status=status,
        fact_refs=cited,
        knowledge_version=knowledge_version,
        ruleset_id=ruleset.ruleset_id,
        source_id=rule.source_id,
        standards_version=ruleset.manifest.standards_version,
        interpretation_tags=tags,
        reason=status_reason,
        conflict_ids=tuple(sorted(rule.known_conflicts)),
    )


def evaluate_palm_rules(
    ruleset: PalmRuleset, fact_set: PalmFactSet, knowledge_version: str
) -> tuple[PalmRuleEvaluation, ...]:
    """Every rule, in rule-id order, evaluated independently (no merging, no winner)."""
    return tuple(
        evaluate_rule(rule, fact_set, knowledge_version, ruleset)
        for rule in (ruleset.rules[k] for k in sorted(ruleset.rules))
    )
