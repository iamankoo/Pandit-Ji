import pytest

from pandit_astro_engine.rashi import (
    RASHI_MODALITY,
    Modality,
    Rashi,
    degree_within_sign,
    offset_sign,
    rashi_from_index,
    rashi_from_longitude,
    rashi_index,
    sign_index_from_longitude,
)


@pytest.mark.parametrize(
    ("longitude", "expected_rashi", "expected_degree"),
    [
        (0.0, Rashi.ARIES, 0.0),
        (29.999, Rashi.ARIES, 29.999),
        (30.0, Rashi.TAURUS, 0.0),
        (359.999, Rashi.PISCES, 29.999),
        (360.0, Rashi.ARIES, 0.0),  # normalizes
        (720.0 + 45.0, Rashi.TAURUS, 15.0),  # unwrapped input normalizes too
    ],
)
def test_sign_boundaries(longitude: float, expected_rashi: Rashi, expected_degree: float) -> None:
    assert rashi_from_longitude(longitude) is expected_rashi
    assert degree_within_sign(longitude) == pytest.approx(expected_degree, abs=1e-9)


def test_sign_index_from_longitude_full_cycle() -> None:
    for index in range(12):
        longitude = index * 30.0 + 5.0
        assert sign_index_from_longitude(longitude) == index


def test_rashi_index_round_trip() -> None:
    for index, rashi in enumerate(
        [
            Rashi.ARIES,
            Rashi.TAURUS,
            Rashi.GEMINI,
            Rashi.CANCER,
            Rashi.LEO,
            Rashi.VIRGO,
            Rashi.LIBRA,
            Rashi.SCORPIO,
            Rashi.SAGITTARIUS,
            Rashi.CAPRICORN,
            Rashi.AQUARIUS,
            Rashi.PISCES,
        ]
    ):
        assert rashi_index(rashi) == index
        assert rashi_from_index(index) is rashi


def test_offset_sign_counts_inclusively() -> None:
    assert offset_sign(Rashi.ARIES, 1) is Rashi.ARIES
    assert offset_sign(Rashi.ARIES, 5) is Rashi.LEO
    assert offset_sign(Rashi.ARIES, 9) is Rashi.SAGITTARIUS
    assert offset_sign(Rashi.PISCES, 7) is Rashi.VIRGO  # wraps past Aries


def test_all_twelve_signs_have_a_modality() -> None:
    assert set(RASHI_MODALITY) == set(Rashi)
    counts: dict[Modality, int] = {Modality.MOVABLE: 0, Modality.FIXED: 0, Modality.DUAL: 0}
    for modality in RASHI_MODALITY.values():
        counts[modality] += 1
    assert counts == {Modality.MOVABLE: 4, Modality.FIXED: 4, Modality.DUAL: 4}


def test_opposite_signs_share_modality() -> None:
    for rashi in Rashi:
        opposite = rashi_from_index(rashi_index(rashi) + 6)
        assert RASHI_MODALITY[rashi] == RASHI_MODALITY[opposite]
