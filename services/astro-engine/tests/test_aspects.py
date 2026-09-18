import pytest

from pandit_astro_engine.aspects import aspect_offsets, aspected_houses
from pandit_astro_engine.models import CelestialBody


@pytest.mark.parametrize(
    "body",
    [
        CelestialBody.SUN,
        CelestialBody.MOON,
        CelestialBody.MERCURY,
        CelestialBody.VENUS,
        CelestialBody.RAHU,
        CelestialBody.KETU,
    ],
)
def test_universal_aspect_only_bodies(body: CelestialBody) -> None:
    assert aspect_offsets(body) == (7,)


def test_mars_special_aspects() -> None:
    assert aspect_offsets(CelestialBody.MARS) == (4, 7, 8)


def test_jupiter_special_aspects() -> None:
    assert aspect_offsets(CelestialBody.JUPITER) == (5, 7, 9)


def test_saturn_special_aspects() -> None:
    assert aspect_offsets(CelestialBody.SATURN) == (3, 7, 10)


def test_seventh_aspect_from_house_one() -> None:
    assert aspected_houses(CelestialBody.SUN, 1) == [7]


def test_mars_aspects_wrap_around_the_zodiac() -> None:
    # From house 10: 4th->1, 7th->4, 8th->5
    assert aspected_houses(CelestialBody.MARS, 10) == [1, 4, 5]


def test_saturn_aspects_from_house_11() -> None:
    # 3rd->1, 7th->5, 10th->8
    assert aspected_houses(CelestialBody.SATURN, 11) == [1, 5, 8]


def test_rahu_ketu_have_no_special_extra_aspects() -> None:
    assert aspected_houses(CelestialBody.RAHU, 3) == aspected_houses(CelestialBody.MERCURY, 3)
    assert aspected_houses(CelestialBody.KETU, 3) == [9]
