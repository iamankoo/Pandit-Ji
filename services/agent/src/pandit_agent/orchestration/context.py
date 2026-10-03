"""Deterministic context assembly: tool results -> a typed ``AgentContext``.

The categories stay separate (facts, rule evaluations, statuses) and every record keeps the
semantic class, confidence, source profile and version it arrived with. Nothing is reclassified:
OBSERVED stays OBSERVED, DERIVED stays DERIVED, a rule evaluation is never a fact. Selection and
ordering are deterministic. When the evidence exceeds the budget it is **trimmed by priority and
the trim is recorded** (``trimmed_count``, an ``EVIDENCE_TRIMMED`` flag and a stated limitation),
never silently truncated. A duplicate evidence id or a record from another domain fails closed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from pandit_contracts.agent import (
    AgentContext,
    AgentErrorCode,
    AgentPlan,
    Domain,
    EvidenceCapability,
    EvidenceClass,
    EvidenceRecord,
    MissingCapability,
)
from pandit_contracts.llm import LLMLanguage

from pandit_agent.orchestration.errors import AgentFailure
from pandit_agent.orchestration.policy import DomainPolicy

CONTEXT_VERSION = "pj-context-1"

_RULE_PRIORITY = {"TRIGGERED": 0, "PARTIALLY_CANCELLED": 1, "NOT_EVALUABLE": 2}


def _rule_rank(record: EvidenceRecord) -> tuple[int, str]:
    return (_RULE_PRIORITY.get(record.status or "", 3), record.evidence_id)


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def assemble_context(
    *,
    request_id: str,
    plan: AgentPlan,
    language: LLMLanguage,
    policy: DomainPolicy,
    records: Iterable[EvidenceRecord],
    provided: frozenset[EvidenceCapability],
    max_items: int,
) -> AgentContext:
    domain: Domain = plan.domain
    unique: dict[str, EvidenceRecord] = {}
    for record in records:
        if record.domain is not domain:
            raise AgentFailure(
                AgentErrorCode.INTERNAL_ERROR, "evidence of another domain reached the context"
            )
        if record.evidence_id in unique:
            raise AgentFailure(
                AgentErrorCode.INTERNAL_ERROR, "duplicate evidence id in the assembled context"
            )
        unique[record.evidence_id] = record

    statuses = sorted(
        (r for r in unique.values() if r.evidence_class is EvidenceClass.CONTEXT_STATUS),
        key=lambda r: r.evidence_id,
    )
    rules = sorted(
        (r for r in unique.values() if r.evidence_class is EvidenceClass.RULE_EVALUATION),
        key=_rule_rank,
    )
    facts = sorted(
        (
            r
            for r in unique.values()
            if r.evidence_class
            in {
                EvidenceClass.OBSERVED_FACT,
                EvidenceClass.DERIVED_FACT,
                EvidenceClass.CALCULATED_FACT,
            }
        ),
        key=lambda r: r.evidence_id,
    )

    # Priority when trimming: every status; then rules in priority order (triggered first), each
    # kept *together with the facts it cites* (and those facts' own sources), so no kept rule ever
    # points at evidence that was dropped; then the remaining facts by id.
    facts_by_id = {r.evidence_id: r for r in facts}

    def closure(rule: EvidenceRecord) -> list[str]:
        needed: list[str] = []
        stack = list(rule.fact_refs)
        while stack:
            fact_id = stack.pop()
            if fact_id in facts_by_id and fact_id not in needed:
                needed.append(fact_id)
                stack.extend(facts_by_id[fact_id].fact_refs)
        return sorted(needed)

    kept: set[str] = set()
    kept_statuses = statuses[:max_items]
    kept.update(r.evidence_id for r in kept_statuses)
    kept_rule_ids: list[str] = []

    def add_rules(limit: int) -> None:
        for rule in rules:
            if rule.evidence_id in kept_rule_ids:
                continue
            group = {rule.evidence_id, *closure(rule)}
            if len(kept | group) <= limit:
                kept.update(group)
                kept_rule_ids.append(rule.evidence_id)

    # Split what is left between rules and facts so neither starves the other (astrology rules
    # cite no facts, so rules alone would crowd out the chart); unused share flows to the other.
    remaining = max_items - len(kept)
    add_rules(len(kept) + (remaining + 1) // 2)
    for fact in facts:
        if len(kept) < max_items:
            kept.add(fact.evidence_id)
    add_rules(max_items)
    kept_rules = [r for r in rules if r.evidence_id in kept_rule_ids]
    kept_facts = [r for r in facts if r.evidence_id in kept]
    trimmed = len(unique) - len(kept_statuses) - len(kept_rules) - len(kept_facts)

    required, desired = plan.required, plan.desired
    missing = tuple(
        MissingCapability(
            capability=cap,
            required=cap in required,
            reason="no tool provides this capability in the registry",
        )
        for cap in dict.fromkeys((*required, *desired))
        if cap not in provided
    )
    bundle_refs = tuple(sorted({r.bundle_ref for r in unique.values()}))
    version_refs = tuple(sorted({r.version_ref for r in unique.values() if r.version_ref}))
    body = {
        "context_version": CONTEXT_VERSION,
        "request_id": request_id,
        "domain": domain.value,
        "intent": plan.intent.value,
        "language": language.value,
        "facts": [r.model_dump(mode="json") for r in kept_facts],
        "rules": [r.model_dump(mode="json") for r in kept_rules],
        "statuses": [r.model_dump(mode="json") for r in kept_statuses],
        "missing": [m.model_dump(mode="json") for m in missing],
        "trimmed": trimmed,
        "restrictions": [c.value for c in policy.output_restrictions],
    }
    # The hash covers the evidence and policy, not the request id: two requests over the same
    # evidence share a context hash.
    hashable = {k: v for k, v in body.items() if k != "request_id"}
    digest = hashlib.sha256(_canonical(hashable).encode("utf-8")).hexdigest()
    return AgentContext(
        context_version=CONTEXT_VERSION,
        request_id=request_id,
        domain=domain,
        intent=plan.intent,
        language=language,
        facts=tuple(kept_facts),
        rule_evaluations=tuple(kept_rules),
        statuses=tuple(kept_statuses),
        missing=missing,
        trimmed_count=trimmed,
        restrictions=tuple(c.value for c in policy.output_restrictions),
        bundle_refs=bundle_refs,
        version_refs=version_refs,
        context_hash=digest,
    )


def all_records(context: AgentContext) -> tuple[EvidenceRecord, ...]:
    return (*context.statuses, *context.facts, *context.rule_evaluations)
