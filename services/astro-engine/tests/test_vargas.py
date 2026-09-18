"""Varga derivation formula tests -- each case is hand-derived from
docs/ASTROLOGY_STANDARDS.md "Varga derivation formulas" (locked v1.3.0),
not copied from the implementation, so a formula bug in `vargas.py` would
be caught here."""

import pytest

from pandit_astro_engine.errors import UnsupportedConfigurationError
from pandit_astro_engine.rashi import Rashi, rashi_index
from pandit_astro_engine.vargas import SUPPORTED_VARGAS, calculate_varga_sign


def _lon(rashi: Rashi, degree_in_sign: float) -> float:
    return rashi_index(rashi) * 30.0 + degree_in_sign


def test_locked_varga_set() -> None:
    assert SUPPORTED_VARGAS == (1, 2, 3, 4, 7, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, 60)


def test_unsupported_varga_raises() -> None:
    with pytest.raises(UnsupportedConfigurationError):
        calculate_varga_sign(5, 10.0)


def test_d1_is_identity() -> None:
    assert calculate_varga_sign(1, _lon(Rashi.SCORPIO, 17.3)) is Rashi.SCORPIO


@pytest.mark.parametrize(
    ("rashi", "degree", "expected"),
    [
        (Rashi.ARIES, 0.0, Rashi.LEO),  # odd sign, first half -> Sun's Hora
        (Rashi.ARIES, 14.999, Rashi.LEO),
        (Rashi.ARIES, 15.0, Rashi.CANCER),  # odd sign, second half -> Moon's Hora
        (Rashi.TAURUS, 0.0, Rashi.CANCER),  # even sign, first half -> Moon's Hora
        (Rashi.TAURUS, 15.0, Rashi.LEO),  # even sign, second half -> Sun's Hora
    ],
)
def test_d2_hora(rashi: Rashi, degree: float, expected: Rashi) -> None:
    assert calculate_varga_sign(2, _lon(rashi, degree)) is expected


@pytest.mark.parametrize(
    ("degree", "expected"),
    [(0.0, Rashi.GEMINI), (9.999, Rashi.GEMINI), (10.0, Rashi.LIBRA), (20.0, Rashi.AQUARIUS)],
)
def test_d3_drekkana_bphs_trine_counting(degree: float, expected: Rashi) -> None:
    # From Gemini: same=Gemini, 5th=Libra, 9th=Aquarius.
    assert calculate_varga_sign(3, _lon(Rashi.GEMINI, degree)) is expected


@pytest.mark.parametrize(
    ("degree", "expected"),
    [
        (0.0, Rashi.ARIES),  # same
        (7.5, Rashi.CANCER),  # 4th
        (15.0, Rashi.LIBRA),  # 7th
        (22.5, Rashi.CAPRICORN),  # 10th
    ],
)
def test_d4_chaturthamsa_kendra_counting(degree: float, expected: Rashi) -> None:
    assert calculate_varga_sign(4, _lon(Rashi.ARIES, degree)) is expected


def test_d7_saptamsa_odd_and_even_start() -> None:
    division = 30.0 / 7.0
    # Odd sign (Aries): starts at Aries itself.
    assert calculate_varga_sign(7, _lon(Rashi.ARIES, 0.0)) is Rashi.ARIES
    assert calculate_varga_sign(7, _lon(Rashi.ARIES, division + 0.01)) is Rashi.TAURUS
    # Even sign (Taurus): starts at the 7th sign from it (Scorpio).
    assert calculate_varga_sign(7, _lon(Rashi.TAURUS, 0.0)) is Rashi.SCORPIO


def test_d9_navamsa_modality_starts() -> None:
    division = 30.0 / 9.0
    # Movable (Aries): starts at Aries.
    assert calculate_varga_sign(9, _lon(Rashi.ARIES, 0.0)) is Rashi.ARIES
    # Fixed (Taurus): starts at the 9th sign from Taurus == Capricorn.
    assert calculate_varga_sign(9, _lon(Rashi.TAURUS, 0.0)) is Rashi.CAPRICORN
    # Dual (Gemini): starts at the 5th sign from Gemini == Libra.
    assert calculate_varga_sign(9, _lon(Rashi.GEMINI, 0.0)) is Rashi.LIBRA
    # Second segment of Aries navamsa -> Taurus.
    assert calculate_varga_sign(9, _lon(Rashi.ARIES, division + 0.01)) is Rashi.TAURUS


def test_d10_dasamsa_odd_and_even_start() -> None:
    # Odd sign (Aries): starts at Aries.
    assert calculate_varga_sign(10, _lon(Rashi.ARIES, 0.0)) is Rashi.ARIES
    # Even sign (Taurus): starts at the 9th sign from Taurus == Capricorn.
    assert calculate_varga_sign(10, _lon(Rashi.TAURUS, 0.0)) is Rashi.CAPRICORN


def test_d12_dwadasamsa_always_same_sign_start() -> None:
    assert calculate_varga_sign(12, _lon(Rashi.ARIES, 0.0)) is Rashi.ARIES
    assert calculate_varga_sign(12, _lon(Rashi.ARIES, 2.5)) is Rashi.TAURUS
    assert calculate_varga_sign(12, _lon(Rashi.TAURUS, 0.0)) is Rashi.TAURUS
    assert calculate_varga_sign(12, _lon(Rashi.TAURUS, 2.5)) is Rashi.GEMINI


