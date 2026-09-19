"""Result model (Phase 6D): runtime statuses, reason codes and provenance.

Statuses are `TRIGGERED`, `NOT_TRIGGERED`, `CANCELLED`, `PARTIALLY_CANCELLED`
and `NOT_EVALUABLE`. A `NOT_EVALUABLE` result always carries a structured
`Reason`; a rule whose readings disagree is
`NOT_EVALUABLE(reading_ambiguous)` and keeps every reading's own outcome.
Source conflicts stay provenance/profile metadata (`conflict_group`), not a
separate runtime status.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from pandit_rule_engine.schema import InterpretationTags, Rule
from pandit_rule_engine.vocab import Reason, Status


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Provenance(_Model):
    """Where a rule comes from; copied into every result."""

    source: str
    source_id: str
    source_edition: str
    translator: str | None
    source_location: str
    source_version: str
    source_tier: int
    verification_level: str
    confidence: str

    @classmethod
    def of(cls, rule: Rule) -> Provenance:
        return cls(
            source=rule.source,
            source_id=rule.source_id,
            source_edition=rule.source_edition,
            translator=rule.translator,
            source_location=rule.source_location,
            source_version=rule.source_version,
            source_tier=rule.source_tier,
            verification_level=rule.verification_level,
            confidence=rule.confidence,
        )


class ReadingResult(_Model):
    reading_id: str
    source_id: str
    status: Status
    reason: Reason | None = None
    detail: str | None = None
    #: Outcome of the readings' conditions alone, before exceptions,
    #: cancellations and unresolved dependencies (`NOT_EVALUABLE` if the
    #: conditions themselves could not be evaluated).
    detected_status: Status
    cancellations_applied: tuple[str, ...] = ()
    exceptions_applied: tuple[str, ...] = ()
    unresolved_dependencies: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _reason_iff_not_evaluable(self) -> ReadingResult:
        if (self.status is Status.NOT_EVALUABLE) != (self.reason is not None):
            raise ValueError("a reason is required exactly when status is NOT_EVALUABLE")
        return self


class RuleResult(_Model):
    rule_id: str
    rule_version: str
    profile: str
    standards_version: str
    status: Status
    reason: Reason | None = None
    detail: str | None = None
    #: False when the readings disagree (status is then
    #: `NOT_EVALUABLE(reading_ambiguous)`).
    readings_agree: bool
    readings: tuple[ReadingResult, ...]
    provenance: Provenance
    priority: int
    conflict_group: str | None = None
    ambiguity_group: str | None = None
    #: Applied only when the rule is TRIGGERED or PARTIALLY_CANCELLED, so a
    #: consumer cannot attach a signification to a result that did not obtain.
    interpretation_tags: InterpretationTags | None = None

    @model_validator(mode="after")
    def _reason_iff_not_evaluable(self) -> RuleResult:
        if (self.status is Status.NOT_EVALUABLE) != (self.reason is not None):
            raise ValueError("a reason is required exactly when status is NOT_EVALUABLE")
        return self


def status_label(status: Status, reason: Reason | None, detail: str | None = None) -> str:
    """`NOT_EVALUABLE(reason)` / `NOT_EVALUABLE(missing_dependency:<id>)` form."""
    if status is not Status.NOT_EVALUABLE or reason is None:
        return status.value
    inner = reason.value if detail is None else f"{reason.value}:{detail}"
    return f"NOT_EVALUABLE({inner})"
