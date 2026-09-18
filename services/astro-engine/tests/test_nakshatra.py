import pytest

from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import (
    NAKSHATRA_LORD,
    NAKSHATRA_ORDER,
    Nakshatra,
    nakshatra_position,
)


def test_27_nakshatras_defined() -> None:
    assert len(NAKSHATRA_ORDER) == 27
    assert len(set(NAKSHATRA_ORDER)) == 27


def test_lord_cycle_repeats_nine_lords_three_times() -> None:
    expected_cycle = [
        CelestialBody.KETU,
        CelestialBody.VENUS,
        CelestialBody.SUN,
        CelestialBody.MOON,
        CelestialBody.MARS,
        CelestialBody.RAHU,
        CelestialBody.JUPITER,
        CelestialBody.SATURN,
        CelestialBody.MERCURY,
    ]
    lords = [NAKSHATRA_LORD[nakshatra] for nakshatra in NAKSHATRA_ORDER]
    assert lords == expected_cycle * 3


@pytest.mark.parametrize(
    ("longitude", "expected_nakshatra", "expected_pada"),
    [
        (0.0, Nakshatra.ASHWINI, 1),
        (3.0, Nakshatra.ASHWINI, 1),
        (3.3333334, Nakshatra.ASHWINI, 2),
        (13.0, Nakshatra.ASHWINI, 4),
        (13.3333334, Nakshatra.BHARANI, 1),
        (359.9, Nakshatra.REVATI, 4),
        (360.0, Nakshatra.ASHWINI, 1),  # normalizes
    ],
)
def test_nakshatra_pada_boundaries(
    longitude: float, expected_nakshatra: Nakshatra, expected_pada: int
) -> None:
    position = nakshatra_position(longitude)
    assert position.nakshatra is expected_nakshatra
    assert position.pada == expected_pada


def test_nakshatra_lord_matches_table() -> None:
    position = nakshatra_position(0.0)
    assert position.lord == NAKSHATRA_LORD[Nakshatra.ASHWINI] == CelestialBody.KETU


def test_near_boundary_flag() -> None:
    exact = nakshatra_position(13.333333333333334)  # exactly on Ashwini/Bharani boundary
    assert exact.near_boundary is True

    mid = nakshatra_position(6.0)
    assert mid.near_boundary is False


def test_27_full_cycle_covers_every_nakshatra_once() -> None:
    span = 360.0 / 27.0
    seen = {nakshatra_position(index * span + 1.0).nakshatra for index in range(27)}
    assert seen == set(Nakshatra)
