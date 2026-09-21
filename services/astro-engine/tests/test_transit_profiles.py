"""The source tables (docs/ASTROLOGY_STANDARDS.md TR-04 to TR-06) are exactly
what the research recorded, and the conflicts stay visible."""

from __future__ import annotations

import pytest

from pandit_astro_engine.models import CelestialBody as B
from pandit_astro_engine.transits import profiles as P

SEVEN = (B.SUN, B.MOON, B.MARS, B.MERCURY, B.JUPITER, B.VENUS, B.SATURN)


def reading(reading_id: str) -> P.FavourableReadingDef:
    return next(r for r in P.FAVOURABLE_READINGS if r.reading_id == reading_id)


def test_four_readings_with_the_recorded_ids() -> None:
    assert P.FAVOURABLE_READING_IDS == (
        "GOCHARA_FAVOURABLE_PHALADEEPIKA_SASTRI_XXVI_2",
        "GOCHARA_FAVOURABLE_BRIHAT_SAMHITA_SASTRI_CIV_4",
        "GOCHARA_FAVOURABLE_BRIHAT_JATAKA_SASTRI_IX_1_7",
        "GOCHARA_FAVOURABLE_BPHS_KAPOOR_66_DERIVED",
    )


def test_phaladeepika_sets_match_sloka_2_with_the_eleventh_for_all() -> None:
    houses = reading(P.FAV_PHALADEEPIKA_ID).houses
    assert houses[B.SUN] == {3, 6, 10, 11}
    assert houses[B.MOON] == {1, 3, 6, 7, 10, 11}
    assert houses[B.MARS] == houses[B.SATURN] == {3, 6, 11}
    assert houses[B.MERCURY] == {2, 4, 6, 8, 10, 11}
    assert houses[B.JUPITER] == {2, 5, 7, 9, 11}
    assert houses[B.VENUS] == set(range(1, 13)) - {6, 7, 10}
    for body in SEVEN:
        assert 11 in houses[body]


def test_the_six_non_moon_planets_agree_across_all_four_readings() -> None:
    for body in (B.SUN, B.MARS, B.MERCURY, B.JUPITER, B.VENUS, B.SATURN):
        sets = {r.houses[body] for r in P.FAVOURABLE_READINGS}
        assert len(sets) == 1, body


def test_moon_from_moon_readings_are_the_three_recorded_variants() -> None:
    by_id = {r.reading_id: r.houses[B.MOON] for r in P.FAVOURABLE_READINGS}
    assert by_id[P.FAV_PHALADEEPIKA_ID] == {1, 3, 6, 7, 10, 11}
    assert by_id[P.FAV_BRIHAT_SAMHITA_ID] == {1, 3, 6, 7, 10, 11}
    assert by_id[P.FAV_BRIHAT_JATAKA_ID] == {1, 3, 5, 7, 10, 11}
    assert by_id[P.FAV_BPHS_DERIVED_ID] == {1, 3, 6, 7, 9, 10, 11}


def test_moon_disagreement_is_exactly_houses_5_6_and_9() -> None:
    sets = [r.houses[B.MOON] for r in P.FAVOURABLE_READINGS]
    union = set().union(*sets)
    intersection = set.intersection(*(set(s) for s in sets))
    assert union - intersection == {5, 6, 9}
    assert intersection == {1, 3, 7, 10, 11}


def test_only_phaladeepika_covers_the_nodes_and_like_the_sun() -> None:
    covering = [r for r in P.FAVOURABLE_READINGS if B.RAHU in r.houses or B.KETU in r.houses]
    assert [r.reading_id for r in covering] == [P.FAV_PHALADEEPIKA_ID]
    houses = covering[0].houses
    assert houses[B.RAHU] == houses[B.KETU] == houses[B.SUN]
    assert P.readings_for(B.RAHU) == tuple(covering)


def test_labels_distinguish_source_from_derived() -> None:
    assert reading(P.FAV_BPHS_DERIVED_ID).label == P.EvidenceLabel.DERIVED_CALCULATION
    for reading_id in (P.FAV_PHALADEEPIKA_ID, P.FAV_BRIHAT_SAMHITA_ID, P.FAV_BRIHAT_JATAKA_ID):
        assert reading(reading_id).label == P.EvidenceLabel.SOURCE_SUPPORTED


def test_vedha_pairs_cover_exactly_the_phaladeepika_favourable_houses() -> None:
    houses = reading(P.FAV_PHALADEEPIKA_ID).houses
    for body in SEVEN:
        assert set(P.VEDHA_PAIRS[body]) == houses[body], body


@pytest.mark.parametrize(
    ("body", "pairs"),
    [
        (B.SUN, {11: 5, 3: 9, 10: 4, 6: 12}),
        (B.MOON, {7: 2, 1: 5, 6: 12, 11: 8, 10: 4, 3: 9}),
        (B.MARS, {3: 12, 11: 5, 6: 9}),
        (B.SATURN, {3: 12, 11: 5, 6: 9}),
        (B.MERCURY, {2: 5, 4: 3, 6: 9, 8: 1, 10: 8, 11: 12}),
        (B.JUPITER, {2: 12, 11: 8, 9: 10, 5: 4, 7: 3}),
        (B.VENUS, {1: 8, 2: 7, 3: 1, 4: 10, 5: 9, 8: 5, 9: 11, 12: 6, 11: 3}),
    ],
)
def test_vedha_table_is_exactly_the_verified_one(body: B, pairs: dict[int, int]) -> None:
    assert P.VEDHA_PAIRS[body] == pairs


def test_vedha_exceptions_are_the_two_stated_pairs_and_symmetric() -> None:
    assert P.VEDHA_EXEMPT == {
        B.SUN: {B.SATURN},
        B.SATURN: {B.SUN},
        B.MOON: {B.MERCURY},
        B.MERCURY: {B.MOON},
    }
    for body, exempt in P.VEDHA_EXEMPT.items():
        for other in exempt:
            assert body in P.VEDHA_EXEMPT[other]


def test_nodes_have_no_vedha_pairs() -> None:
    assert B.RAHU not in P.VEDHA_PAIRS and B.KETU not in P.VEDHA_PAIRS


def test_sade_sati_band_is_twelfth_first_second_from_the_moon() -> None:
    assert P.SADE_SATI_PHASE_BY_OFFSET == {11: 1, 0: 2, 1: 3}
    assert set(P.SADE_SATI_PHASE_NAMES.values()) == {
        "twelfth_from_moon",
        "first_from_moon",
        "second_from_moon",
    }


def test_reserved_modern_profiles_are_documented_but_not_the_active_one() -> None:
    assert P.SADE_SATI_ID not in P.RESERVED_MODERN_PROFILE_IDS
    assert P.RESERVED_MODERN_PROFILE_IDS == {
        "DHAIYA_SIGN_BASED_MODERN_V1",
        "ASHTAMA_SIGN_BASED_MODERN_V1",
        "SADE_SATI_DEGREE_45_MODERN_V1",
    }


def test_sade_sati_classical_status_denies_classical_certainty() -> None:
    text = P.SADE_SATI_CLASSICAL_STATUS.lower()
    assert "not found as a combined unit" in text
    assert "modern-tradition" in text
