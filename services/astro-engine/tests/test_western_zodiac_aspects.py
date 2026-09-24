"""Phase 9 WP-D: tropical sign classification and Western aspect detection
(pure functions; `docs/ASTROLOGY_STANDARDS.md` WD-02, WD-09 to WD-14)."""

from __future__ import annotations

import math
import random
from fractions import Fraction

import pytest

from pandit_astro_engine.western.aspects import AspectInput, evaluate_aspects, separation
from pandit_astro_engine.western.constants import (
    ASPECT_ANGLE,
    SIGN_ORDER,
    AspectType,
    TropicalSign,
    WesternBody,
)
from pandit_astro_engine.western.models import MotionState, WesternReason
from pandit_astro_engine.western.profiles import (
    ASPECT_SET_PROFILES,
    ASPECTS_PTOLEMAIC_5,
    ORB_FIXED_V1,
    ORB_LILLY_MOIETY,
    ORB_PROFILES,
    largest_possible_orb,
    max_orb,
    smallest_aspect_gap,
)
from pandit_astro_engine.western.zodiac import (
    degree_in_sign,
    normalize_longitude,
    sign_index,
    tropical_sign,
)

B = WesternBody

# ---------------------------------------------------------------- zodiac


@pytest.mark.parametrize("index", range(12))
def test_each_sign_starts_exactly_at_its_boundary(index: int) -> None:
    start = 30.0 * index
    assert tropical_sign(start) is SIGN_ORDER[index]
    assert degree_in_sign(start) == 0.0
    assert tropical_sign(math.nextafter(start + 30.0, 0.0)) is SIGN_ORDER[index]


def test_the_boundary_belongs_to_the_later_sign() -> None:
    assert tropical_sign(30.0) is TropicalSign.TAURUS
    assert tropical_sign(math.nextafter(30.0, 0.0)) is TropicalSign.ARIES
    assert tropical_sign(0.0) is TropicalSign.ARIES
    assert tropical_sign(math.nextafter(360.0, 0.0)) is TropicalSign.PISCES


def test_wraparound_and_normalization() -> None:
    assert normalize_longitude(360.0) == 0.0
    assert normalize_longitude(-30.0) == 330.0
    assert normalize_longitude(725.0) == 5.0
    assert tropical_sign(360.0) is TropicalSign.ARIES
    assert tropical_sign(-0.5) is TropicalSign.PISCES
    # a negative value that rounds to 360.0 under float modulo is still Aries (360 = 0)
    assert normalize_longitude(-1e-20) == 0.0


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_longitude_is_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        tropical_sign(value)


def test_degree_in_sign_and_index_are_exact() -> None:
    assert degree_in_sign(59.25) == 29.25
    assert sign_index(329.999999) == 10
    assert degree_in_sign(330.0) == 0.0
    rng = random.Random(7)
    for _ in range(2000):
        lon = rng.uniform(0.0, 360.0)
        i = sign_index(lon)
        assert 0 <= i < 12
        assert 0.0 <= degree_in_sign(lon) < 30.0
        assert Fraction(lon) == 30 * i + Fraction(degree_in_sign(lon))


def test_tropical_signs_are_a_separate_type_from_the_vedic_rashi() -> None:
    from pandit_astro_engine.rashi import Rashi

    # The sign names are shared vocabulary, but the types are distinct: a Western
    # result carries TropicalSign plus the tropical zodiac profile, never a Rashi.
    assert TropicalSign is not Rashi
    assert not issubclass(TropicalSign, Rashi)
    assert not isinstance(TropicalSign.ARIES, Rashi)


# --------------------------------------------------------------- aspects


def _inp(body: WesternBody, lon: float, speed: float = 1.0) -> AspectInput:
    return AspectInput(body, lon, speed)


def _one(a: AspectInput, b: AspectInput, orbs=ORB_FIXED_V1):  # type: ignore[no-untyped-def]
    found, blocked = evaluate_aspects([a, b], ASPECTS_PTOLEMAIC_5, orbs)
    assert blocked == ()
    return found


@pytest.mark.parametrize("aspect", list(AspectType))
def test_each_exact_aspect_is_found(aspect: AspectType) -> None:
    angle = ASPECT_ANGLE[aspect]
    found = _one(_inp(B.SUN, 10.0), _inp(B.MARS, 10.0 + angle, 0.5))
    assert len(found) == 1
    assert found[0].aspect is aspect
    assert found[0].deviation == 0.0
    assert found[0].motion_state is MotionState.EXACT


