"""Numerology request and result contracts (Phase 11; `docs/ASTROLOGY_STANDARDS.md`
v1.25.0, NU-01 to NU-16). Numbers and provenance only; no interpretation."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pandit_astro_engine.numerology.constants import (
    DEFAULT_PROFILE,
    ItemReason,
    ItemStatus,
    MasterNumberPolicy,
    NumerologyProfileId,
    NumerologySystem,
)
from pandit_astro_engine.numerology.profiles import EvidenceLabel, SourceReference


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NameInput(_Model):
    """The name as it is used, in Latin letters, supplied by the caller. No
    transliteration is performed (NU-09, NU-10)."""

    latin_spelling: str = Field(max_length=200)


class NumerologyRequest(_Model):
    """`date_of_birth` is the civil calendar date of birth at the birth place,
    as entered; no time or timezone is needed (NU-03). `master_number_policy`
    has no default for the Pythagorean profile and must be `none` (or
    omitted) for the Chaldean profile (NU-06)."""

    profile: NumerologyProfileId = DEFAULT_PROFILE
    date_of_birth: dt.date | None = None
    name: NameInput | None = None
    master_number_policy: MasterNumberPolicy | None = None

    @model_validator(mode="after")
    def _check(self) -> NumerologyRequest:
        if self.date_of_birth is None and self.name is None:
            raise ValueError("a date of birth or a name is required")
        if self.profile is NumerologyProfileId.CHALDEAN_CHEIRO_1926:
            if self.master_number_policy not in (None, MasterNumberPolicy.NONE):
                raise ValueError(
                    "the Chaldean (Cheiro) profile reduces every number to one digit; "
                    "master-number retention is not supported"
                )
        elif self.master_number_policy is None:
            raise ValueError(
                "the Pythagorean profile needs an explicit master_number_policy (no default)"
            )
        return self

    @property
    def effective_policy(self) -> MasterNumberPolicy:
        return self.master_number_policy or MasterNumberPolicy.NONE


class Reduction(_Model):
    """`chain` starts with the unreduced total and ends with the result; the
    compound number (NU-07) is the first value when it has two or more digits."""

    chain: tuple[int, ...]
    value: int
    compound: int | None
    master_retained: bool


class NumberItem(_Model):
    item_id: str
    status: ItemStatus
    reason: ItemReason | None = None
    label: EvidenceLabel
    inputs: dict[str, int | str] = Field(default_factory=dict)
    reduction: Reduction | None = None
    note: str = ""

    @model_validator(mode="after")
    def _reason_iff_not_evaluated(self) -> NumberItem:
        if (self.status is ItemStatus.EVALUATED) == (self.reason is not None):
            raise ValueError("a reason is required exactly when the item is not evaluated")
        if (self.status is ItemStatus.EVALUATED) != (self.reduction is not None):
            raise ValueError("an evaluated item carries its reduction, and only then")
        return self


class NameWord(_Model):
    word: str
    letter_values: tuple[int, ...]
    total: int
    reduction: Reduction


class NameNumber(_Model):
    status: ItemStatus
    reason: ItemReason | None = None
    input_spelling: str | None = None
    normalized_words: tuple[str, ...] = ()
    normalization_notes: tuple[str, ...] = ()
    offending_characters: tuple[str, ...] = ()
    words: tuple[NameWord, ...] = ()
    reduction: Reduction | None = None

    @model_validator(mode="after")
    def _consistent(self) -> NameNumber:
        if (self.status is ItemStatus.EVALUATED) != (self.reduction is not None):
            raise ValueError("an evaluated name carries its reduction, and only then")
        if (self.status is ItemStatus.EVALUATED) == (self.reason is not None):
            raise ValueError("a reason is required exactly when the name is not evaluated")
        return self


class AssociatedNumbers(_Model):
    """Cheiro's own-series dates and 'interchangeable' numbers (NU-12)."""

    status: ItemStatus
    reason: ItemReason | None = None
    birth_number: int | None = None
    own_series_dates: tuple[int, ...] = ()
    interchangeable_numbers: tuple[int, ...] = ()
    interchangeable_dates: tuple[int, ...] = ()
    statement: str = ""


class InterpretationReference(_Model):
    """Interpretation is deferred (NU-13): only where the source discusses it."""

    status: ItemStatus = ItemStatus.DEFERRED
    reason: ItemReason = ItemReason.INTERPRETATION_DEFERRED_TO_KNOWLEDGE_PHASE
    references: tuple[SourceReference, ...] = ()


class ProvenanceEntry(_Model):
    entry_id: str
    item: str
    evidence_label: EvidenceLabel
    statement: str
    references: tuple[SourceReference, ...] = ()


class NumerologyFacts(_Model):
    system: NumerologySystem
    profile_id: NumerologyProfileId
    methodology_version: str
    standards_version: str
    engine_version: str
    master_number_policy: MasterNumberPolicy
    date_of_birth: dt.date | None
    moolank: NumberItem
    bhagyank: NumberItem
    date_numbers: tuple[NumberItem, ...] = ()
    name_number: NameNumber
    associated_numbers: AssociatedNumbers
    interpretation: InterpretationReference
    assumptions: tuple[str, ...]
    confidence: str
    provenance: tuple[ProvenanceEntry, ...]
