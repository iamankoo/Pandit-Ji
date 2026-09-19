"""Builds Phase 5 Kundli-shaped JSON for tests and golden fixtures.

The rule engine consumes Phase 5 output; it never computes positions. Tests
therefore describe a chart by *placements* (sign and degree per body) and
this module renders them into the JSON shape of `Kundli.model_dump(mode="json")`
using the locked standards tables (lordship, dignity, graha drishti), exactly
as Phase 5 defines them. The result is then read through the production
adapter, so the adapter is exercised by every test.
"""

from __future__ import annotations

from typing import Any

from pandit_rule_engine.adapters import facts_from_kundli
from pandit_rule_engine.facts import ChartFacts

SIGNS = (
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
)
BODIES = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu")

# docs/ASTROLOGY_STANDARDS.md §Sign / House lordship standard
LORDS = {
    "aries": "mars",
    "taurus": "venus",
    "gemini": "mercury",
    "cancer": "moon",
    "leo": "sun",
    "virgo": "mercury",
    "libra": "venus",
    "scorpio": "mars",
    "sagittarius": "jupiter",
    "capricorn": "saturn",
    "aquarius": "saturn",
    "pisces": "jupiter",
}
# docs/ASTROLOGY_STANDARDS.md §Planetary dignity standard (sign level)
EXALTATION = {
    "sun": "aries",
    "moon": "taurus",
    "mars": "capricorn",
    "mercury": "virgo",
    "jupiter": "cancer",
    "venus": "pisces",
    "saturn": "libra",
}
DEBILITATION = {
    "sun": "libra",
    "moon": "scorpio",
    "mars": "cancer",
    "mercury": "pisces",
    "jupiter": "capricorn",
    "venus": "virgo",
    "saturn": "aries",
}
# docs/ASTROLOGY_STANDARDS.md §Planetary aspects standard
ASPECT_OFFSETS = {"mars": (4, 7, 8), "jupiter": (5, 7, 9), "saturn": (3, 7, 10)}

Placement = str | tuple[str, float]


def _dignity(body: str, sign: str) -> str | None:
    if body in ("rahu", "ketu"):
        return None
    if EXALTATION[body] == sign:
        return "exalted"
    if DEBILITATION[body] == sign:
        return "debilitated"
    if LORDS[sign] == body:
        return "own_sign"
    return "neutral"


def kundli_dict(
    lagna: str,
    placements: dict[str, Placement],
    *,
    retrograde: frozenset[str] = frozenset(),
    combust: frozenset[str] = frozenset(),
    standards_version: str = "1.3.0",
    timezone: str = "Asia/Kolkata",
) -> dict[str, Any]:
    """A Phase 5 Kundli in JSON form. `placements` maps body -> sign or
    (sign, degree_in_sign); bodies not listed are omitted from the chart."""
    lagna_index = SIGNS.index(lagna)
    houses = [
        {
            "house": number,
            "rashi": SIGNS[(lagna_index + number - 1) % 12],
            "lord": LORDS[SIGNS[(lagna_index + number - 1) % 12]],
        }
        for number in range(1, 13)
    ]
    planets: list[dict[str, Any]] = []
    for body in BODIES:
        if body not in placements:
            continue
        placement = placements[body]
        sign, degree = (placement, 10.0) if isinstance(placement, str) else placement
        sign_index = SIGNS.index(sign)
        house = (sign_index - lagna_index) % 12 + 1
        offsets = ASPECT_OFFSETS.get(body, (7,))
        planets.append(
            {
                "body": body,
                "longitude": sign_index * 30.0 + degree,
                "rashi": sign,
                "degree_in_sign": degree,
                "house": house,
                "dignity": _dignity(body, sign),
                "retrograde": body in retrograde,
                "combust": None if body in ("sun", "rahu", "ketu") else body in combust,
                "aspected_houses": sorted(
                    {(house - 1 + offset - 1) % 12 + 1 for offset in offsets}
                ),
            }
        )
    return {
        "astronomical": {
            "metadata": {
                "engine_version": "test-astro",
                "calculation_config": {
                    "zodiac": "sidereal",
                    "ayanamsa": "lahiri",
                    "node_convention": "mean",
                },
                "time_resolution": {
                    "timezone": timezone,
                    "input_local_datetime": "2000-01-01T06:00:00",
                    "utc_datetime": "2000-01-01T00:30:00+00:00",
                },
                "location": {"latitude": 28.61, "longitude": 77.2, "altitude_meters": 0.0},
            }
        },
        "lagna": {"rashi": lagna, "degree_in_sign": 5.0},
        "houses": houses,
        "planets": planets,
        "metadata": {
            "engine_version": "test-astro",
            "standards_version": standards_version,
            "house_system": "vedic_whole_sign",
            "varga_scheme": "classical_parashari_v1",
            "aspect_standard": "vedic_graha_drishti_v1",
            "dignity_standard": "classical_exaltation_debilitation_v1",
        },
    }


def chart(
    lagna: str,
    placements: dict[str, Placement],
    **kwargs: Any,
) -> ChartFacts:
    return facts_from_kundli(kundli_dict(lagna, placements, **kwargs))


def full_placements(**signs: Placement) -> dict[str, Placement]:
    """Placements for all nine bodies; unspecified bodies sit in Aries."""
    return {body: signs.get(body, "aries") for body in BODIES}