def test_d16_shodasamsa_modality_absolute_starts() -> None:
    assert calculate_varga_sign(16, _lon(Rashi.ARIES, 0.0)) is Rashi.ARIES  # movable -> Aries
    assert calculate_varga_sign(16, _lon(Rashi.TAURUS, 0.0)) is Rashi.LEO  # fixed -> Leo
    assert (
        calculate_varga_sign(16, _lon(Rashi.GEMINI, 0.0)) is Rashi.SAGITTARIUS
    )  # dual -> Sagittarius


def test_d20_vimsamsa_modality_absolute_starts() -> None:
    assert calculate_varga_sign(20, _lon(Rashi.ARIES, 0.0)) is Rashi.ARIES  # movable -> Aries
    assert (
        calculate_varga_sign(20, _lon(Rashi.TAURUS, 0.0)) is Rashi.SAGITTARIUS
    )  # fixed -> Sagittarius
    assert calculate_varga_sign(20, _lon(Rashi.GEMINI, 0.0)) is Rashi.LEO  # dual -> Leo


def test_d24_chaturvimsamsa_odd_even_absolute_starts() -> None:
    assert calculate_varga_sign(24, _lon(Rashi.ARIES, 0.0)) is Rashi.LEO  # odd -> Leo
    assert calculate_varga_sign(24, _lon(Rashi.TAURUS, 0.0)) is Rashi.CANCER  # even -> Cancer


def test_d27_nakshatramsa_modality_absolute_starts() -> None:
    assert calculate_varga_sign(27, _lon(Rashi.ARIES, 0.0)) is Rashi.ARIES  # movable -> Aries
    assert calculate_varga_sign(27, _lon(Rashi.TAURUS, 0.0)) is Rashi.CANCER  # fixed -> Cancer
    assert calculate_varga_sign(27, _lon(Rashi.GEMINI, 0.0)) is Rashi.LIBRA  # dual -> Libra


@pytest.mark.parametrize(
    ("degree", "expected"),
    [
        (0.0, Rashi.ARIES),  # Mars 0-5
        (5.0, Rashi.AQUARIUS),  # Saturn 5-10
        (10.0, Rashi.SAGITTARIUS),  # Jupiter 10-18
        (18.0, Rashi.GEMINI),  # Mercury 18-25
        (25.0, Rashi.LIBRA),  # Venus 25-30
        (29.999, Rashi.LIBRA),
    ],
)
def test_d30_trimsamsa_odd_sign_ranges(degree: float, expected: Rashi) -> None:
    assert calculate_varga_sign(30, _lon(Rashi.ARIES, degree)) is expected


@pytest.mark.parametrize(
    ("degree", "expected"),
    [
        (0.0, Rashi.TAURUS),  # Venus 0-5
        (5.0, Rashi.VIRGO),  # Mercury 5-12
        (12.0, Rashi.PISCES),  # Jupiter 12-20
        (20.0, Rashi.CAPRICORN),  # Saturn 20-25
        (25.0, Rashi.SCORPIO),  # Mars 25-30
    ],
)
def test_d30_trimsamsa_even_sign_ranges(degree: float, expected: Rashi) -> None:
    assert calculate_varga_sign(30, _lon(Rashi.TAURUS, degree)) is expected


def test_d40_khavedamsa_odd_even_absolute_starts() -> None:
    assert calculate_varga_sign(40, _lon(Rashi.ARIES, 0.0)) is Rashi.ARIES  # odd -> Aries
    assert calculate_varga_sign(40, _lon(Rashi.TAURUS, 0.0)) is Rashi.LIBRA  # even -> Libra


def test_d45_akshavedamsa_modality_absolute_starts() -> None:
    assert calculate_varga_sign(45, _lon(Rashi.ARIES, 0.0)) is Rashi.ARIES  # movable -> Aries
    assert calculate_varga_sign(45, _lon(Rashi.TAURUS, 0.0)) is Rashi.LEO  # fixed -> Leo
    assert (
        calculate_varga_sign(45, _lon(Rashi.GEMINI, 0.0)) is Rashi.SAGITTARIUS
    )  # dual -> Sagittarius


def test_d60_shashtiamsa_always_same_sign_start_sequential() -> None:
    assert calculate_varga_sign(60, _lon(Rashi.ARIES, 0.0)) is Rashi.ARIES
    assert calculate_varga_sign(60, _lon(Rashi.ARIES, 0.5)) is Rashi.TAURUS
    assert calculate_varga_sign(60, _lon(Rashi.ARIES, 29.5)) is Rashi.PISCES


def test_exact_upper_boundary_never_overflows_part_index() -> None:
    # 30.0 is exclusive in principle (degree_within_sign never reaches it),
    # but float imprecision must never push a part index out of range.
    for varga in SUPPORTED_VARGAS:
        calculate_varga_sign(varga, _lon(Rashi.PISCES, 29.999999999))
