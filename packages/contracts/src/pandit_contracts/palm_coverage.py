"""Source coverage manifest models (Phase 13; standards PM-28, final owner decision D).

A machine-checkable record of what the palmistry sources were actually *read* and what each
concept's support is, so an unread concept can never silently become production-supported.
The manifest content lives in the palm knowledge content (``services/knowledge/content/palm``);
these models are shared so the knowledge service (which builds the palm knowledge version from
it) and the rule engine (which validates every palm rule against it) read the same thing.

Status vocabulary: the locked set (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `NOT_SUPPORTED`,
`NOT_READ`, `EXCLUDED_BY_POLICY`) plus `NOT_EVALUABLE` and `RESEARCH_PENDING` named in the
Phase 13 implementation directive. Only `SUPPORTED` and `PARTIALLY_SUPPORTED` records (with
``read`` true) can back an interpretation, and a partial record only for the one statement it
names.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator

from pandit_contracts.palm_canonical import sha256_hex


class CoverageStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    NOT_READ = "NOT_READ"
    EXCLUDED_BY_POLICY = "EXCLUDED_BY_POLICY"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    RESEARCH_PENDING = "RESEARCH_PENDING"


# Statuses that may back a production interpretation (and only when ``read`` is true).
BACKING_STATUSES = frozenset({CoverageStatus.SUPPORTED, CoverageStatus.PARTIALLY_SUPPORTED})


class CoverageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    profile_id: str  # a PALM_ source profile (registry 6.11) or a methodology profile
    methodology_profile: str  # PALM_WESTERN or PALM_INDIAN_HASTA_SAMUDRIKA
    location: str
    concept_id: str
    status: CoverageStatus
    reading_level: str
    confidence: str  # HIGH | MEDIUM | LOW
    read: bool
    statement: str = ""  # the one statement a PARTIALLY_SUPPORTED record backs
    note: str = ""

    @model_validator(mode="after")
    def _consistent(self) -> CoverageRecord:
        if self.status in BACKING_STATUSES and not self.read:
            raise ValueError(f"{self.concept_id}: a supported concept must have been read")
        if self.status is CoverageStatus.NOT_READ and self.read:
            raise ValueError(f"{self.concept_id}: NOT_READ cannot be marked read")
        if self.status is CoverageStatus.PARTIALLY_SUPPORTED and not self.statement:
            raise ValueError(f"{self.concept_id}: a partial record names the statement it backs")
        if self.confidence not in {"HIGH", "MEDIUM", "LOW"}:
            raise ValueError(f"{self.concept_id}: confidence must be HIGH, MEDIUM or LOW")
        if self.methodology_profile == "PALM_INDIAN_HASTA_SAMUDRIKA" and (
            self.status in BACKING_STATUSES
        ):
            raise ValueError("the Indian profile is RESEARCH_PENDING: nothing may be supported")
        return self


class PalmSourceCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_id: str
    manifest_version: str
    records: tuple[CoverageRecord, ...]

    @model_validator(mode="after")
    def _unique(self) -> PalmSourceCoverage:
        seen: set[tuple[str, str, str]] = set()
        for rec in self.records:
            key = (rec.profile_id, rec.location, rec.concept_id)
            if key in seen:
                raise ValueError(f"duplicate coverage record {key}")
            seen.add(key)
        return self

    @property
    def content_hash(self) -> str:
        return sha256_hex(self.model_dump(mode="json"))

    def record_for(self, profile_id: str, location: str, concept_id: str) -> CoverageRecord | None:
        for rec in self.records:
            if (rec.profile_id, rec.location, rec.concept_id) == (profile_id, location, concept_id):
                return rec
        return None

    def status_of(self, concept_id: str) -> tuple[CoverageStatus, ...]:
        """Every status recorded for a concept (a concept may differ by source profile)."""
        return tuple(sorted({r.status for r in self.records if r.concept_id == concept_id}))

    def problems_for_rule(
        self,
        source_profile: str,
        source_location: str,
        concept_ids: Iterable[str],
    ) -> tuple[str, ...]:
        """Reasons a rule citing this profile, location and these concepts is not allowed."""
        problems: list[str] = []
        for concept_id in sorted(set(concept_ids)):
            rec = self.record_for(source_profile, source_location, concept_id)
            if rec is None:
                problems.append(
                    f"{concept_id}: no coverage record for {source_profile} at {source_location}"
                )
            elif rec.status not in BACKING_STATUSES or not rec.read:
                problems.append(
                    f"{concept_id}: coverage status {rec.status.value} cannot back a rule"
                )
        return tuple(problems)
