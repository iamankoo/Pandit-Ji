import pytest

from pandit_astro_engine.combustion import angular_separation_degrees, evaluate_combustion
from pandit_astro_engine.models import CelestialBody


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (10, 20, 10),
        (350, 10, 20),
        (0, 180, 180),
        (0, 0, 0),
        (10, 350, 20),
    ],
)
def test_angular_separation(a: float, b: float, expected: float) -> None:
    assert angular_separation_degrees(a, b) == pytest.approx(expected)


def test_sun_and_nodes_are_not_evaluated() -> None:
    assert evaluate_combustion(CelestialBody.SUN, 100, 100, is_retrograde=False) is None
    assert evaluate_combustion(CelestialBody.RAHU, 100, 40, is_retrograde=False) is None
    assert evaluate_combustion(CelestialBody.KETU, 100, 40, is_retrograde=False) is None


def test_moon_combustion_threshold_boundary() -> None:
    just_inside = evaluate_combustion(CelestialBody.MOON, 12.0, 0.0, is_retrograde=False)
    assert just_inside is not None
    assert just_inside.is_combust is True
    assert just_inside.threshold_degrees == 12.0

    just_outside = evaluate_combustion(CelestialBody.MOON, 12.0001, 0.0, is_retrograde=False)
    assert just_outside is not None
    assert just_outside.is_combust is False


def test_mercury_uses_retrograde_threshold_when_retrograde() -> None:
    direct = evaluate_combustion(CelestialBody.MERCURY, 13.0, 0.0, is_retrograde=False)
    retro = evaluate_combustion(CelestialBody.MERCURY, 13.0, 0.0, is_retrograde=True)
    assert direct is not None and retro is not None
    assert direct.threshold_degrees == 14.0
    assert direct.is_combust is True
    assert retro.threshold_degrees == 12.0
    assert retro.is_combust is False  # 13 deg > 12 deg retrograde threshold


def test_venus_uses_retrograde_threshold_when_retrograde() -> None:
    direct = evaluate_combustion(CelestialBody.VENUS, 9.0, 0.0, is_retrograde=False)
    retro = evaluate_combustion(CelestialBody.VENUS, 9.0, 0.0, is_retrograde=True)
    assert direct is not None and direct.is_combust is True  # 9 <= 10 (direct threshold)
    assert retro is not None and retro.is_combust is False  # 9 > 8 (retrograde threshold)


def test_venus_retrograde_boundary_precisely() -> None:
    at_boundary = evaluate_combustion(CelestialBody.VENUS, 8.0, 0.0, is_retrograde=True)
    beyond_boundary = evaluate_combustion(CelestialBody.VENUS, 8.1, 0.0, is_retrograde=True)
    assert at_boundary is not None and at_boundary.is_combust is True
    assert beyond_boundary is not None and beyond_boundary.is_combust is False


@pytest.mark.parametrize(
    ("body", "threshold"),
    [
        (CelestialBody.MARS, 17.0),
        (CelestialBody.JUPITER, 11.0),
        (CelestialBody.SATURN, 15.0),
    ],
)
def test_direct_only_bodies_ignore_retrograde_flag(body: CelestialBody, threshold: float) -> None:
    direct = evaluate_combustion(body, threshold, 0.0, is_retrograde=False)
    retro = evaluate_combustion(body, threshold, 0.0, is_retrograde=True)
    assert direct is not None and retro is not None
    assert direct.threshold_degrees == retro.threshold_degrees == threshold
