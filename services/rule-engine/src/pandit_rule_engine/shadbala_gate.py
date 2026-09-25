"""Eligibility of a Shadbala total for rule use (Shadbala method policy,
`docs/ASTROLOGY_STANDARDS.md` v1.22.0, SM-09).

A rule that needs a planet's Shadbala may use it only when the bundle's
Shadbala section was built from a `ShadbalaMethodResult` of the method
`MODERN_RAMAN`, the birth time is exact, the planet is one of the seven
Shadbala planets, and that planet's total is complete -- which also means
that no open methodology reading changes it. Every other case returns
`NOT_EVALUABLE` with one precise reason; nothing is guessed, defaulted or
taken from the BPHS reference method.

This gate answers "may the total be used"; it does not say whether a planet
is "strong". No threshold for "strong" is locked (the Phase 6 strength rules
keep `requires_shadbala`), so no shipped rule calls it yet.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from pandit_rule_engine.phase9_evidence import ShadbalaEvidence

SHADBALA_PLANETS = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn")
RULE_METHOD = "MODERN_RAMAN"
_READING_NOT_SELECTED = "methodology_reading_not_selected"


class ShadbalaGateReason(str, Enum):
    EVIDENCE_ABSENT = "shadbala_evidence_absent"
    METHOD_NOT_RECORDED = "shadbala_method_not_recorded"
    METHOD_NOT_MODERN_RAMAN = "shadbala_method_not_modern_raman"
    BODY_NOT_COVERED = "shadbala_body_not_covered"
    BIRTH_TIME_NOT_EXACT = "shadbala_birth_time_not_exact"
    METHODOLOGY_CHOICE_UNRESOLVED = "shadbala_methodology_choice_unresolved"
    TOTAL_PARTIAL = "shadbala_total_partial"


class ShadbalaRuleInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    body: str
    status: str  # "success" | "not_evaluable"
    reason: ShadbalaGateReason | None = None
    detail: str | None = None
    total_rupas: float | None = None
    method: str | None = None
    method_version: str | None = None
    profile_id: str | None = None


def _blocked(
    body: str, reason: ShadbalaGateReason, detail: str | None, ev: ShadbalaEvidence | None
) -> ShadbalaRuleInput:
    return ShadbalaRuleInput(
        body=body,
        status="not_evaluable",
        reason=reason,
        detail=detail,
        method=ev.method.method if ev is not None and ev.method is not None else None,
        method_version=(
            ev.method.method_version if ev is not None and ev.method is not None else None
        ),
        profile_id=ev.profile_id if ev is not None else None,
    )


def shadbala_for_rule(evidence: ShadbalaEvidence | None, body: str) -> ShadbalaRuleInput:
    """The planet's MODERN_RAMAN total, or NOT_EVALUABLE with the first
    failing condition in a fixed order."""
    if evidence is None:
        return _blocked(body, ShadbalaGateReason.EVIDENCE_ABSENT, None, None)
    method = evidence.method
    if method is None:
        return _blocked(
            body,
            ShadbalaGateReason.METHOD_NOT_RECORDED,
            f"profile facts {evidence.profile_id} without a method envelope",
            evidence,
        )
    if method.method != RULE_METHOD:
        return _blocked(body, ShadbalaGateReason.METHOD_NOT_MODERN_RAMAN, method.method, evidence)
    if body not in SHADBALA_PLANETS:
        return _blocked(body, ShadbalaGateReason.BODY_NOT_COVERED, None, evidence)
    if evidence.time_precision != "exact":
        return _blocked(
            body, ShadbalaGateReason.BIRTH_TIME_NOT_EXACT, evidence.time_precision, evidence
        )
    total = next((t for t in method.totals if t.body == body), None)
    if total is None:
        return _blocked(body, ShadbalaGateReason.TOTAL_PARTIAL, "no total recorded", evidence)
    if total.status != "complete":
        planet = next(p for p in evidence.planets if p.body == body)
        open_reading = [
            c.component
            for c in planet.components
            if c.status == "not_evaluable" and c.reason == _READING_NOT_SELECTED
        ]
        if open_reading:
            return _blocked(
                body,
                ShadbalaGateReason.METHODOLOGY_CHOICE_UNRESOLVED,
                f"{', '.join(method.unresolved_choices)} changes {', '.join(open_reading)}",
                evidence,
            )
        return _blocked(
            body,
            ShadbalaGateReason.TOTAL_PARTIAL,
            "missing: " + ", ".join(total.missing_components),
            evidence,
        )
    return ShadbalaRuleInput(
        body=body,
        status="success",
        total_rupas=total.total_rupas,
        method=method.method,
        method_version=method.method_version,
        profile_id=evidence.profile_id,
    )
