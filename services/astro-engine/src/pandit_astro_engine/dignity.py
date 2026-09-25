"""Planetary dignity -- Phase 5 (Birth Chart / Kundli Engine).

docs/ASTROLOGY_STANDARDS.md "Planetary dignity standard": exaltation,
debilitation (both at exact degrees), own-sign, and neutral. Mooltrikona is
explicitly out of scope for Phase 5 (documented deferral, not a silent
omission) -- do not add it here without a corresponding standards-document
update. Rahu/Ketu are not evaluated under this standard.
"""

from __future__ import annotations

from enum import Enum

from pandit_astro_engine.lordship import RASHI_LORD
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.rashi import Rashi


class DignityStatus(str, Enum):
    EXALTED = "exalted"
    DEBILITATED = "debilitated"
    OWN_SIGN = "own_sign"
    NEUTRAL = "neutral"


class ExaltationPoint:
    __slots__ = ("rashi", "degree")

    def __init__(self, rashi: Rashi, degree: float) -> None:
        self.rashi = rashi
        self.degree = degree


#: (exaltation point, debilitation point) per graha, exact degrees per the
#: locked standard. Rahu/Ketu deliberately absent -- no classical
#: exaltation/debilitation degree consensus is asserted for the nodes here.
_EXALTATION: dict[CelestialBody, ExaltationPoint] = {
    CelestialBody.SUN: ExaltationPoint(Rashi.ARIES, 10.0),
    CelestialBody.MOON: ExaltationPoint(Rashi.TAURUS, 3.0),
    CelestialBody.MARS: ExaltationPoint(Rashi.CAPRICORN, 28.0),
    CelestialBody.MERCURY: ExaltationPoint(Rashi.VIRGO, 15.0),
    CelestialBody.JUPITER: ExaltationPoint(Rashi.CANCER, 5.0),
    CelestialBody.VENUS: ExaltationPoint(Rashi.PISCES, 27.0),
    CelestialBody.SATURN: ExaltationPoint(Rashi.LIBRA, 20.0),
}

_DEBILITATION: dict[CelestialBody, ExaltationPoint] = {
    CelestialBody.SUN: ExaltationPoint(Rashi.LIBRA, 10.0),
    CelestialBody.MOON: ExaltationPoint(Rashi.SCORPIO, 3.0),
    CelestialBody.MARS: ExaltationPoint(Rashi.CANCER, 28.0),
    CelestialBody.MERCURY: ExaltationPoint(Rashi.PISCES, 15.0),
    CelestialBody.JUPITER: ExaltationPoint(Rashi.CAPRICORN, 5.0),
    CelestialBody.VENUS: ExaltationPoint(Rashi.VIRGO, 27.0),
    CelestialBody.SATURN: ExaltationPoint(Rashi.ARIES, 20.0),
}

#: Own signs, derived from the lordship table (§Sign/House lordship
#: standard) rather than re-declared, so the two tables can never drift.
_OWN_SIGNS: dict[CelestialBody, tuple[Rashi, ...]] = {
    body: tuple(rashi for rashi, lord in RASHI_LORD.items() if lord == body)
    for body in (
        CelestialBody.SUN,
        CelestialBody.MOON,
        CelestialBody.MARS,
        CelestialBody.MERCURY,
        CelestialBody.JUPITER,
        CelestialBody.VENUS,
        CelestialBody.SATURN,
    )
}

#: Evaluable bodies under this standard -- Rahu/Ketu excluded, per the
#: standards document.
DIGNITY_EVALUATED_BODIES: frozenset[CelestialBody] = frozenset(_EXALTATION)


def evaluate_dignity(
    body: CelestialBody, rashi: Rashi, degree_in_sign: float
) -> DignityStatus | None:
    """`degree_in_sign` is 0.0..30.0 (see `rashi.degree_within_sign`).
    Returns `None` for Rahu/Ketu (not evaluated under this standard)."""
    if body not in DIGNITY_EVALUATED_BODIES:
        return None

    exaltation = _EXALTATION[body]
    if rashi == exaltation.rashi:
        return DignityStatus.EXALTED

    debilitation = _DEBILITATION[body]
    if rashi == debilitation.rashi:
        return DignityStatus.DEBILITATED

    if rashi in _OWN_SIGNS[body]:
        return DignityStatus.OWN_SIGN

    return DignityStatus.NEUTRAL


def debilitation_point(body: CelestialBody) -> tuple[Rashi, float]:
    """(sign, degree) of the deep debilitation point of a classical planet,
    from the table above. Used by Uchcha Bala (Phase 9 WP-F, SB-03); raises
    `KeyError` for Rahu/Ketu, which have no point under this standard."""
    point = _DEBILITATION[body]
    return point.rashi, point.degree
