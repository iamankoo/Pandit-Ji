"""Western methodology profiles (Phase 9 WP-D; `docs/ASTROLOGY_STANDARDS.md`
v1.14.0, WD-01 to WD-20; sources in `research/ASTROLOGY_SOURCES.md` Group 15).

Every choice that is not fixed by a source is an explicit, named profile
with an evidence label, so a result always says which rule produced it.
Unknown profile IDs are rejected at request validation; nothing falls back
to a different profile.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from pandit_astro_engine.western.constants import ASPECT_ANGLE, AspectType, WesternBody


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceLabel(str, Enum):
    """Same vocabulary as the other phase modules' own copies
    (`dashas.profiles`, `transits.profiles`, `partial_degree_drishti.profiles`)
    -- deliberately not a shared cross-phase import."""

    SOURCE_SUPPORTED = "source_supported"
    TRANSLATOR_NOTE = "translator_note"
    INFERENCE = "inference"
    ENGINEERING_CONVENTION = "engineering_convention"
    DERIVED_CALCULATION = "derived_calculation"
    UNRESOLVED_CONFLICT = "unresolved_conflict"
    MODERN_TRADITION = "modern_tradition"
    ENGINEERING_EVIDENCE = "engineering_evidence"


class SourceReference(_Model):
    source_id: str
    locator: str
    verification_level: str
    note: str = ""


SWISSEPH_DOC = "SRC-SWISSEPH-DOC"
TETRABIBLOS = "SRC-PTOLEMY-TETRABIBLOS-ROBBINS-1940"
LILLY = "SRC-LILLY-CHRISTIAN-ASTROLOGY-1647"

# --------------------------------------------------------------------------
# Zodiac (WD-01, WD-02)
# --------------------------------------------------------------------------

ZODIAC_TROPICAL_ID = "WESTERN_ZODIAC_TROPICAL_OF_DATE"


class ZodiacProfileDef(_Model):
    profile_id: str
    label: EvidenceLabel
    title: str
    references: tuple[SourceReference, ...]


ZODIAC_TROPICAL = ZodiacProfileDef(
    profile_id=ZODIAC_TROPICAL_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title=(
        "Tropical zodiac: 0 degrees Aries at the vernal point; geocentric apparent "
        "ecliptic longitude of date, no ayanamsa"
    ),
    references=(
        SourceReference(
            source_id=SWISSEPH_DOC,
            locator="Section 2.8.1 'The problem of defining the zodiac'",
            verification_level="DOCUMENTATION-DIRECT",
            note=(
                "Western astrology mostly uses the tropical zodiac, with 0 Aries fixed at "
                "the vernal point; the sidereal zodiac drifts from it by precession."
            ),
        ),
    ),
)

# --------------------------------------------------------------------------
# Bodies (WD-03, WD-04, WD-05)
# --------------------------------------------------------------------------

BODIES_CLASSICAL_7_ID = "WESTERN_BODIES_CLASSICAL_7"
BODIES_MODERN_10_ID = "WESTERN_BODIES_MODERN_10"
BODIES_MODERN_10_NODES_ID = "WESTERN_BODIES_MODERN_10_NODES"

_CLASSICAL: tuple[WesternBody, ...] = (
    WesternBody.SUN,
    WesternBody.MOON,
    WesternBody.MERCURY,
    WesternBody.VENUS,
    WesternBody.MARS,
    WesternBody.JUPITER,
    WesternBody.SATURN,
)
_MODERN: tuple[WesternBody, ...] = (
    *_CLASSICAL,
    WesternBody.URANUS,
    WesternBody.NEPTUNE,
    WesternBody.PLUTO,
)


class BodyProfileDef(_Model):
    profile_id: str
    label: EvidenceLabel
    title: str
    bodies: tuple[WesternBody, ...]
    aspect_bodies: tuple[WesternBody, ...]
    requires_node_convention: bool
    references: tuple[SourceReference, ...] = ()


BODIES_CLASSICAL_7 = BodyProfileDef(
    profile_id=BODIES_CLASSICAL_7_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title="The seven classical planets (Sun to Saturn)",
    bodies=_CLASSICAL,
    aspect_bodies=_CLASSICAL,
    requires_node_convention=False,
    references=(
        SourceReference(
            source_id=LILLY,
            locator="Book I, the seven planet chapters (1647 text)",
            verification_level="OCR-ORIGINAL-ENGLISH",
            note="Lilly describes exactly these seven planets, each with its own orb.",
        ),
    ),
)

BODIES_MODERN_10 = BodyProfileDef(
    profile_id=BODIES_MODERN_10_ID,
    label=EvidenceLabel.MODERN_TRADITION,
    title="Seven classical planets plus Uranus, Neptune and Pluto (the default)",
    bodies=_MODERN,
    aspect_bodies=_MODERN,
    requires_node_convention=False,
)

BODIES_MODERN_10_NODES = BodyProfileDef(
    profile_id=BODIES_MODERN_10_NODES_ID,
    label=EvidenceLabel.MODERN_TRADITION,
    title=(
        "The modern ten plus the lunar nodes; the nodes are positions only and never take "
        "part in aspects"
    ),
    bodies=(*_MODERN, WesternBody.NORTH_NODE, WesternBody.SOUTH_NODE),
    aspect_bodies=_MODERN,
    requires_node_convention=True,
)

BODY_PROFILES: dict[str, BodyProfileDef] = {
    p.profile_id: p for p in (BODIES_CLASSICAL_7, BODIES_MODERN_10, BODIES_MODERN_10_NODES)
}
DEFAULT_BODY_PROFILE_ID = BODIES_MODERN_10_ID

# --------------------------------------------------------------------------
# Houses (WD-06, WD-07, WD-08)
# --------------------------------------------------------------------------

HOUSES_PLACIDUS_ID = "WESTERN_HOUSES_PLACIDUS_SWISSEPH"


class HouseProfileDef(_Model):
    profile_id: str
    label: EvidenceLabel
    title: str
    references: tuple[SourceReference, ...]


HOUSES_PLACIDUS = HouseProfileDef(
    profile_id=HOUSES_PLACIDUS_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title=(
        "Placidus (trisection of the semi-diurnal and semi-nocturnal arcs), Swiss "
        "Ephemeris implementation; undefined inside the polar circles"
    ),
    references=(
        SourceReference(
            source_id=SWISSEPH_DOC,
            locator="Section 6.2.1 'Placidus'; section 6.4 'House cusps beyond the polar circle'",
            verification_level="DOCUMENTATION-DIRECT",
            note=(
                "Cusp 11 has completed 2/3 and cusp 12 1/3 of its semi-diurnal arc; cusps 2 "
                "and 3 likewise on the semi-nocturnal arc. Placidus cannot always be computed "
                "beyond the polar circles, where Swiss Ephemeris substitutes Porphyry; this "
                "module never accepts the substitute."
            ),
        ),
        SourceReference(
            source_id=SWISSEPH_DOC,
            locator="Section 6.7 'Improvement of the Placidus house calculation in SE 2.09'",
            verification_level="DOCUMENTATION-DIRECT",
            note=(
                "Iteration to convergence (at most 100 steps); a non-converging case is also "
                "switched to Porphyry with a warning, which this module reports as not "
                "evaluable."
            ),
        ),
    ),
)

HOUSE_PROFILES: dict[str, HouseProfileDef] = {HOUSES_PLACIDUS_ID: HOUSES_PLACIDUS}
DEFAULT_HOUSE_PROFILE_ID = HOUSES_PLACIDUS_ID

# --------------------------------------------------------------------------
# Aspects (WD-09, WD-10)
# --------------------------------------------------------------------------

ASPECTS_PTOLEMAIC_5_ID = "WESTERN_ASPECTS_PTOLEMAIC_5"


class AspectSetProfileDef(_Model):
    profile_id: str
    label: EvidenceLabel
    title: str
    aspects: tuple[AspectType, ...]
    references: tuple[SourceReference, ...]


ASPECTS_PTOLEMAIC_5 = AspectSetProfileDef(
    profile_id=ASPECTS_PTOLEMAIC_5_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title="Conjunction, sextile, square, trine and opposition",
    aspects=tuple(AspectType),
    references=(
        SourceReference(
            source_id=TETRABIBLOS,
            locator="Book I ch. 13 'Of the Aspects of the Signs' and Robbins's note to it",
            verification_level="WEB-TRANSCRIPTION-TRANSLATION",
            note=(
                "Ptolemy names opposition (180), trine (120), quartile (90) and sextile (60). "
                "Robbins's note: Ptolemy does not class the conjunction as an aspect, although "
                "it is treated as one throughout the Tetrabiblos; Kepler's added aspects are "
                "inconsistent with Ptolemy's doctrine. Ptolemy's aspects are between signs."
            ),
        ),
        SourceReference(
            source_id=LILLY,
            locator="Book I, chapter on the aspects (partile and platick aspects), 1647 text",
            verification_level="OCR-ORIGINAL-ENGLISH",
            note=(
                "Lilly uses the same five, including the conjunction, and measures them in "
                "degrees with orbs."
            ),
        ),
    ),
)

ASPECT_SET_PROFILES: dict[str, AspectSetProfileDef] = {ASPECTS_PTOLEMAIC_5_ID: ASPECTS_PTOLEMAIC_5}
DEFAULT_ASPECT_SET_PROFILE_ID = ASPECTS_PTOLEMAIC_5_ID

# --------------------------------------------------------------------------
# Orbs (WD-11, WD-12, WD-13)
# --------------------------------------------------------------------------

ORB_FIXED_V1_ID = "WESTERN_ORB_FIXED_V1"
ORB_LILLY_MOIETY_ID = "WESTERN_ORB_LILLY_1647_MOIETY"


class OrbMethod(str, Enum):
    PER_ASPECT = "per_aspect"
    PLANET_MOIETY = "planet_moiety"


class OrbProfileDef(_Model):
    profile_id: str
    label: EvidenceLabel
    title: str
    method: OrbMethod
    per_aspect_orb: dict[AspectType, float] = {}
    planet_orb: dict[WesternBody, float] = {}
    references: tuple[SourceReference, ...] = ()


ORB_FIXED_V1 = OrbProfileDef(
    profile_id=ORB_FIXED_V1_ID,
    label=EvidenceLabel.ENGINEERING_CONVENTION,
    title=(
        "Pandit Ji fixed orbs by aspect: 8 degrees for conjunction, square, trine and "
        "opposition; 6 degrees for sextile; same for every body (the default)"
    ),
    method=OrbMethod.PER_ASPECT,
    per_aspect_orb={
        AspectType.CONJUNCTION: 8.0,
        AspectType.SEXTILE: 6.0,
        AspectType.SQUARE: 8.0,
        AspectType.TRINE: 8.0,
        AspectType.OPPOSITION: 8.0,
    },
)

ORB_LILLY_MOIETY = OrbProfileDef(
    profile_id=ORB_LILLY_MOIETY_ID,
    label=EvidenceLabel.SOURCE_SUPPORTED,
    title=(
        "Lilly's per-planet orbs from the planet chapters, combined by moiety (half of each "
        "planet's orb, added); the same for every aspect; defined for the seven classical "
        "planets only"
    ),
    method=OrbMethod.PLANET_MOIETY,
    planet_orb={
        WesternBody.SATURN: 9.0,
        WesternBody.JUPITER: 9.0,
        WesternBody.MARS: 7.0,
        WesternBody.SUN: 15.0,
        WesternBody.VENUS: 7.0,
        WesternBody.MERCURY: 7.0,
        WesternBody.MOON: 12.0,
    },
    references=(
        SourceReference(
            source_id=LILLY,
            locator=(
                "Book I planet chapters, 'Orbe' entries (1647 text; Mars read from the 1659 "
                "text only)"
            ),
            verification_level="OCR-ORIGINAL-ENGLISH",
            note=(
                "Saturn 9, Jupiter 9, Mars 7, Sun 15, Venus 7, Mercury 7, Moon 12 degrees "
                "'before and after' any aspect."
            ),
        ),
        SourceReference(
            source_id=LILLY,
            locator="Book I, chapter on the aspects: platick aspect and separation (1647 text)",
            verification_level="OCR-ORIGINAL-ENGLISH",
            note=(
                "A platick aspect is within the moiety (half) of both planets' orbs; each "
                "planet is allowed half its own orb and half the other's. Lilly's own worked "
                "platick example uses moieties Saturn 5 and Venus 4 (orbs 10 and 8), which "
                "disagrees with the planet chapters; the table printed after it is illegible "
                "in the OCR. Recorded as an unresolved conflict; not implemented as a profile."
            ),
        ),
    ),
)

ORB_PROFILES: dict[str, OrbProfileDef] = {p.profile_id: p for p in (ORB_FIXED_V1, ORB_LILLY_MOIETY)}
DEFAULT_ORB_PROFILE_ID = ORB_FIXED_V1_ID

# --------------------------------------------------------------------------
# Motion (WD-14)
# --------------------------------------------------------------------------

MOTION_INSTANTANEOUS_ID = "WESTERN_MOTION_INSTANTANEOUS_V1"


class MotionProfileDef(_Model):
    profile_id: str
    label: EvidenceLabel
    title: str
    references: tuple[SourceReference, ...]


MOTION_INSTANTANEOUS = MotionProfileDef(
    profile_id=MOTION_INSTANTANEOUS_ID,
    label=EvidenceLabel.ENGINEERING_CONVENTION,
    title=(
        "Applying when the distance from the exact aspect angle is decreasing at the chart "
        "instant (from the two bodies' longitudinal speeds), separating when increasing"
    ),
    references=(
        SourceReference(
            source_id=LILLY,
            locator="Book I, chapter on the aspects: application and separation (1647 text)",
            verification_level="OCR-ORIGINAL-ENGLISH",
            note=(
                "Lilly's three ways of application (the swifter planet approaching the "
                "slower when both are direct, both retrograde, or one retrograde) all describe "
                "a closing distance; reading them as the sign of the rate of change is a "
                "Pandit Ji inference."
            ),
        ),
        SourceReference(
            source_id=TETRABIBLOS,
            locator="Book I ch. 24 'Of Applications and Separations'",
            verification_level="WEB-TRANSCRIPTION-TRANSLATION",
            note=(
                "Application and separation 'when the interval between them is not great'; "
                "no number is given."
            ),
        ),
    ),
)

MOTION_PROFILES: dict[str, MotionProfileDef] = {MOTION_INSTANTANEOUS_ID: MOTION_INSTANTANEOUS}


def max_orb(
    profile: OrbProfileDef, aspect: AspectType, a: WesternBody, b: WesternBody
) -> float | None:
    """Allowed deviation from the exact angle for this pair and aspect, or
    `None` when the profile defines no orb for one of the bodies."""
    if profile.method is OrbMethod.PER_ASPECT:
        return profile.per_aspect_orb[aspect]
    orb_a = profile.planet_orb.get(a)
    orb_b = profile.planet_orb.get(b)
    if orb_a is None or orb_b is None:
        return None
    return orb_a / 2.0 + orb_b / 2.0


def largest_possible_orb(profile: OrbProfileDef) -> float:
    if profile.method is OrbMethod.PER_ASPECT:
        return max(profile.per_aspect_orb.values())
    orbs = sorted(profile.planet_orb.values(), reverse=True)
    return orbs[0] / 2.0 + orbs[1] / 2.0


def smallest_aspect_gap(aspects: tuple[AspectType, ...]) -> float:
    angles = sorted(ASPECT_ANGLE[a] for a in aspects)
    return min(b - a for a, b in zip(angles, angles[1:], strict=False))