def test_separation_is_the_shorter_arc_across_zero() -> None:
    assert separation(359.0, 1.0) == 2
    assert separation(1.0, 359.0) == 2
    assert separation(0.0, 180.0) == 180
    assert separation(10.0, 250.0) == 120
    found = _one(_inp(B.SUN, 359.0), _inp(B.VENUS, 1.0))
    assert [a.aspect for a in found] == [AspectType.CONJUNCTION]
    assert found[0].separation == 2.0


def test_orb_boundary_is_inclusive_and_exact() -> None:
    # square orb 8: 98.0 apart is in (deviation exactly 8), the next float beyond is out
    assert [a.aspect for a in _one(_inp(B.SUN, 0.0), _inp(B.MARS, 98.0))] == [AspectType.SQUARE]
    assert _one(_inp(B.SUN, 0.0), _inp(B.MARS, math.nextafter(98.0, 99.0))) == ()
    # sextile orb 6
    assert _one(_inp(B.SUN, 0.0), _inp(B.MARS, 66.0))[0].aspect is AspectType.SEXTILE
    assert _one(_inp(B.SUN, 0.0), _inp(B.MARS, 66.0001)) == ()


def test_out_of_orb_and_unsupported_minor_angles_find_nothing() -> None:
    for gap in (30.0, 45.0, 72.0, 135.0, 144.0, 150.0, 20.0):  # minor-aspect angles and a plain gap
        assert _one(_inp(B.SUN, 100.0), _inp(B.MOON, 100.0 + gap)) == (), gap
    assert {a.value for a in AspectType} == {
        "conjunction",
        "sextile",
        "square",
        "trine",
        "opposition",
    }


def test_each_pair_is_evaluated_once_in_profile_order() -> None:
    bodies = [_inp(B.SUN, 0.0), _inp(B.MOON, 120.0), _inp(B.MARS, 240.0)]
    found, _ = evaluate_aspects(bodies, ASPECTS_PTOLEMAIC_5, ORB_FIXED_V1)
    pairs = [(a.body_a, a.body_b) for a in found]
    assert pairs == [(B.SUN, B.MOON), (B.SUN, B.MARS), (B.MOON, B.MARS)]
    assert len(set(frozenset(p) for p in pairs)) == len(pairs)


def test_input_order_only_changes_the_pair_orientation() -> None:
    a = _one(_inp(B.SUN, 10.0, 1.0), _inp(B.MOON, 128.0, 13.0))[0]
    b = _one(_inp(B.MOON, 128.0, 13.0), _inp(B.SUN, 10.0, 1.0))[0]
    assert (a.aspect, a.deviation, a.motion_state) == (b.aspect, b.deviation, b.motion_state)


@pytest.mark.parametrize(
    ("lon_a", "speed_a", "lon_b", "speed_b", "expected"),
    [
        # faster body behind a slower one, both direct, closing on a conjunction
        (10.0, 1.0, 5.0, 13.0, MotionState.APPLYING),
        (10.0, 1.0, 15.0, 13.0, MotionState.SEPARATING),
        # both retrograde (Lilly's second way): the retrograde body moves back onto the other
        (10.0, -0.1, 12.0, -1.0, MotionState.APPLYING),
        # one retrograde meeting a direct body (Lilly's third way)
        (10.0, 1.0, 14.0, -0.5, MotionState.APPLYING),
        # trine measured across 0 degrees
        (350.0, 1.0, 112.0, 0.1, MotionState.APPLYING),
        (350.0, 1.0, 108.0, 0.1, MotionState.SEPARATING),
    ],
)
def test_applying_and_separating(
    lon_a: float, speed_a: float, lon_b: float, speed_b: float, expected: MotionState
) -> None:
    found = _one(_inp(B.SUN, lon_a, speed_a), _inp(B.MARS, lon_b, speed_b))
    assert len(found) == 1
    assert found[0].motion_state is expected


def test_equal_speeds_give_not_evaluable_motion() -> None:
    found = _one(_inp(B.SUN, 0.0, 0.8), _inp(B.MARS, 93.0, 0.8))
    assert found[0].motion_state is MotionState.NOT_EVALUABLE
    assert found[0].motion_reason is WesternReason.RELATIVE_MOTION_ZERO


