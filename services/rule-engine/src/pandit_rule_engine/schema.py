"""Rule schema (Phase 6A): typed, declarative rule documents.

The schema follows `docs/ARCHITECTURE.md` §7 ("Rule schema") and
`docs/ASTROLOGY_STANDARDS.md` §"Phase 6 rule-engine methodology". A rule is
a *source-specific profile*: it names its source, edition, translator and
location, carries one or more *readings* (each evaluated separately), and
keeps exceptions, cancellations and dependencies apart from detection.

Conditions are a closed set of typed operators (no embedded code). Only the
operators the approved first-tranche rules need are defined -- the language
is deliberately not generic.
"""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from pandit_rule_engine.vocab import (
    Body,
    Dignity,
    Modality,
    Reason,
    Status,
)

#: Reserved variable naming the current candidate inside `exists`, `for_all`
#: and `count` (`where` sub-conditions).
IT = "$it"
#: The binding of the immediately enclosing quantifier, readable from a
#: nested quantifier's `where` (for example "no malefic aspects this benefic").
OUTER = "$outer"

_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_]*$")
_TAG_PATTERN = re.compile(r"^[a-z0-9_.]+$")
_BODY_VALUES = {body.value for body in Body}


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _check_planet(value: str) -> str:
    if value not in (IT, OUTER) and value not in _BODY_VALUES:
        raise ValueError(f"planet must be one of {sorted(_BODY_VALUES)}, {IT!r} or {OUTER!r}")
    return value


def _check_reference(value: str) -> str:
    if value not in ("lagna", IT, OUTER) and value not in _BODY_VALUES:
        raise ValueError(f"reference must be 'lagna' or a body, got {value!r}")
    return value


def _check_id(value: str) -> str:
    if not _ID_PATTERN.match(value):
        raise ValueError(f"identifier must be UPPER_SNAKE_CASE, got {value!r}")
    return value


PlanetName = Annotated[str, AfterValidator(_check_planet)]
ReferenceName = Annotated[str, AfterValidator(_check_reference)]
IdStr = Annotated[str, AfterValidator(_check_id)]


# --------------------------------------------------------------------------
# Planet sets
# --------------------------------------------------------------------------


class PlanetSet(_Model):
    """A set of bodies a quantified condition ranges over.

    `bodies` names them explicitly; otherwise `nature` selects by natural
    benefic/malefic (Ch. 3 v. 11) over all nine bodies; with neither, the
    seven classical planets are used. `nodes` is the node-participation
    policy: `excluded` (source counts seven planets), `included` (source
    names the nodes) or `unspecified` (the source is silent; the reading is
    evaluated both ways and a difference gives
    `NOT_EVALUABLE(node_participation_unspecified)`).
    """

    bodies: tuple[Body, ...] | None = None
    nature: Literal["benefic", "malefic"] | None = None
    exclude: tuple[Body, ...] = ()
    nodes: Literal["excluded", "included", "unspecified"] = "excluded"

    @model_validator(mode="after")
    def _one_selector(self) -> PlanetSet:
        if self.bodies is not None and self.nature is not None:
            raise ValueError("PlanetSet takes either bodies or nature, not both")
        return self


# --------------------------------------------------------------------------
# Conditions
# --------------------------------------------------------------------------


