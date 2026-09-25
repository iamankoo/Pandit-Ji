"""Pure KP significator and Ruling Planets functions on hand-built charts
(Phase 9 WP-E, KP-04, KP-08 to KP-10)."""

from __future__ import annotations

import pytest

from pandit_astro_engine.kp.ruling_planets import (
    RetrogradeStarFlag,
    RulingRole,
    ruling_planets,
)
from pandit_astro_engine.kp.significators import (
    house_lord,
    house_of,
    house_significators,
    planet_significations,
)
from pandit_astro_engine.kp.subdivision import kp_lords
from pandit_astro_engine.models import CelestialBody as B

#: Equal 30-degree cusps starting at 15 Aries, so house n spans 15 deg of one
#: sign to 15 deg of the next.
CUSPS = tuple(15.0 + 30.0 * i for i in range(12))


def test_house_of_half_open_and_wrapping() -> None:
    assert house_of(15.0, CUSPS) == 1
    assert house_of(44.999999, CUSPS) == 1
    assert house_of(45.0, CUSPS) == 2
    assert house_of(14.9, CUSPS) == 12  # wraps through 0 Aries
    assert house_of(0.0, CUSPS) == 12
    uneven = (350.0, 20.0, 40.0, 70.0, 110.0, 150.0, 170.0, 200.0, 220.0, 250.0, 290.0, 330.0)
    assert house_of(355.0, uneven) == 1
    assert house_of(5.0, uneven) == 1
    assert house_of(345.0, uneven) == 12


def test_house_of_requires_twelve_cusps() -> None:
    with pytest.raises(ValueError):
        house_of(10.0, CUSPS[:11])


def test_house_lord_is_the_cusp_sign_lord() -> None:
    assert house_lord(15.0) is B.MARS
    assert house_lord(45.0) is B.VENUS
    assert house_lord(345.0) is B.JUPITER


def test_four_levels() -> None:
    # Moon at 20 Aries (house 1, Bharani = Venus star); Venus at 50 (house 2,
    # Rohini = Moon star); Mars at 196 (house 7, Swati = Rahu star).
    longitudes = {B.MOON: 20.0, B.VENUS: 50.0, B.MARS: 196.0}
    stars = {b: kp_lords(lon).star_lord for b, lon in longitudes.items()}
    assert stars == {B.MOON: B.VENUS, B.VENUS: B.MOON, B.MARS: B.RAHU}
    result = house_significators(CUSPS, longitudes, stars)
    assert result[1] == {"a": (B.VENUS,), "b": (B.MOON,), "c": (), "d": (B.MARS,)}
    # House 2: cusp 45 (Taurus), lord Venus; the Moon is in Venus's star.
    assert result[2] == {"a": (B.MOON,), "b": (B.VENUS,), "c": (B.MOON,), "d": (B.VENUS,)}
    assert result[7]["b"] == (B.MARS,)
    assert result[7]["d"] == (B.VENUS,)
    assert result[7]["a"] == ()  # nothing is in Mars's star
    assert result[7]["c"] == (B.MOON,)  # the Moon is in Venus's star
    inverse = planet_significations(result)
    assert 1 in inverse[B.MOON] and 2 in inverse[B.MOON] and 7 in inverse[B.MOON]


def _all(**overrides: float) -> dict[B, float]:
    base = {
        B.SUN: 100.0,
        B.MOON: 20.0,  # Aries, Bharani (Venus star)
        B.MARS: 255.0,  # Sagittarius, Purva Ashadha (Venus star)
        B.MERCURY: 110.0,
        B.JUPITER: 130.0,
        B.VENUS: 60.0,
        B.SATURN: 300.0,
        B.RAHU: 5.0,  # Aries, owned by Mars
        B.KETU: 185.0,  # Libra, owned by Venus
    }
    base.update({B[k.upper()]: v for k, v in overrides.items()})
    return base


def test_ruling_planets_members_and_node_agents() -> None:
    lons = _all()
    retro = {b: False for b in lons}
    members = ruling_planets(
        ascendant=190.0, longitudes=lons, retrograde=retro, weekday_sunday_zero=2
    )
    # Ascendant 190: Libra (Venus), Swati (Rahu star). Moon: Aries (Mars), Venus star.
    # Tuesday: Mars.
    assert [(m.body, m.role) for m in members[:5]] == [
        (B.RAHU, RulingRole.ASCENDANT_STAR_LORD),
        (B.VENUS, RulingRole.ASCENDANT_SIGN_LORD),
        (B.VENUS, RulingRole.MOON_STAR_LORD),
        (B.MARS, RulingRole.MOON_SIGN_LORD),
        (B.MARS, RulingRole.DAY_LORD),
    ]
    agents = {(m.body, m.represents) for m in members[5:]}
    assert agents == {(B.RAHU, B.MARS), (B.KETU, B.VENUS)}


def test_node_not_added_when_its_sign_lord_is_not_a_sign_or_day_ruler() -> None:
    lons = _all(rahu=95.0, ketu=275.0)  # Cancer (Moon), Capricorn (Saturn)
    members = ruling_planets(
        ascendant=190.0, longitudes=lons, retrograde={b: False for b in lons}, weekday_sunday_zero=2
    )
    assert all(m.role is not RulingRole.NODE_AGENT for m in members)


def test_retrograde_star_flags() -> None:
    lons = _all()
    retro = {b: False for b in lons}
    retro[B.VENUS] = True
    members = ruling_planets(
        ascendant=190.0, longitudes=lons, retrograde=retro, weekday_sunday_zero=2
    )
    by_role = {m.role: m for m in members}
    # Mars (Moon sign lord) at 255 is in Purva Ashadha, a Venus star.
    assert by_role[RulingRole.MOON_SIGN_LORD].star_lord_of_body is B.VENUS
    assert (
        by_role[RulingRole.MOON_SIGN_LORD].retrograde_star_flag
        is RetrogradeStarFlag.IN_STAR_OF_RETROGRADE
    )
    # Venus at 60 is in Mrigashira (Mars star), Mars direct.
    assert (
        by_role[RulingRole.ASCENDANT_SIGN_LORD].retrograde_star_flag
        is RetrogradeStarFlag.NOT_IN_STAR_OF_RETROGRADE
    )
    # The Ascendant star lord Rahu sits at 5 Aries (Ashwini, a Ketu star).
    assert (
        by_role[RulingRole.ASCENDANT_STAR_LORD].retrograde_star_flag
        is RetrogradeStarFlag.NODE_RETROGRESSION_UNRESOLVED
    )


def test_ruling_planets_validation() -> None:
    lons = _all()
    with pytest.raises(ValueError):
        ruling_planets(ascendant=1.0, longitudes=lons, retrograde={}, weekday_sunday_zero=7)
    partial = dict(lons)
    del partial[B.KETU]
    with pytest.raises(ValueError):
        ruling_planets(ascendant=1.0, longitudes=partial, retrograde={}, weekday_sunday_zero=0)
