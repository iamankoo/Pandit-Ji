"""Nakshatra / Pada -- Phase 5 (Birth Chart / Kundli Engine).

docs/ASTROLOGY_STANDARDS.md "Nakshatra standards": 27 Nakshatras of 13°20'
each spanning the full sidereal zodiac, 4 Padas of 3°20' each, and the nine
Vimshottari lords repeating three times across the 27 Nakshatras.

Classification convention (a Pandit Ji engineering convention, not a rule
stated by a classical source): Nakshatra and Pada intervals are half-open,
lower-inclusive and upper-exclusive, so an exact boundary belongs to the upper
Nakshatra/Pada, and 360 degrees is 0 degrees. Classification uses exact
rational arithmetic on the input float, because the float divisor 360.0/27.0
is not exactly 13 degrees 20 minutes.
"""

from __future__ import annotations

from enum import Enum
from fractions import Fraction

from pandit_astro_engine.models import CelestialBody

#: 30/27 degrees, exact -- do not approximate with a rounded float literal.
NAKSHATRA_SPAN_DEGREES = 360.0 / 27.0
PADA_SPAN_DEGREES = NAKSHATRA_SPAN_DEGREES / 4.0

#: Floating-point tolerance for flagging a longitude that falls essentially
#: exactly on a Nakshatra/Pada boundary, per the standard's "must be flagged
#: for review rather than silently rounded" requirement. This is a numeric
#: epsilon (about 0.0036 arcseconds), not an astrological judgment.
_BOUNDARY_EPSILON_DEGREES = 1e-6


class Nakshatra(str, Enum):
    ASHWINI = "ashwini"
    BHARANI = "bharani"
    KRITTIKA = "krittika"
    ROHINI = "rohini"
    MRIGASHIRA = "mrigashira"
    ARDRA = "ardra"
    PUNARVASU = "punarvasu"
    PUSHYA = "pushya"
    ASHLESHA = "ashlesha"
    MAGHA = "magha"
    PURVA_PHALGUNI = "purva_phalguni"
    UTTARA_PHALGUNI = "uttara_phalguni"
    HASTA = "hasta"
    CHITRA = "chitra"
    SWATI = "swati"
    VISHAKHA = "vishakha"
    ANURADHA = "anuradha"
    JYESHTHA = "jyeshtha"
    MULA = "mula"
    PURVA_ASHADHA = "purva_ashadha"
    UTTARA_ASHADHA = "uttara_ashadha"
    SHRAVANA = "shravana"
    DHANISHTA = "dhanishta"
    SHATABHISHA = "shatabhisha"
    PURVA_BHADRAPADA = "purva_bhadrapada"
    UTTARA_BHADRAPADA = "uttara_bhadrapada"
    REVATI = "revati"


NAKSHATRA_ORDER: tuple[Nakshatra, ...] = tuple(Nakshatra)

#: The nine Vimshottari lords, repeating three times across the 27
#: Nakshatras (9 x 3 = 27) -- the exact sequence locked in
#: docs/ASTROLOGY_STANDARDS.md "Nakshatra standards".
_VIMSHOTTARI_LORD_CYCLE: tuple[CelestialBody, ...] = (
    CelestialBody.KETU,
    CelestialBody.VENUS,
    CelestialBody.SUN,
    CelestialBody.MOON,
    CelestialBody.MARS,
    CelestialBody.RAHU,
    CelestialBody.JUPITER,
    CelestialBody.SATURN,
    CelestialBody.MERCURY,
)

NAKSHATRA_LORD: dict[Nakshatra, CelestialBody] = {
    nakshatra: _VIMSHOTTARI_LORD_CYCLE[index % 9] for index, nakshatra in enumerate(NAKSHATRA_ORDER)
}


class NakshatraPosition:
    __slots__ = ("nakshatra", "pada", "lord", "near_boundary")

    def __init__(
        self, nakshatra: Nakshatra, pada: int, lord: CelestialBody, near_boundary: bool
    ) -> None:
        self.nakshatra = nakshatra
        self.pada = pada
        self.lord = lord
        self.near_boundary = near_boundary


def _near_boundary(longitude: float, span_degrees: float) -> bool:
    remainder = longitude % span_degrees
    return (
        remainder < _BOUNDARY_EPSILON_DEGREES
        or (span_degrees - remainder) < _BOUNDARY_EPSILON_DEGREES
    )


def nakshatra_position(longitude: float) -> NakshatraPosition:
    """`longitude` is an absolute sidereal ecliptic longitude, degrees
    [0, 360)."""
    normalized = longitude % 360.0
    # Exact rational classification: `exact` is the float's exact value, so
    # 27/360 and 108/360 divisions carry no rounding. `% 360` maps a float
    # normalization result of 360.0 to 0.
    exact = Fraction(normalized) % 360
    nakshatra_index = (exact * 27) // 360
    pada = int((exact * 108) // 360) % 4 + 1
    position_in_nakshatra = normalized - (nakshatra_index * NAKSHATRA_SPAN_DEGREES)

    nakshatra = NAKSHATRA_ORDER[nakshatra_index]
    return NakshatraPosition(
        nakshatra=nakshatra,
        pada=pada,
        lord=NAKSHATRA_LORD[nakshatra],
        near_boundary=_near_boundary(normalized, NAKSHATRA_SPAN_DEGREES)
        or _near_boundary(position_in_nakshatra, PADA_SPAN_DEGREES),
    )