class PlanetHouse(_Model):
    """`planet` is in one of `houses`, counted (whole-sign) from `reference`."""

    op: Literal["planet_house"]
    planet: PlanetName
    reference: ReferenceName = "lagna"
    houses: tuple[int, ...] = Field(min_length=1)

    @field_validator("houses")
    @classmethod
    def _houses(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(house < 1 or house > 12 for house in value):
            raise ValueError("houses must be in 1..12")
        return value


class PlanetDignity(_Model):
    """Phase 5 dignity of `planet` is one of `in_` (sign-level)."""

    op: Literal["planet_dignity"]
    planet: PlanetName
    in_: tuple[Dignity, ...] = Field(alias="in", min_length=1)


class PlanetFlag(_Model):
    """A Phase 4/5 boolean fact of `planet` (`retrograde` or `combust`)."""

    op: Literal["planet_flag"]
    planet: PlanetName
    flag: Literal["retrograde", "combust"]
    value: bool = True


class PlanetMoolatrikona(_Model):
    """`planet` is in its Moolatrikona (BPHS Ch. 3 v. 51-54), a Phase 6 fact
    kept separate from the Phase 5 dignity model."""

    op: Literal["planet_moolatrikona"]
    planet: PlanetName
    value: bool = True


class PlanetModality(_Model):
    op: Literal["planet_modality"]
    planet: PlanetName
    in_: tuple[Modality, ...] = Field(alias="in", min_length=1)


class SameSign(_Model):
    """`a` and `b` occupy the same sign (conjunction, whole-sign)."""

    op: Literal["same_sign"]
    a: PlanetName
    b: PlanetName


class AspectedBy(_Model):
    """`by` casts a Phase 5 full-sign graha drishti on `planet`.

    Present -> definitely true. Absent -> `NOT_EVALUABLE(requires_partial_drishti)`
    when a partial aspect could exist (BPHS Ch. 26 v. 2-5: only on the 3rd/10th,
    5th/9th or 4th/8th from the aspecting planet), because partial aspects are not
    available until Phase 9 (`docs/ASTROLOGY_STANDARDS.md` §"Aspect refinement");
    from any other house there is no aspect, so the result is false.
    """

    op: Literal["aspected_by"]
    planet: PlanetName
    by: PlanetName


class NaturalNature(_Model):
    """Natural benefic/malefic (Ch. 3 v. 11) of `planet` equals `is_`.
    Mercury `mixed` and Moon near the waxing/waning boundary are
    `NOT_EVALUABLE(reading_ambiguous)`."""

    op: Literal["natural_nature"]
    planet: PlanetName
    is_: Literal["benefic", "malefic"] = Field(alias="is")


class SignLordRelation(_Model):
    """The lord of the sign `planet` occupies stands in one of `kinds` to
    `planet` (an "enemy sign" test). `basis` selects the natural (Ch. 3 v. 55)
    or compound (v. 57-58) relationship. A planet in its own sign has no
    relation to itself, so the test is false."""

    op: Literal["sign_lord_relation"]
    planet: PlanetName
    basis: Literal["natural", "compound"]
    kinds: tuple[str, ...] = Field(min_length=1)


class DistinctSigns(_Model):
    """The planets of `over` occupy exactly `count` distinct signs."""

    op: Literal["distinct_signs"]
    over: PlanetSet
    count: int = Field(ge=1, le=12)


class RuleResultIs(_Model):
    """The result of another rule has one of the given statuses. Used for
    explicit inter-rule dependencies (for example a suppression rule)."""

    op: Literal["rule_result"]
    rule_id: IdStr
    in_: tuple[Status, ...] = Field(alias="in", min_length=1)


class AllOf(_Model):
    op: Literal["all"]
    args: tuple[Condition, ...] = Field(min_length=1)


class AnyOf(_Model):
    op: Literal["any"]
    args: tuple[Condition, ...] = Field(min_length=1)


class Not(_Model):
    op: Literal["not"]
    arg: Condition


class Exists(_Model):
    """At least one body of `over` satisfies `where` (bound as `$it`)."""

    op: Literal["exists"]
    over: PlanetSet
    where: Condition


class ForAll(_Model):
    """Every body of `over` satisfies `where` (bound as `$it`)."""

    op: Literal["for_all"]
    over: PlanetSet
    where: Condition


class CountAtLeast(_Model):
    """At least `at_least` bodies of `over` satisfy `where`; the observed
    count is recorded as evidence."""

    op: Literal["count"]
    over: PlanetSet
    where: Condition
    at_least: int = Field(ge=1, le=9)


Condition = Annotated[
    PlanetHouse
    | PlanetDignity
    | PlanetFlag
    | PlanetModality
    | PlanetMoolatrikona
    | SameSign
    | AspectedBy
    | NaturalNature
    | SignLordRelation
    | DistinctSigns
    | RuleResultIs
    | AllOf
    | AnyOf
    | Not
    | Exists
    | ForAll
    | CountAtLeast,
    Field(discriminator="op"),
]

for _model in (AllOf, AnyOf, Not, Exists, ForAll, CountAtLeast):
    _model.model_rebuild()


# --------------------------------------------------------------------------
# Rule parts
# --------------------------------------------------------------------------

Confidence = Literal["HIGH", "MEDIUM", "LOW"]
VerificationLevel = Literal[
    "IMAGE-TRANSLATION",
    "OCR-TRANSLATION",
    "OCR-SOURCE-LANGUAGE",
    "SANSKRIT-LEVEL",
]
EffectClass = Literal["supportive", "challenging", "mixed", "neutral", "context_dependent"]
RuleStatus = Literal["draft", "active", "deprecated"]
ReadingBasis = Literal["translation", "sanskrit_reading", "convention"]


class Reading(_Model):
    """One source-supported reading of a rule's condition. Every reading is
    evaluated separately; `reading_id` and `source_id` are preserved in the
    result."""

    reading_id: IdStr
    source_id: IdStr | None = None
    basis: ReadingBasis
    note: str = ""
    conditions: Condition


class Exception_(_Model):
    """A source-stated exception: when it holds the rule does not obtain."""

    exception_id: IdStr
    when: Condition
    note: str = ""


class Cancellation(_Model):
    """A source-stated cancellation, kept separate from detection."""

    cancellation_id: IdStr
    when: Condition
    effect: Literal["full", "partial"] = "full"
    source_location: str = ""
    note: str = ""


class Dependency(_Model):
    """A dependency on something this phase does not supply.

    `unresolved_effect: not_evaluable_if_detected` makes a detected rule
    `NOT_EVALUABLE(reason)` (for example a partner-chart cancellation, or a
    suppression rule whose condition is absent from the source);
    `informational` only documents the dependency.
    """

    dependency_id: IdStr
    kind: Literal["fact", "rule", "later_phase_input", "source_gap"]
    owner_phase: int | None = Field(default=None, ge=1, le=21)
    reason: Reason
    unresolved_effect: Literal["not_evaluable_if_detected", "informational"] = "informational"
    description: str = ""


class Applicability(_Model):
    schools: tuple[str, ...] = ()
    #: Gender is never a detection requirement; at most it selects the
    #: source's stated effect label.
    gender: Literal["not_required", "effect_label_only"] = "not_required"
    notes: str = ""


class InterpretationTags(_Model):
    """Structured, language-neutral interpretation tags (never prose)."""

    domain: tuple[str, ...] = ()
    signification: tuple[str, ...] = ()
    effect_class: EffectClass

    @field_validator("domain", "signification")
    @classmethod
    def _tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for tag in value:
            if not _TAG_PATTERN.match(tag):
                raise ValueError(f"tag must be lower_snake/dot ID, got {tag!r}")
        return value


class _SourceFields(_Model):
    source: str = Field(min_length=1, description="Work title.")
    source_id: IdStr
    source_edition: str = Field(min_length=1)
    translator: str | None
    source_location: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    source_tier: int = Field(ge=1, le=5)
    verification_level: VerificationLevel


class Rule(_SourceFields):
    document_type: Literal["rule"]
    rule_id: IdStr
    rule_version: str = Field(min_length=1)
    astrology_system: Literal["vedic_parashari"]
    school: str = Field(min_length=1)
    profile: IdStr
    category: Literal["yoga", "dosha"]
    standards_version: str = Field(min_length=1)
    confidence: Confidence
    status: RuleStatus
    priority: int = Field(default=100, ge=0)
    conflict_group: IdStr | None = None
    ambiguity_group: IdStr | None = None
    #: Common precondition, ANDed with every reading.
    conditions: Condition | None = None
    readings: tuple[Reading, ...] = Field(min_length=1)
    exceptions: tuple[Exception_, ...] = ()
    cancellations: tuple[Cancellation, ...] = ()
    dependencies: tuple[Dependency, ...] = ()
    applicability: Applicability = Applicability()
    interpretation_tags: InterpretationTags

    @model_validator(mode="after")
    def _consistency(self) -> Rule:
        if not self.rule_id.startswith(self.profile):
            raise ValueError("rule_id must start with its profile ID")
        ids = [reading.reading_id for reading in self.readings]
        if len(set(ids)) != len(ids):
            raise ValueError("reading_id values must be unique within a rule")
        return self


class TableDocument(_SourceFields):
    """A methodology data table (relationships, natural nature, functional
    nature, Moolatrikona). `data` is validated per `table_kind` by
    `pandit_rule_engine.tables`."""

    document_type: Literal["table"]
    table_id: IdStr
    table_kind: Literal[
        "natural_relationships",
        "temporal_relationship",
        "compound_relationship",
        "natural_nature",
        "moolatrikona",
        "functional_nature",
    ]
    standards_version: str = Field(min_length=1)
    confidence: Confidence
    data: dict[str, Any]


class RulesetManifest(_Model):
    document_type: Literal["ruleset"]
    ruleset_id: IdStr
    ruleset_version: str = Field(min_length=1)
    schema_version: int = Field(ge=1)
    standards_version: str = Field(min_length=1)