def test_motion_state_matches_a_small_time_step() -> None:
    rng = random.Random(11)
    checked = 0
    for _ in range(4000):
        la, lb = rng.uniform(0, 360), rng.uniform(0, 360)
        va, vb = rng.uniform(-1.5, 15.0), rng.uniform(-1.5, 15.0)
        found = _one(_inp(B.SUN, la, va), _inp(B.MARS, lb, vb))
        for asp in found:
            if asp.motion_state not in (MotionState.APPLYING, MotionState.SEPARATING):
                continue
            dt = 1e-5
            later = float(separation(la + va * dt, lb + vb * dt))
            later_dev = abs(later - asp.exact_angle)
            if abs(later_dev - asp.deviation) < 1e-9:
                continue
            assert (later_dev < asp.deviation) == (asp.motion_state is MotionState.APPLYING)
            checked += 1
    assert checked > 200


def test_lilly_moiety_orbs() -> None:
    assert max_orb(ORB_LILLY_MOIETY, AspectType.TRINE, B.SUN, B.MOON) == 13.5
    assert max_orb(ORB_LILLY_MOIETY, AspectType.SQUARE, B.SATURN, B.VENUS) == 8.0
    assert max_orb(ORB_LILLY_MOIETY, AspectType.SQUARE, B.MARS, B.URANUS) is None
    # Sun and Moon 13.5 apart from an exact square: in orb under Lilly, out under the fixed default
    lilly = _one(_inp(B.SUN, 0.0), _inp(B.MOON, 103.5), orbs=ORB_LILLY_MOIETY)
    assert [a.aspect for a in lilly] == [AspectType.SQUARE]
    assert lilly[0].orb_allowed == 13.5
    assert _one(_inp(B.SUN, 0.0), _inp(B.MOON, 103.5)) == ()


def test_lilly_orbs_make_outer_planet_pairs_not_evaluable() -> None:
    found, blocked = evaluate_aspects(
        [_inp(B.SUN, 0.0), _inp(B.URANUS, 0.0), _inp(B.MOON, 0.0)],
        ASPECTS_PTOLEMAIC_5,
        ORB_LILLY_MOIETY,
    )
    assert [(a.body_a, a.body_b) for a in found] == [(B.SUN, B.MOON)]
    assert [(p.body_a, p.body_b, p.reason) for p in blocked] == [
        (B.SUN, B.URANUS, WesternReason.ORB_NOT_DEFINED_FOR_BODY),
        (B.URANUS, B.MOON, WesternReason.ORB_NOT_DEFINED_FOR_BODY),
    ]


@pytest.mark.parametrize("orb_id", sorted(ORB_PROFILES))
@pytest.mark.parametrize("aspect_set_id", sorted(ASPECT_SET_PROFILES))
def test_no_profile_can_produce_two_aspects_for_one_pair(orb_id: str, aspect_set_id: str) -> None:
    aspect_set = ASPECT_SET_PROFILES[aspect_set_id]
    orbs = ORB_PROFILES[orb_id]
    assert largest_possible_orb(orbs) < smallest_aspect_gap(aspect_set.aspects) / 2
    rng = random.Random(orb_id)
    classical = [B.SUN, B.MOON, B.MERCURY, B.VENUS, B.MARS, B.JUPITER, B.SATURN]
    for _ in range(500):
        inputs = [_inp(b, rng.uniform(0, 360), rng.uniform(-1, 14)) for b in classical]
        found, _ = evaluate_aspects(inputs, aspect_set, orbs)
        pairs = [(a.body_a, a.body_b) for a in found]
        assert len(pairs) == len(set(pairs))
        for a in found:
            assert a.deviation <= a.orb_allowed


def test_fixed_orb_values_are_the_documented_ones() -> None:
    assert ORB_FIXED_V1.per_aspect_orb == {
        AspectType.CONJUNCTION: 8.0,
        AspectType.SEXTILE: 6.0,
        AspectType.SQUARE: 8.0,
        AspectType.TRINE: 8.0,
        AspectType.OPPOSITION: 8.0,
    }
    assert ORB_LILLY_MOIETY.planet_orb == {
        B.SATURN: 9.0,
        B.JUPITER: 9.0,
        B.MARS: 7.0,
        B.SUN: 15.0,
        B.VENUS: 7.0,
        B.MERCURY: 7.0,
        B.MOON: 12.0,
    }
