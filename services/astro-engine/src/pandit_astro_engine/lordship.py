"""Sign / house lordship -- Phase 5 (Birth Chart / Kundli Engine).

docs/ASTROLOGY_STANDARDS.md "Sign / House lordship standard": the
traditional 12-sign ruler table. A house's lord is the ruler of whichever
sign occupies that house under the locked whole-sign convention, so house
lordship is derived, never independently defined.
"""

from __future__ import annotations

from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.rashi import Rashi

RASHI_LORD: dict[Rashi, CelestialBody] = {
    Rashi.ARIES: CelestialBody.MARS,
    Rashi.TAURUS: CelestialBody.VENUS,
    Rashi.GEMINI: CelestialBody.MERCURY,
    Rashi.CANCER: CelestialBody.MOON,
    Rashi.LEO: CelestialBody.SUN,
    Rashi.VIRGO: CelestialBody.MERCURY,
    Rashi.LIBRA: CelestialBody.VENUS,
    Rashi.SCORPIO: CelestialBody.MARS,
    Rashi.SAGITTARIUS: CelestialBody.JUPITER,
    Rashi.CAPRICORN: CelestialBody.SATURN,
    Rashi.AQUARIUS: CelestialBody.SATURN,
    Rashi.PISCES: CelestialBody.JUPITER,
}


def sign_lord(rashi: Rashi) -> CelestialBody:
    return RASHI_LORD[rashi]
