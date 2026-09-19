"""Methodology data tables (Phase 6F-6H): typed validation and access.

The tables are ruleset documents (`document_type: table`) so they are hashed
with the rules and carry provenance. This module validates each table's
`data` per `table_kind` and exposes typed views:

- natural relationships (BPHS Ch. 3 v. 55), temporal (v. 56), compound
  (v. 57-58): friend / enemy / equal and the five-fold compound result;
- natural nature (Ch. 3 v. 11) with the labelled Pandit Ji conventions;
- Moolatrikona sign and degree ranges (Ch. 3 v. 51-54);
- the 84-cell BPHS Ch. 34 functional-nature table, source labels preserved.

Nothing here derives a value the source does not give: Rahu and Ketu have no
relationship, Moolatrikona or functional-nature entries, and a cell the verse
does not address is `not_specified_by_source`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pandit_rule_engine.schema import TableDocument
from pandit_rule_engine.vocab import CLASSICAL_BODIES, Body, Sign

Kind = Literal["friend", "enemy", "equal"]
CompoundKind = Literal["great_friend", "friend", "equal", "enemy", "great_enemy"]

#: Closed vocabulary of source labels used in the Ch. 34 table. Each label is
#: the verse's own term; none is a score.
FUNCTIONAL_LABELS = frozenset(
    {
        "auspicious",
        "malefic",
        "neutral",
        "killer",
        "killer_by_association",
        "killer_not_independent",
        "not_killer_of_own",
        "helpful_to_auspicious",
        "somewhat_auspicious",
        "association_dependent",
        "meddling_mixed",
        "yoga",
        "rajayoga",
        "superior_yoga",
        "yogakaraka",
        "rajayoga_with_mercury",
        "yoga_with_sun",
        "yoga_with_mars",
        "yoga_with_mercury",
        "only_auspicious_planet",
        "only_rajayoga_planet",
    }
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NaturalRelationships(_Model):
    friends: dict[Body, tuple[Body, ...]]
    enemies: dict[Body, tuple[Body, ...]]
    note: str = ""

    @model_validator(mode="after")
    def _valid(self) -> NaturalRelationships:
        classical = set(CLASSICAL_BODIES)
        if set(self.friends) != classical or set(self.enemies) != classical:
            raise ValueError("natural relationships must cover exactly the seven classical planets")
        for body in CLASSICAL_BODIES:
            listed = set(self.friends[body]) | set(self.enemies[body])
            if body in listed or not listed <= classical:
                raise ValueError(f"{body.value}: relationships name itself or a non-classical body")
            if set(self.friends[body]) & set(self.enemies[body]):
                raise ValueError(f"{body.value}: a planet is both friend and enemy")
        return self

    def kind(self, a: Body, b: Body) -> Kind:
        if b in self.friends[a]:
            return "friend"
        if b in self.enemies[a]:
            return "enemy"
        return "equal"


class TemporalRelationship(_Model):
    friend_houses: tuple[int, ...]
    note: str = ""

    @model_validator(mode="after")
    def _valid(self) -> TemporalRelationship:
        if not self.friend_houses or any(not 1 <= house <= 12 for house in self.friend_houses):
            raise ValueError("friend_houses must be houses in 1..12")
        return self


class CompoundRow(_Model):
    natural: Kind
    temporal: Literal["friend", "enemy"]
    compound: CompoundKind


class CompoundRelationship(_Model):
    matrix: tuple[CompoundRow, ...]

    @model_validator(mode="after")
    def _complete(self) -> CompoundRelationship:
        keys = {(row.natural, row.temporal) for row in self.matrix}
        expected = {(n, t) for n in ("friend", "enemy", "equal") for t in ("friend", "enemy")}
        if keys != expected or len(self.matrix) != len(expected):
            raise ValueError("compound matrix must cover every natural x temporal pair once")
        return self

    def result(self, natural: Kind, temporal: Literal["friend", "enemy"]) -> CompoundKind:
        for row in self.matrix:
            if row.natural == natural and row.temporal == temporal:
                return row.compound
        raise KeyError((natural, temporal))


class MoonRule(_Model):
    waxing: Literal["benefic"]
    waning: Literal["malefic"]


class MercuryRule(_Model):
    alone_or_with_benefics: Literal["benefic"]
    with_malefic: Literal["malefic"]


class NatureConventions(_Model):
    label: Literal["pandit_ji_convention"]
    moon_waxing_elongation_degrees: tuple[float, float]
    moon_boundary_epsilon_degrees: float = Field(gt=0.0, lt=1.0)
    mercury_joined_with: Literal["same_sign_conjunction_only"]
    mercury_mixed_association: Literal["reading_ambiguous"]
    note: str = ""


class NaturalNatureTable(_Model):
    malefic: tuple[Body, ...]
    benefic: tuple[Body, ...]
    moon: MoonRule
    mercury: MercuryRule
    conventions: NatureConventions

    @model_validator(mode="after")
    def _valid(self) -> NaturalNatureTable:
        listed = list(self.malefic) + list(self.benefic)
        if len(set(listed)) != len(listed):
            raise ValueError("a planet is listed as both benefic and malefic")
        covered = set(listed) | {Body.MOON, Body.MERCURY}
        if covered != set(Body):
            raise ValueError("natural nature must cover all nine bodies (Moon and Mercury by rule)")
        return self


class MoolatrikonaRange(_Model):
    sign: Sign
    from_degree: float = Field(ge=0.0, lt=30.0)
    to_degree: float = Field(gt=0.0, le=30.0)

    @model_validator(mode="after")
    def _ordered(self) -> MoolatrikonaRange:
        if self.from_degree >= self.to_degree:
            raise ValueError("from_degree must be below to_degree")
        return self


class MoolatrikonaTable(_Model):
    ranges: dict[Body, MoolatrikonaRange]
    note: str = ""

    @model_validator(mode="after")
    def _valid(self) -> MoolatrikonaTable:
        if set(self.ranges) != set(CLASSICAL_BODIES):
            raise ValueError("Moolatrikona ranges must cover exactly the seven classical planets")
        return self

    def contains(self, body: Body, sign: Sign, degree_in_sign: float) -> bool:
        entry = self.ranges[body]
        return entry.sign is sign and entry.from_degree <= degree_in_sign < entry.to_degree


class FunctionalCell(_Model):
    labels: tuple[str, ...]
    status: Literal["not_specified_by_source"] | None = None

    @model_validator(mode="after")
    def _valid(self) -> FunctionalCell:
        unknown = set(self.labels) - FUNCTIONAL_LABELS
        if unknown:
            raise ValueError(f"unknown functional-nature labels: {sorted(unknown)}")
        if bool(self.labels) == (self.status is not None):
            raise ValueError("a cell has labels, or is not_specified_by_source, never both/neither")
        return self


class FunctionalLagna(_Model):
    verse: str = Field(min_length=1)
    cells: dict[Body, FunctionalCell]

    @model_validator(mode="after")
    def _seven(self) -> FunctionalLagna:
        if set(self.cells) != set(CLASSICAL_BODIES):
            raise ValueError("each Lagna must have exactly the seven classical planets")
        return self


class FunctionalNatureTable(_Model):
    lagnas: dict[Sign, FunctionalLagna]
    note: str = ""

    @model_validator(mode="after")
    def _twelve(self) -> FunctionalNatureTable:
        if set(self.lagnas) != set(Sign):
            raise ValueError("the functional-nature table must cover all twelve Lagnas (84 cells)")
        return self


class FunctionalValue(_Model):
    """A cell as the source gives it, or why there is none."""

    labels: tuple[str, ...]
    status: Literal["specified", "not_specified_by_source", "outside_table"]
    verse: str | None = None


class Tables(_Model):
    natural_relationships: NaturalRelationships
    temporal_relationship: TemporalRelationship
    compound_relationship: CompoundRelationship
    natural_nature: NaturalNatureTable
    moolatrikona: MoolatrikonaTable
    functional_nature: FunctionalNatureTable

    def functional(self, lagna: Sign, body: Body) -> FunctionalValue:
        if body not in CLASSICAL_BODIES:
            return FunctionalValue(labels=(), status="outside_table")
        lagna_entry = self.functional_nature.lagnas[lagna]
        cell = lagna_entry.cells[body]
        if cell.status is not None:
            return FunctionalValue(labels=(), status=cell.status, verse=lagna_entry.verse)
        return FunctionalValue(labels=cell.labels, status="specified", verse=lagna_entry.verse)


_PARSERS: dict[str, type[_Model]] = {
    "natural_relationships": NaturalRelationships,
    "temporal_relationship": TemporalRelationship,
    "compound_relationship": CompoundRelationship,
    "natural_nature": NaturalNatureTable,
    "moolatrikona": MoolatrikonaTable,
    "functional_nature": FunctionalNatureTable,
}


def validate_table_data(table: TableDocument) -> _Model:
    """Validate one table document's `data`; raises `pydantic.ValidationError`."""
    parser = _PARSERS[table.table_kind]
    return parser.model_validate(table.data)


def build_tables(tables: dict[str, TableDocument]) -> Tables:
    """Typed tables from a ruleset's table documents (exactly one per kind)."""
    by_kind: dict[str, _Model] = {}
    for table in tables.values():
        if table.table_kind in by_kind:
            raise ValueError(f"more than one {table.table_kind} table")
        by_kind[table.table_kind] = validate_table_data(table)
    missing = set(_PARSERS) - set(by_kind)
    if missing:
        raise ValueError(f"missing methodology tables: {sorted(missing)}")
    return Tables.model_validate(by_kind)
