"""Planetary aspects (graha drishti) -- Phase 5 (Birth Chart / Kundli Engine).

docs/ASTROLOGY_STANDARDS.md "Planetary aspects standard": Vedic sign/house-
based graha drishti, not Western degree-based aspects. All nine grahas cast
the universal 7th-house aspect; Mars/Jupiter/Saturn cast additional special
aspects; Rahu/Ketu cast only the universal aspect (no special extras).
"""

from __future__ import annotations

from pandit_astro_engine.models import CelestialBody

#: Special aspect offsets ("Nth house from its own placement", counting the
#: planet's own house as 1st -- see `rashi.offset_sign`'s convention) beyond
#: the universal 7th-house aspect every graha casts. Rahu/Ketu and the
#: remaining grahas (Sun, Moon, Mercury, Venus) intentionally have no entry
#: here: they cast only the universal aspect.
_SPECIAL_ASPECT_OFFSETS: dict[CelestialBody, tuple[int, ...]] = {
    CelestialBody.MARS: (4, 8),
    CelestialBody.JUPITER: (5, 9),
    CelestialBody.SATURN: (3, 10),
}

_UNIVERSAL_ASPECT_OFFSET = 7


def aspect_offsets(body: CelestialBody) -> tuple[int, ...]:
    """All house-offsets (counting the planet's own house as 1st) that
    `body` aspects, universal 7th included, sorted ascending."""
    return tuple(sorted((_UNIVERSAL_ASPECT_OFFSET, *_SPECIAL_ASPECT_OFFSETS.get(body, ()))))


def aspected_houses(body: CelestialBody, source_house: int) -> list[int]:
    """`source_house` is 1..12 (the house `body` occupies in some chart).
    Returns the sorted list of houses (1..12) that `body` aspects from
    there, under the locked whole-sign house convention."""
    return sorted({((source_house - 1 + (offset - 1)) % 12) + 1 for offset in aspect_offsets(body)})
