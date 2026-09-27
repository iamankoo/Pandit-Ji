"""Compatibility request and result contracts (Phase 11;
`docs/ASTROLOGY_STANDARDS.md` v1.25.0, CM-01 to CM-12).

Two participants, labelled A and B only. Results are factor-level facts
with provenance: no overall compatible/incompatible verdict, no statements
of effect, and no traditional total unless every factor is evaluable.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pandit_astro_engine.compatibility.constants import (
    Classification,
    CompatibilityProfileId,
    CompatibilitySystem,
    DoshaState,
    FactorReason,
    FactorStatus,
    MatchReason,
    MatchStatus,
    Participant,
)
from pandit_astro_engine.compatibility.profiles import EvidenceLabel, SourceReference
from pandit_astro_engine.dashas.models import BirthTimeInput, BirthTimeStatus
from pandit_astro_engine.models import CalculationConfig, LocalDateTimeInput, Location
from pandit_astro_engine.nakshatra import Nakshatra
from pandit_astro_engine.rashi import Rashi

FactValue = str | int | float | bool | None


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------
# Input
# --------------------------------------------------------------------------


class MatchParticipantInput(_Model):
    """One person's birth data. The civil birth date in `local_datetime` is
    also the date the minimum-age check uses (CM-04). No name, gender or
    role is taken."""

    local_datetime: LocalDateTimeInput
    location: Location
    birth_time: BirthTimeInput = Field(default_factory=BirthTimeInput)


class CompatibilityRequest(_Model):
    """`profile` has no default (the owner selected no default system).
    `as_of_date` is the caller's current civil date: the engine never reads
    the clock. `participant_consent_attested` records that the caller has a
    basis to process both people's birth data (CM-05)."""

    profile: CompatibilityProfileId
    person_a: MatchParticipantInput
    person_b: MatchParticipantInput
    as_of_date: dt.date
    participant_consent_attested: Literal[True]
    config: CalculationConfig = Field(default_factory=CalculationConfig)


class MoonPlacement(_Model):
    """The birth Moon as matching needs it. A field is `None` when the
    birth-time uncertainty spans a boundary (CM-06)."""

    participant: Participant
    birth_time_status: BirthTimeStatus
    nakshatra: Nakshatra | None
    pada: int | None = Field(default=None, ge=1, le=4)
    rashi: Rashi | None
    moon_longitude: float | None = None
    moon_longitude_low: float | None = None
    moon_longitude_high: float | None = None


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


class FactorResult(_Model):
    factor_id: str
    name: str
    status: FactorStatus
    reason: FactorReason | None = None
    #: Ashtakoot only: points awarded and the factor's maximum.
    points: float | None = None
    max_points: float | None = None
    #: Ten poruthams only: the source's own outcome.
    classification: Classification | None = None
    #: True when the source judges from a named partner (bride or groom).
    role_dependent: bool
    #: True when a role-dependent rule gives the same result under both
    #: possible assignments, so the result holds whichever partner is which.
    role_invariant: bool | None = None
    label: EvidenceLabel
    facts: dict[str, FactValue] = Field(default_factory=dict)
    note: str = ""
    provenance_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> FactorResult:
        evaluated = self.status is FactorStatus.EVALUATED
        if evaluated == (self.reason is not None):
            raise ValueError("a reason is required exactly when a factor is not evaluated")
        if not evaluated and (self.points is not None or self.classification is not None):
            raise ValueError("a factor that is not evaluated carries no outcome")
        return self


class DoshaRecord(_Model):
    dosha_id: str
    name: str
    state: DoshaState
    reason: FactorReason | None = None
    facts: dict[str, FactValue] = Field(default_factory=dict)
    #: Conditions the source names as exceptions or cancellations, each
    #: True, False or None (not evaluable). Reported only: no verdict is
    #: derived from them unless `cancellation_state` says so.
    exception_conditions: dict[str, bool | None] = Field(default_factory=dict)
    cancellation_state: str
    note: str = ""
    provenance_ids: tuple[str, ...] = ()


class AshtakootTotal(_Model):
    """The traditional 36-point total, given only when all eight kutas are
    evaluated (CM-08). Never rescaled from a partial set."""

    status: FactorStatus
    reason: FactorReason | None = None
    points: float | None = None
    max_points: float = 36.0
    missing_factors: tuple[str, ...] = ()


class PoruthamSummary(_Model):
    """Counts only; Kalaprakasika's 'at least five' statement is provenance,
    not a verdict (CM-09)."""

    agreements: int
    disagreements: int
    neutral: int
    not_evaluable: int


class ParticipantPolicyRecord(_Model):
    participant: Participant
    minimum_age_met: bool | None
    reason: MatchReason | None = None


class ProvenanceEntry(_Model):
    entry_id: str
    item: str
    evidence_label: EvidenceLabel
    statement: str
    references: tuple[SourceReference, ...] = ()


class NotImplementedItem(_Model):
    item: str
    reason: str


class CompatibilityFacts(_Model):
    system: CompatibilitySystem
    profile_id: CompatibilityProfileId
    methodology_version: str
    standards_version: str
    engine_version: str
    status: MatchStatus
    reason: MatchReason | None = None
    as_of_date: dt.date
    minimum_age_years: int
    policy_checks: tuple[ParticipantPolicyRecord, ...]
    placements: tuple[MoonPlacement, ...] = ()
    factors: tuple[FactorResult, ...] = ()
    doshas: tuple[DoshaRecord, ...] = ()
    ashtakoot_total: AshtakootTotal | None = None
    porutham_summary: PoruthamSummary | None = None
    assumptions: tuple[str, ...] = ()
    unresolved_choices: tuple[str, ...] = ()
    not_implemented: tuple[NotImplementedItem, ...] = ()
    source_confidence: str = ""
    provenance: tuple[ProvenanceEntry, ...] = ()
    notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> CompatibilityFacts:
        produced = bool(self.placements or self.factors or self.doshas)
        if self.status in (
            MatchStatus.BLOCKED_BY_POLICY,
            MatchStatus.INVALID_INPUT,
            MatchStatus.INTERNAL_ERROR,
        ):
            if produced or self.ashtakoot_total or self.porutham_summary:
                raise ValueError(f"a {self.status.value} result exposes no compatibility facts")
            if self.reason is None:
                raise ValueError(f"a {self.status.value} result needs a reason")
        return self
