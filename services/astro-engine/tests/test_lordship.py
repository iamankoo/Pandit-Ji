from pandit_astro_engine.lordship import RASHI_LORD, sign_lord
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.rashi import Rashi


def test_every_sign_has_a_lord() -> None:
    assert set(RASHI_LORD) == set(Rashi)


def test_mercury_and_venus_and_mars_and_jupiter_and_saturn_rule_two_signs_each() -> None:
    from collections import Counter

    counts = Counter(RASHI_LORD.values())
    assert counts[CelestialBody.MERCURY] == 2
    assert counts[CelestialBody.VENUS] == 2
    assert counts[CelestialBody.MARS] == 2
    assert counts[CelestialBody.JUPITER] == 2
    assert counts[CelestialBody.SATURN] == 2
    assert counts[CelestialBody.SUN] == 1
    assert counts[CelestialBody.MOON] == 1


def test_sign_lord_known_values() -> None:
    assert sign_lord(Rashi.ARIES) == CelestialBody.MARS
    assert sign_lord(Rashi.LEO) == CelestialBody.SUN
    assert sign_lord(Rashi.CANCER) == CelestialBody.MOON
    assert sign_lord(Rashi.LIBRA) == CelestialBody.VENUS
    assert sign_lord(Rashi.CAPRICORN) == CelestialBody.SATURN
    assert sign_lord(Rashi.AQUARIUS) == CelestialBody.SATURN
    assert sign_lord(Rashi.PISCES) == CelestialBody.JUPITER


def test_rahu_ketu_never_assigned_lordship() -> None:
    assert CelestialBody.RAHU not in RASHI_LORD.values()
    assert CelestialBody.KETU not in RASHI_LORD.values()
