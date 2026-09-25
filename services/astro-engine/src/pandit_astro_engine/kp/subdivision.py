"""KP star, sub and sub-sub lords, and the 249-entry sign-star-sub table
(Phase 9 WP-E; `docs/ASTROLOGY_STANDARDS.md` v1.15.0, KP-05 to KP-07).

KP Reader III ("Predictive Stellar Astrology", OCR, original English):
each 13 degrees 20 minutes constellation is divided into nine subs whose
spans are proportional to the Vimshottari years (span = years x 800/120
arcminutes = years x 400 arcseconds); the first sub belongs to the star
lord and the rest follow the Vimshottari cycle. Counting the subs cut by
a sign boundary twice gives 249 sign-star-sub combinations instead of 243.
The sub-sub division repeats the same proportional rule inside a sub; the
Reader mentions further subdivision only "for research students", so it is
labelled a derived calculation, not a stated rule (KP-06).

All arithmetic is exact (`fractions.Fraction` in arcseconds); intervals are
half-open, lower bound inclusive (engineering convention, KP-07), so an exact
boundary belongs to the later star, sub or sub-sub.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache

from pandit_astro_engine.dashas.constants import (
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_TOTAL_YEARS,
    VIMSHOTTARI_YEARS,
)
from pandit_astro_engine.kp.constants import (
    ARCSEC_PER_DEGREE,
    BOUNDARY_EPSILON_DEGREES,
    KP_TABLE_SIZE,
    NAKSHATRA_ARCSEC,
    SIGN_ARCSEC,
    ZODIAC_ARCSEC,
)
from pandit_astro_engine.lordship import RASHI_LORD
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import NAKSHATRA_LORD, NAKSHATRA_ORDER, Nakshatra
from pandit_astro_engine.rashi import RASHI_ORDER, Rashi


def _cycle_from(lord: CelestialBody) -> tuple[CelestialBody, ...]:
    start = VIMSHOTTARI_SEQUENCE.index(lord)
    return VIMSHOTTARI_SEQUENCE[start:] + VIMSHOTTARI_SEQUENCE[:start]


def _divide(
    start: Fraction, span: Fraction, first_lord: CelestialBody
) -> list[tuple[CelestialBody, Fraction, Fraction]]:
    """Split [start, start + span) among the nine lords, starting with
    `first_lord`, in proportion to their Vimshottari years."""
    parts: list[tuple[CelestialBody, Fraction, Fraction]] = []
    cursor = start
    for lord in _cycle_from(first_lord):
        width = span * VIMSHOTTARI_YEARS[lord] / VIMSHOTTARI_TOTAL_YEARS
        parts.append((lord, cursor, cursor + width))
        cursor += width
    return parts


@dataclass(frozen=True)
class KpLords:
    """Sign, star, sub and sub-sub lordship of one sidereal longitude. The
    `*_start`/`*_end` fields are exact boundaries in degrees, as fractions."""

    sign: Rashi
    sign_lord: CelestialBody
    nakshatra: Nakshatra
    star_lord: CelestialBody
    sub_lord: CelestialBody
    sub_sub_lord: CelestialBody
    sub_start: Fraction
    sub_end: Fraction
    sub_sub_start: Fraction
    sub_sub_end: Fraction
    near_boundary: bool


def _exact_arcsec(longitude: float | Fraction) -> Fraction:
    if not 0 <= longitude < 360:
        raise ValueError(f"longitude must be in [0, 360), got {longitude}")
    return Fraction(longitude) * ARCSEC_PER_DEGREE


def _near(value: Fraction, bounds: tuple[Fraction, ...]) -> bool:
    eps = Fraction(BOUNDARY_EPSILON_DEGREES) * ARCSEC_PER_DEGREE
    return any(abs(value - b) < eps for b in bounds)


def kp_lords(longitude: float | Fraction) -> KpLords:
    """KP lordship of a sidereal longitude in degrees, [0, 360). An exact
    `Fraction` (for example a table boundary) is classified without any
    float rounding."""
    exact = _exact_arcsec(longitude)
    sign_index = int(exact // SIGN_ARCSEC)
    star_index = int(exact // NAKSHATRA_ARCSEC)
    nakshatra = NAKSHATRA_ORDER[star_index]
    star_lord = NAKSHATRA_LORD[nakshatra]
    star_start = Fraction(star_index * NAKSHATRA_ARCSEC)

    subs = _divide(star_start, Fraction(NAKSHATRA_ARCSEC), star_lord)
    sub_lord, sub_start, sub_end = next(p for p in subs if p[1] <= exact < p[2])
    sub_subs = _divide(sub_start, sub_end - sub_start, sub_lord)
    ss_lord, ss_start, ss_end = next(p for p in sub_subs if p[1] <= exact < p[2])

    sign = RASHI_ORDER[sign_index]
    return KpLords(
        sign=sign,
        sign_lord=RASHI_LORD[sign],
        nakshatra=nakshatra,
        star_lord=star_lord,
        sub_lord=sub_lord,
        sub_sub_lord=ss_lord,
        sub_start=sub_start / ARCSEC_PER_DEGREE,
        sub_end=sub_end / ARCSEC_PER_DEGREE,
        sub_sub_start=ss_start / ARCSEC_PER_DEGREE,
        sub_sub_end=ss_end / ARCSEC_PER_DEGREE,
        near_boundary=_near(exact, (ss_start, ss_end)),
    )


@dataclass(frozen=True)
class KpTableEntry:
    """One row of the KP sign-star-sub table. `number` runs 1-249 from 0
    degrees Aries; `start`/`end` are exact degrees, half-open."""

    number: int
    sign: Rashi
    sign_lord: CelestialBody
    nakshatra: Nakshatra
    star_lord: CelestialBody
    sub_lord: CelestialBody
    start: Fraction
    end: Fraction


@lru_cache(maxsize=1)
def kp_table() -> tuple[KpTableEntry, ...]:
    """The 249 sign-star-sub combinations, derived from the proportional rule
    (never transcribed from a printed table). A sub crossing a sign boundary
    becomes two entries, one per sign."""
    rows: list[KpTableEntry] = []
    for star_index, nakshatra in enumerate(NAKSHATRA_ORDER):
        star_lord = NAKSHATRA_LORD[nakshatra]
        star_start = Fraction(star_index * NAKSHATRA_ARCSEC)
        for sub_lord, start, end in _divide(star_start, Fraction(NAKSHATRA_ARCSEC), star_lord):
            pieces = [(start, end)]
            boundary = (start // SIGN_ARCSEC + 1) * SIGN_ARCSEC
            if start < boundary < end:
                pieces = [(start, Fraction(boundary)), (Fraction(boundary), end)]
            for piece_start, piece_end in pieces:
                sign = RASHI_ORDER[int(piece_start // SIGN_ARCSEC)]
                rows.append(
                    KpTableEntry(
                        number=len(rows) + 1,
                        sign=sign,
                        sign_lord=RASHI_LORD[sign],
                        nakshatra=nakshatra,
                        star_lord=star_lord,
                        sub_lord=sub_lord,
                        start=piece_start / ARCSEC_PER_DEGREE,
                        end=piece_end / ARCSEC_PER_DEGREE,
                    )
                )
    if len(rows) != KP_TABLE_SIZE or rows[-1].end * ARCSEC_PER_DEGREE != ZODIAC_ARCSEC:
        raise RuntimeError(f"KP table derivation produced {len(rows)} entries, expected 249")
    return tuple(rows)


def kp_table_entry(number: int) -> KpTableEntry:
    if not 1 <= number <= KP_TABLE_SIZE:
        raise ValueError(f"KP horary number must be 1-{KP_TABLE_SIZE}, got {number}")
    return kp_table()[number - 1]
