"""Schema of the Phase 17 domain ruleset (ADR-012; standards LD-01 to LD-27).

The domain ruleset is a SEPARATE ruleset from the Phase 6 Vedic ruleset (precedent: the Phase 13
palm ruleset): its own manifest, its own version, its own content hash, its own document types.
It states no prediction. A domain rule says which house, karaka, divisional chart or researched
method a named source assigns to a life domain, and how to read that state from facts that
already exist.

Every rule carries its provenance (source, location, verification level, profile), its research
support status, its policy flags and its structured interpretation tags. There is no free text
that reaches a user: ``source_term`` is the source's own short term and ``bridge_note`` records
where the product label is not the source's word.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pandit_contracts.domain import (
    DomainReason,
    DomainRuleKind,
    DomainSupport,
    EffectClass,
    LifeDomain,
    PolicyClass,
)
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

from pandit_rule_engine.vocab import Body

DOMAIN_STANDARDS_VERSION = "1.30.0"
DOMAIN_RULESET_ID = "PANDIT_JI_DOMAIN_PHASE17"
RULE_PREFIX = "DOM_"

#: The only divisional charts a domain may use (owner decision 3, standards LD-09, BPHS Ch. 7
#: v. 1-8): D2 wealth, D3 co-born, D7 sons, D9 spouse, D10 power and position, D12 parents, D20
#: worship, D24 learning. D4 is neither property nor foreign settlement.
LOCKED_VARGAS: tuple[int, ...] = (2, 3, 7, 9, 10, 12, 20, 24)

_ID = re.compile(r"^[A-Z0-9][A-Z0-9_]*$")
_TAG = re.compile(r"^[a-z0-9_.]+$")
_MAPPING_ID = re.compile(r"^MAP\.[A-Z0-9_]+\.[A-Z0-9_.]+$")
_BODIES = {b.value for b in Body}


def _id(value: str) -> str:
    if not _ID.match(value):
        raise ValueError(f"identifier must be UPPER_SNAKE_CASE, got {value!r}")
    return value


IdStr = Annotated[str, AfterValidator(_id)]


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


# -- documents ---------------------------------------------------------------------------------


class DomainRulesetManifest(_M):
    document_type: Literal["domain_ruleset"]
    ruleset_id: Literal["PANDIT_JI_DOMAIN_PHASE17"]
    ruleset_version: str = Field(min_length=1)
    schema_version: int = Field(ge=1)
    standards_version: Literal["1.30.0"]
    methodology_version: str = Field(min_length=1)
    scope: str = Field(min_length=1)


class TaxonomyEntry(_M):
    domain: LifeDomain
    label: str = Field(min_length=1)
    parent: LifeDomain | None = None
    kind: Literal["PHASES_MD", "EXTENSION"]
    #: The research status. It is never upgraded and never inherited from the parent.
    support: DomainSupport
    #: A static policy block applied before any methodology (the minors policy for Childhood
    #: and School).
    blocked_reason: DomainReason | None = None
    #: Why a domain with no approved mapping is not evaluable.
    not_evaluable_reason: DomainReason | None = None
    #: Policy classes of this domain. Policy (the stricter side) inherits from the parent.
    policy: tuple[PolicyClass, ...] = ()
    adult_confirmation_required: bool = False
    note: str = ""

    @model_validator(mode="after")
    def _checks(self) -> TaxonomyEntry:
        if self.parent is self.domain:
            raise ValueError("a domain cannot be its own parent")
        if self.blocked_reason is not None and self.blocked_reason not in {
            DomainReason.MINORS_POLICY_UNRESOLVED,
            DomainReason.POLICY_BLOCKED,
        }:
            raise ValueError("blocked_reason must be a policy reason")
        return self


class TaxonomyDocument(_M):
    document_type: Literal["domain_taxonomy"]
    taxonomy_version: str = Field(min_length=1)
    entries: tuple[TaxonomyEntry, ...] = Field(min_length=1)


# -- rule parameters (one model per kind) --------------------------------------------------------


class HouseParams(_M):
    kind: Literal["HOUSE_RELEVANCE"]
    house: int = Field(ge=1, le=12)
    #: ``SIGNIFICATION_ONLY`` states the house sign and its lord's identity only (used where
    #: policy limits the domain to structural significations, for example Children).
    detail: Literal["FULL", "SIGNIFICATION_ONLY"] = "FULL"


class KarakaParams(_M):
    kind: Literal["KARAKA_RELEVANCE"]
    planet: Body
    for_house: int | None = Field(default=None, ge=1, le=12)
    detail: Literal["FULL", "SIGNIFICATION_ONLY"] = "FULL"


class VargaParams(_M):
    kind: Literal["VARGA_RELEVANCE"]
    varga: int
    #: Which placements to show in that divisional chart. This selection is an engineering
    #: choice stated here, not a source statement: the source names the chart and the matter.
    show_house_lords: tuple[int, ...] = ()
    show_karakas: tuple[Body, ...] = ()
    show_lagna_lord: bool = False

    @field_validator("varga")
    @classmethod
    def _locked(cls, value: int) -> int:
        if value not in LOCKED_VARGAS:
            raise ValueError(
                f"D{value} is not a locked divisional-chart mapping (allowed: "
                + ", ".join(f"D{v}" for v in LOCKED_VARGAS)
                + ")"
            )
        return value

    @model_validator(mode="after")
    def _something(self) -> VargaParams:
        if not (self.show_house_lords or self.show_karakas or self.show_lagna_lord):
            raise ValueError("a varga rule shows at least one placement")
        return self


class Phase6Params(_M):
    kind: Literal["PHASE6_RULE_APPLICABILITY"]
    phase6_rule_id: IdStr
    #: The signification tag the Phase 6 rule carries (a cross-package test pins it to the real
    #: rule). A blocked tag makes the result POLICY_BLOCKED whatever the Phase 6 status.
    phase6_signification: str
    blocked: bool = False

    @field_validator("phase6_signification")
    @classmethod
    def _t(cls, value: str) -> str:
        if not _TAG.match(value):
            raise ValueError("tag must be lower_snake/dot")
        return value


class MarriageDashaParams(_M):
    kind: Literal["MARRIAGE_DASHA_METHOD"]
    house: Literal[7]
    #: The source says "the Dasa period of the planet" (Phaladeepika X sl. 13): the Mahadasha.
    level: Literal["MAHADASHA"] = "MAHADASHA"
    relations: tuple[Literal["occupies", "aspects", "owns"], ...] = ("occupies", "aspects", "owns")


class SubjectParams(_M):
    kind: Literal["SUBJECT_PROFICIENCY"]
    house: Literal[2] = 2
    associated_planet: Body
    area_tag: str

    @field_validator("area_tag")
    @classmethod
    def _t(cls, value: str) -> str:
        if not _TAG.match(value):
            raise ValueError("tag must be lower_snake/dot")
        return value


class WithheldParams(_M):
    """A source statement the methodology knows and withholds from the user (LD-20, LD-26).

    ``outcome`` is ``POLICY_BLOCKED`` for a policy withholding and ``NOT_EVALUABLE`` where the
    source method needs information the product does not collect (the subject's sex).
    """

    kind: Literal["POLICY_WITHHELD"]
    reason: DomainReason
    outcome: Literal["POLICY_BLOCKED", "NOT_EVALUABLE"] = "POLICY_BLOCKED"


RuleParams = Annotated[
    HouseParams
    | KarakaParams
    | VargaParams
    | Phase6Params
    | MarriageDashaParams
    | SubjectParams
    | WithheldParams,
    Field(discriminator="kind"),
]

VerificationLevel = Literal[
    "IMAGE-TRANSLATION", "OCR-TRANSLATION", "OCR-SOURCE-LANGUAGE", "SANSKRIT-LEVEL"
]


class RuleTags(_M):
    domain_tags: tuple[str, ...] = ()
    signification_tags: tuple[str, ...] = ()
    effect_class: EffectClass = "neutral"

    @field_validator("domain_tags", "signification_tags")
    @classmethod
    def _tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for tag in value:
            if not _TAG.match(tag):
                raise ValueError(f"tag must be lower_snake/dot, got {tag!r}")
        return value


class DomainRuleDocument(_M):
    document_type: Literal["domain_rule"]
    rule_id: IdStr
    rule_version: str = Field(min_length=1)
    domain: LifeDomain
    kind: DomainRuleKind
    mapping_id: str
    status: Literal["active", "draft"] = "active"
    # provenance
    source: str = Field(min_length=1)
    source_id: IdStr
    source_edition: str = Field(min_length=1)
    translator: str | None = None
    source_location: str = Field(min_length=1)
    verification_level: VerificationLevel
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    profile: IdStr
    # research status of the mapping this rule executes (never upgraded)
    support: DomainSupport
    source_term: str = ""
    bridge_note: str = ""
    params: RuleParams
    tags: RuleTags = RuleTags()
    policy_flags: tuple[PolicyClass, ...] = ()
    conflict_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _checks(self) -> DomainRuleDocument:
        if not self.rule_id.startswith(RULE_PREFIX):
            raise ValueError(f"rule_id must start with {RULE_PREFIX}")
        if not _MAPPING_ID.match(self.mapping_id):
            raise ValueError("mapping_id must look like MAP.<DOMAIN>.<KIND>.<id>")
        if self.params.kind != self.kind.value:
            raise ValueError("params.kind must equal kind")
        if self.support is DomainSupport.NOT_EVALUABLE and not (
            isinstance(self.params, WithheldParams)
            and self.params.outcome == "NOT_EVALUABLE"
            and self.params.reason is DomainReason.RESEARCH_PENDING
        ):
            raise ValueError("a rule cannot execute a NOT_EVALUABLE mapping")
        # (a research-pending record is the one exception: it states a researched method that
        # is not approved for this domain and evaluates nothing)
        if self.kind is DomainRuleKind.POLICY_WITHHELD and (
            self.tags.domain_tags or self.tags.signification_tags
        ):
            raise ValueError("a withheld rule exposes no tags")
        return self


class DomainConflict(_M):
    """A recorded source conflict (DC-01 to DC-05). Kept, never resolved."""

    document_type: Literal["domain_conflict"]
    conflict_id: str
    title: str = Field(min_length=1)
    profiles: tuple[str, ...] = Field(min_length=2)
    note: str = ""

    @field_validator("conflict_id")
    @classmethod
    def _id(cls, value: str) -> str:
        if not re.match(r"^DC-\d{2}$|^[A-Z0-9_]+$", value):
            raise ValueError("conflict id must be DC-nn or UPPER_SNAKE")
        return value
