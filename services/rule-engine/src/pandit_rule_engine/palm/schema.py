"""Schema of the palm ruleset documents (Phase 13; standards PM-12, PM-25 to PM-29).

A palm ruleset is a **separate ruleset** from the Phase 6 Vedic ruleset: its own documents
(``palm_ruleset``, ``palm_rule``, ``palm_tag_vocabulary``, ``palm_conflict``), its own manifest
and version, its own rule-identifier namespace (``PALMR_``), its own directory
(``services/rule-engine/palm_rules/``). The Vedic loader does not know these document types and
rejects them; the palm loader rejects Vedic documents. Neither can load the other.

A rule is not prose. It names **one** source profile and **one** source location (no consensus of
authors, no merging), the coverage concepts it depends on, the structured conditions over palm
facts, and interpretation **tags** from a closed, reviewed vocabulary. It carries no free
interpretation text and predicts no event.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PALM_RULE_ID = re.compile(r"^PALMR_[A-Z0-9_]+$")
PALM_TAG = re.compile(r"^[A-Z][A-Z0-9_]{2,60}$")
PALM_SOURCE_PROFILE = re.compile(r"^PALM_[A-Z]{2}_[A-Z0-9_]+$")
PALM_RULESET_ID = "PANDIT_JI_PALM_WESTERN_PHASE13"
PALM_STANDARDS_VERSION = "1.28.0"
FRAMING = "TRADITIONAL_INTERPRETIVE_NOT_SCIENTIFIC"

ClaimKind = Literal["READING_CONVENTION", "TRADITIONAL_TENDENCY"]
Visibility = Literal["CLEAR", "PARTIAL", "OCCLUDED", "NOT_VISIBLE", "NOT_EVALUABLE"]


class _Doc(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PalmRulesetManifest(_Doc):
    document_type: Literal["palm_ruleset"]
    ruleset_id: str
    ruleset_version: str
    schema_version: int
    standards_version: str
    methodology_profile: Literal["PALM_WESTERN"]
    scope: str  # records that this is a fixture set, not the production rule list


class Requirement(_Doc):
    """One condition over the palm facts. All requirements of a rule must hold."""

    fact_type: str
    region_id: str | None = None
    hand_side: Literal["LEFT", "RIGHT"] | None = None
    value_kind: Literal["INT", "ENUM", "BOOL", "RATIO_FIXED"] | None = None
    value_equals: str | int | bool | None = None
    labelling_profile: str | None = None  # the source profile that named the structure

    @model_validator(mode="after")
    def _value(self) -> Requirement:
        if (self.value_kind is None) != (self.value_equals is None):
            raise ValueError("value_kind and value_equals go together")
        return self


class PalmRule(_Doc):
    document_type: Literal["palm_rule"]
    rule_id: str = Field(pattern=PALM_RULE_ID.pattern)
    rule_version: str
    ruleset_id: str
    methodology_profile: Literal["PALM_WESTERN"]
    source_profile: str = Field(pattern=PALM_SOURCE_PROFILE.pattern)
    source_id: str
    source_location: str = Field(min_length=3)
    reading_level: str
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    claim_kind: ClaimKind
    concepts: tuple[str, ...] = Field(min_length=1)
    requires: tuple[Requirement, ...] = Field(min_length=1)
    interpretation_tags: tuple[str, ...] = Field(min_length=1)
    known_conflicts: tuple[str, ...] = ()
    framing: Literal["TRADITIONAL_INTERPRETIVE_NOT_SCIENTIFIC"]
    source_note: str = ""


class TagEntry(_Doc):
    tag: str
    claim_kind: ClaimKind
    description: str


class PalmTagVocabulary(_Doc):
    document_type: Literal["palm_tag_vocabulary"]
    vocabulary_id: str
    tags: tuple[TagEntry, ...]


class PalmConflict(_Doc):
    """A recorded UNRESOLVED_CONFLICT between source profiles. No winner is chosen."""

    document_type: Literal["palm_conflict"]
    conflict_id: str
    profiles: tuple[str, ...] = Field(min_length=2)
    status: Literal["UNRESOLVED_CONFLICT"]
    summary: str
