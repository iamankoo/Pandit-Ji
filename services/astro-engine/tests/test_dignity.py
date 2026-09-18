import pytest

from pandit_astro_engine.dignity import DIGNITY_EVALUATED_BODIES, DignityStatus, evaluate_dignity
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.rashi import Rashi


def test_rahu_ketu_not_evaluated() -> None:
    assert evaluate_dignity(CelestialBody.RAHU, Rashi.ARIES, 10.0) is None
    assert evaluate_dignity(CelestialBody.KETU, Rashi.LIBRA, 10.0) is None
    assert CelestialBody.RAHU not in DIGNITY_EVALUATED_BODIES
    assert CelestialBody.KETU not in DIGNITY_EVALUATED_BODIES


@pytest.mark.parametrize(
    ("body", "exaltation_rashi", "debilitation_rashi"),
    [
        (CelestialBody.SUN, Rashi.ARIES, Rashi.LIBRA),
        (CelestialBody.MOON, Rashi.TAURUS, Rashi.SCORPIO),
        (CelestialBody.MARS, Rashi.CAPRICORN, Rashi.CANCER),
        (CelestialBody.MERCURY, Rashi.VIRGO, Rashi.PISCES),
        (CelestialBody.JUPITER, Rashi.CANCER, Rashi.CAPRICORN),
        (CelestialBody.VENUS, Rashi.PISCES, Rashi.VIRGO),
        (CelestialBody.SATURN, Rashi.LIBRA, Rashi.ARIES),
    ],
)
def test_exaltation_and_debilitation_signs(
    body: CelestialBody, exaltation_rashi: Rashi, debilitation_rashi: Rashi
) -> None:
    assert evaluate_dignity(body, exaltation_rashi, 15.0) == DignityStatus.EXALTED
    assert evaluate_dignity(body, debilitation_rashi, 15.0) == DignityStatus.DEBILITATED


def test_mercury_own_signs() -> None:
    assert evaluate_dignity(CelestialBody.MERCURY, Rashi.GEMINI, 10.0) == DignityStatus.OWN_SIGN
    # Virgo is Mercury's exaltation sign, not merely its own sign -- exaltation wins.
    assert evaluate_dignity(CelestialBody.MERCURY, Rashi.VIRGO, 10.0) == DignityStatus.EXALTED


def test_neutral_when_none_apply() -> None:
    assert evaluate_dignity(CelestialBody.SUN, Rashi.TAURUS, 10.0) == DignityStatus.NEUTRAL


def test_sun_own_sign_leo() -> None:
    assert evaluate_dignity(CelestialBody.SUN, Rashi.LEO, 10.0) == DignityStatus.OWN_SIGN


def test_dignity_is_sign_level_not_exact_degree() -> None:
    # Mooltrikona is explicitly out of scope for Phase 5 -- exaltation is
    # asserted at the sign level, regardless of exact degree within it.
    assert evaluate_dignity(CelestialBody.SUN, Rashi.ARIES, 0.5) == DignityStatus.EXALTED
    assert evaluate_dignity(CelestialBody.SUN, Rashi.ARIES, 29.5) == DignityStatus.EXALTED
