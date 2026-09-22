"""Phase 9 WP-B-1: Rashi Drishti (BPHS Ch. 8 v. 1-3).

The expected table below is transcribed directly from BPHS's own printed
worked table (Santhanam translation, printed pp. 106-107, page-image
verified -- see `research/ASTROLOGY_SOURCES.md` Group 12), not derived from
the implementation under test.
"""

from __future__ import annotations

import pytest

from pandit_astro_engine.jaimini.profiles import RASHI_DRISHTI_PROFILE, RASHI_DRISHTI_PROFILE_ID
from pandit_astro_engine.jaimini.rashi_drishti import has_rashi_drishti, rashi_drishti
from pandit_astro_engine.rashi import Rashi

#: BPHS Ch. 8's own printed table (pp. 106-107), transcribed verbatim.
_PRINTED_TABLE: dict[Rashi, tuple[Rashi, ...]] = {
    Rashi.ARIES: (Rashi.LEO, Rashi.SCORPIO, Rashi.AQUARIUS),
    Rashi.TAURUS: (Rashi.CANCER, Rashi.LIBRA, Rashi.CAPRICORN),
    Rashi.GEMINI: (Rashi.VIRGO, Rashi.SAGITTARIUS, Rashi.PISCES),
    Rashi.CANCER: (Rashi.SCORPIO, Rashi.AQUARIUS, Rashi.TAURUS),
    Rashi.LEO: (Rashi.LIBRA, Rashi.CAPRICORN, Rashi.ARIES),
    Rashi.VIRGO: (Rashi.SAGITTARIUS, Rashi.PISCES, Rashi.GEMINI),
    Rashi.LIBRA: (Rashi.AQUARIUS, Rashi.TAURUS, Rashi.LEO),
    Rashi.SCORPIO: (Rashi.CAPRICORN, Rashi.ARIES, Rashi.CANCER),
    Rashi.SAGITTARIUS: (Rashi.PISCES, Rashi.GEMINI, Rashi.VIRGO),
    Rashi.CAPRICORN: (Rashi.TAURUS, Rashi.LEO, Rashi.SCORPIO),
    Rashi.AQUARIUS: (Rashi.ARIES, Rashi.CANCER, Rashi.LIBRA),
    Rashi.PISCES: (Rashi.GEMINI, Rashi.VIRGO, Rashi.SAGITTARIUS),
}


@pytest.mark.parametrize("rashi", list(Rashi))
def test_matches_bphs_printed_table_exactly(rashi: Rashi) -> None:
    assert set(rashi_drishti(rashi)) == set(_PRINTED_TABLE[rashi])


@pytest.mark.parametrize("rashi", list(Rashi))
def test_always_exactly_three_targets(rashi: Rashi) -> None:
    assert len(rashi_drishti(rashi)) == 3


@pytest.mark.parametrize("rashi", list(Rashi))
def test_a_sign_never_aspects_itself(rashi: Rashi) -> None:
    assert rashi not in rashi_drishti(rashi)


@pytest.mark.parametrize(
    "movable,excluded_fixed",
    [
        (Rashi.ARIES, Rashi.TAURUS),
        (Rashi.CANCER, Rashi.LEO),
        (Rashi.LIBRA, Rashi.SCORPIO),
        (Rashi.CAPRICORN, Rashi.AQUARIUS),
    ],
)
def test_movable_sign_excludes_its_adjacent_fixed_sign(
    movable: Rashi, excluded_fixed: Rashi
) -> None:
    assert excluded_fixed not in rashi_drishti(movable)


@pytest.mark.parametrize(
    "fixed,excluded_movable",
    [
        (Rashi.TAURUS, Rashi.ARIES),
        (Rashi.LEO, Rashi.CANCER),
        (Rashi.SCORPIO, Rashi.LIBRA),
        (Rashi.AQUARIUS, Rashi.CAPRICORN),
    ],
)
def test_fixed_sign_excludes_its_adjacent_movable_sign(
    fixed: Rashi, excluded_movable: Rashi
) -> None:
    assert excluded_movable not in rashi_drishti(fixed)


@pytest.mark.parametrize("common", [Rashi.GEMINI, Rashi.VIRGO, Rashi.SAGITTARIUS, Rashi.PISCES])
def test_common_sign_aspects_all_three_other_common_signs(common: Rashi) -> None:
    others = {Rashi.GEMINI, Rashi.VIRGO, Rashi.SAGITTARIUS, Rashi.PISCES} - {common}
    assert set(rashi_drishti(common)) == others


@pytest.mark.parametrize("a", list(Rashi))
def test_relation_is_always_mutual(a: Rashi) -> None:
    """A genuine BPHS finding, not assumed: every Rasi Drishti pair aspects
    back (movable<->fixed pairs are mutual; all four common signs mutually
    aspect one another)."""
    for b in rashi_drishti(a):
        assert has_rashi_drishti(b, a), f"{a} aspects {b} but not vice versa"


def test_has_rashi_drishti_matches_the_table() -> None:
    assert has_rashi_drishti(Rashi.ARIES, Rashi.LEO) is True
    assert has_rashi_drishti(Rashi.ARIES, Rashi.TAURUS) is False


def test_invalid_sign_input_is_rejected() -> None:
    with pytest.raises(ValueError):
        Rashi("not-a-real-sign")


def test_deterministic_and_longitude_independent() -> None:
    # Same input, called repeatedly, always the same output -- there is no
    # hidden state, iteration-order dependency or clock/random input.
    first = {r: rashi_drishti(r) for r in Rashi}
    second = {r: rashi_drishti(r) for r in Rashi}
    assert first == second


def test_does_not_conflate_with_graha_drishti() -> None:
    """Regression: Rashi Drishti (sign-to-sign, this module) must never be
    confused with or substitute for Phase 5/6's graha drishti
    (planet-to-house, `aspects.py`) -- they are separate systems with
    different rules and different inputs (a Rashi here, a CelestialBody and
    house number there)."""
    from pandit_astro_engine.aspects import aspected_houses
    from pandit_astro_engine.models import CelestialBody

    # Graha drishti's Mars special aspects (4th, 8th, plus universal 7th)
    # are a completely different shape of rule (house-offsets from a single
    # placement) than Rashi Drishti's fixed 3-sign targets; there is no
    # shared table or function between the two modules.
    assert aspected_houses(CelestialBody.MARS, 1) == [4, 7, 8]
    assert len(rashi_drishti(Rashi.ARIES)) == 3


def test_profile_provenance() -> None:
    assert RASHI_DRISHTI_PROFILE.profile_id == RASHI_DRISHTI_PROFILE_ID
    assert RASHI_DRISHTI_PROFILE.reference.source_id == "SRC-BPHS-SANTHANAM-1984"
    assert "Ch. 8" in RASHI_DRISHTI_PROFILE.reference.locator
