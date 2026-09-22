"""Constant Karaka (Phase 9 WP-B-2) -- BPHS Ch. 32 v. 18-21: a static,
longitude-independent planet-to-relative significator table, separate from
Chara Karaka's longitude-ranked roles (`chara_karaka.py`).

The source, in its own words: "I narrate below the constant significators as
related to the planets. The stronger among the Sun and Venus indicates the
father while the stronger among the Moon and Mars indicates the mother.
Mercury denotes sister, brother-in-law, younger brother and mother. Mars
rules maternal relative while Jupiter indicates paternal grand-father.
Husband and sons are respectively denoted by Venus and Saturn. From Ketu
note wife, father, mother, parents-in-law and maternal grand father."

Two of the eight stated significations name "the stronger" of a pair of
planets (Sun-or-Venus for father, Moon-or-Mars for mother) without defining
what "stronger" means anywhere in this chapter. This reproduces a conflict
this project already found and recorded (`research/ASTROLOGY_SOURCES.md`,
"Conflicts found": "Ch. 32 v. 18-21 ... versus Ch. 3 (Sun father, Moon
mother) with 'stronger' undefined"), so both slots are
`NOT_EVALUABLE(strength_undefined)` rather than guessed; the five
single-planet significations are unambiguous and always resolved.

v. 22-24 ("Houses Related": each constant significator's effects read from a
house counted from that significator) is an interpretive-effects layer, not
a fact, and is out of scope under the project's facts-only boundary -- it is
not implemented here.

BPHS's own v. 13 illustration links this system to Chara Karaka's "deficit
of one karaka" case (a tied Dara Karaka falls back to Venus, the constant
husband/wife significator) -- but only that one case is demonstrated, so
this module is deliberately **not** wired as an automatic substitute inside
`chara_karaka.py`'s output; see both modules' docstrings and
`research/ASTROLOGY_SOURCES.md` Group 13.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from pandit_astro_engine.models import CelestialBody


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ConstantKarakaRelation(str, Enum):
    FATHER = "father"
    MOTHER = "mother"
    SIBLING = "sibling"
    MATERNAL_RELATIVE = "maternal_relative"
    PATERNAL_GRANDFATHER = "paternal_grandfather"
    HUSBAND = "husband"
    SONS = "sons"
    KETU_GROUP = "ketu_group"


class ConstantKarakaStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"


class ConstantKarakaReason(str, Enum):
    STRENGTH_UNDEFINED = "strength_undefined"


class ConstantSignificator(_Model):
    relation: ConstantKarakaRelation
    body: CelestialBody | None
    status: ConstantKarakaStatus
    reason_code: ConstantKarakaReason | None


#: The five direct, unambiguous single-planet significations (v. 18-21).
#: `FATHER` (Sun-or-Venus, "the stronger") and `MOTHER` (Moon-or-Mars, "the
#: stronger") are intentionally absent -- see `constant_karakas()`.
_DIRECT_SIGNIFICATORS: dict[ConstantKarakaRelation, CelestialBody] = {
    ConstantKarakaRelation.SIBLING: CelestialBody.MERCURY,
    ConstantKarakaRelation.MATERNAL_RELATIVE: CelestialBody.MARS,
    ConstantKarakaRelation.PATERNAL_GRANDFATHER: CelestialBody.JUPITER,
    ConstantKarakaRelation.HUSBAND: CelestialBody.VENUS,
    ConstantKarakaRelation.SONS: CelestialBody.SATURN,
    ConstantKarakaRelation.KETU_GROUP: CelestialBody.KETU,
}

_UNDEFINED_STRENGTH_RELATIONS: tuple[ConstantKarakaRelation, ...] = (
    ConstantKarakaRelation.FATHER,
    ConstantKarakaRelation.MOTHER,
)


def constant_karakas() -> tuple[ConstantSignificator, ...]:
    """The full, longitude-independent Constant Karaka table: five resolved
    significators plus the two `NOT_EVALUABLE(strength_undefined)` slots
    (father, mother) that this project has no locked "stronger of two
    planets" rule to evaluate. Deterministic: always returns the same eight
    entries, in the same order, since nothing here depends on a chart."""
    entries = [
        ConstantSignificator(
            relation=relation,
            body=None,
            status=ConstantKarakaStatus.NOT_EVALUABLE,
            reason_code=ConstantKarakaReason.STRENGTH_UNDEFINED,
        )
        for relation in _UNDEFINED_STRENGTH_RELATIONS
    ] + [
        ConstantSignificator(
            relation=relation,
            body=body,
            status=ConstantKarakaStatus.SUCCESS,
            reason_code=None,
        )
        for relation, body in _DIRECT_SIGNIFICATORS.items()
    ]
    order = (*_UNDEFINED_STRENGTH_RELATIONS, *_DIRECT_SIGNIFICATORS)
    return tuple(sorted(entries, key=lambda e: order.index(e.relation)))
