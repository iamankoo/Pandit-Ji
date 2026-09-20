import math
from fractions import Fraction

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


# ---------------------------------------------------------------------------
# Exact-boundary regression tests (Phase 5 patch).
#
# Convention (a Pandit Ji engineering convention, not a classical source rule):
# Nakshatra and Pada intervals are half-open, [lower, upper). An exact boundary
# belongs to the upper Nakshatra/Pada, and 360 degrees is 0 degrees. The
# expected values below are derived independently with exact Fractions.
# ---------------------------------------------------------------------------

_PADA_BOUNDARY_FRACTIONS = [Fraction(k * 10, 3) for k in range(108)]  # k * 3 deg 20 min
_LEAP = math.nextafter


def _exact_expected(longitude: float) -> tuple[Nakshatra, int]:
    exact = Fraction(longitude) % 360
    slot = int(exact * 108 // 360)
    return NAKSHATRA_ORDER[slot // 4], slot % 4 + 1


@pytest.mark.parametrize("index", range(27))
def test_exact_nakshatra_boundary_belongs_to_the_upper_nakshatra(index: int) -> None:
    boundary = Fraction(index * 40, 3)  # index * 13 deg 20 min
    position = nakshatra_position(float(boundary))
    # float(boundary) can differ from the true boundary by less than 1 ulp, so
    # classify the exact float value independently rather than assume the side.
    assert (position.nakshatra, position.pada) == _exact_expected(float(boundary))


@pytest.mark.parametrize(
    ("longitude", "expected_nakshatra", "expected_pada"),
    [
        (40.0, Nakshatra.ROHINI, 1),  # 3 x 13 deg 20 min: was Krittika pada 4
        (10.0, Nakshatra.ASHWINI, 4),  # 3 x 3 deg 20 min: was pada 3
        (20.0, Nakshatra.BHARANI, 3),
        (30.0, Nakshatra.KRITTIKA, 2),
        (80.0, Nakshatra.PUNARVASU, 1),
        (120.0, Nakshatra.MAGHA, 1),
        (200.0, Nakshatra.VISHAKHA, 1),
        (240.0, Nakshatra.MULA, 1),
        (280.0, Nakshatra.SHRAVANA, 1),
        (320.0, Nakshatra.PURVA_BHADRAPADA, 1),
    ],
)
def test_exactly_representable_boundaries_go_to_the_upper_bucket(
    longitude: float, expected_nakshatra: Nakshatra, expected_pada: int
) -> None:
    position = nakshatra_position(longitude)
    assert position.nakshatra is expected_nakshatra
    assert position.pada == expected_pada
    assert position.near_boundary is True


def test_360_degrees_normalizes_to_zero() -> None:
    at_360 = nakshatra_position(360.0)
    at_zero = nakshatra_position(0.0)
    assert (at_360.nakshatra, at_360.pada) == (Nakshatra.ASHWINI, 1)
    assert (at_360.nakshatra, at_360.pada) == (at_zero.nakshatra, at_zero.pada)
    assert nakshatra_position(-0.0).nakshatra is Nakshatra.ASHWINI


@pytest.mark.parametrize("longitude", [-360.0, 720.0, 1080.0])
def test_whole_turn_multiples_normalize_to_zero(longitude: float) -> None:
    position = nakshatra_position(longitude)
    assert (position.nakshatra, position.pada) == (Nakshatra.ASHWINI, 1)


def test_equivalent_longitudes_classify_identically() -> None:
    for longitude in (0.5, 13.0, 40.0, 100.25, 359.5):
        base = nakshatra_position(longitude)
        for turns in (-2, -1, 1, 2):
            other = nakshatra_position(longitude + 360.0 * turns)
            assert (other.nakshatra, other.pada) == (base.nakshatra, base.pada)


@pytest.mark.parametrize(
    ("longitude", "expected_nakshatra", "expected_pada"),
    [
        (-0.5, Nakshatra.REVATI, 4),  # 359.5 deg
        (-10.0, Nakshatra.REVATI, 2),  # 350 deg: exactly the Revati pada 1/2 boundary
        (-13.5, Nakshatra.UTTARA_BHADRAPADA, 4),  # 346.5 deg
    ],
)
def test_supported_negative_longitudes(
    longitude: float, expected_nakshatra: Nakshatra, expected_pada: int
) -> None:
    position = nakshatra_position(longitude)
    assert position.nakshatra is expected_nakshatra
    assert position.pada == expected_pada
    assert (position.nakshatra, position.pada) == _exact_expected(longitude)


def test_negative_longitude_exactly_on_a_boundary_goes_to_the_upper_bucket() -> None:
    # -320.0 normalizes to exactly 40.0, a Nakshatra boundary -> Rohini pada 1.
    position = nakshatra_position(-320.0)
    assert (position.nakshatra, position.pada) == (Nakshatra.ROHINI, 1)


@pytest.mark.parametrize("boundary", _PADA_BOUNDARY_FRACTIONS)
def test_pada_boundary_neighbourhood_matches_exact_classification(boundary: Fraction) -> None:
    at = float(boundary)
    for longitude in (_LEAP(at, -1e9), at, _LEAP(at, 1e9)):
        if longitude < 0.0:
            continue
        position = nakshatra_position(longitude)
        assert (position.nakshatra, position.pada) == _exact_expected(longitude)


def test_value_immediately_below_an_exact_boundary_stays_in_the_lower_bucket() -> None:
    for longitude in (10.0, 20.0, 40.0, 80.0, 120.0, 200.0, 240.0, 280.0, 320.0):
        below = nakshatra_position(_LEAP(longitude, -1e9))
        at = nakshatra_position(longitude)
        slot_below = NAKSHATRA_ORDER.index(below.nakshatra) * 4 + below.pada - 1
        slot_at = NAKSHATRA_ORDER.index(at.nakshatra) * 4 + at.pada - 1
        assert slot_at == slot_below + 1
        assert below.near_boundary is True and at.near_boundary is True


def test_pada_numbers_run_one_to_four_within_every_nakshatra() -> None:
    for index in range(27):
        start = Fraction(index * 40, 3)
        pads = [
            nakshatra_position(float(start + Fraction(k * 10, 3) + Fraction(1, 3)))
            for k in range(4)
        ]
        assert [p.nakshatra for p in pads] == [NAKSHATRA_ORDER[index]] * 4
        assert [p.pada for p in pads] == [1, 2, 3, 4]


def test_partition_is_gapless_and_monotonic() -> None:
    previous = -1
    for step in range(0, 3600):
        position = nakshatra_position(step / 10.0)
        slot = NAKSHATRA_ORDER.index(position.nakshatra) * 4 + position.pada - 1
        assert slot in (previous, previous + 1) or (previous == -1 and slot == 0)
        previous = slot
    assert previous == 107


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_longitude_is_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        nakshatra_position(value)
