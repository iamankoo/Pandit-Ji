"""Ashtakavarga calculator tests (Phase 9 WP-A1): the rotation arithmetic,
the independent Brihat Jataka worked example, and structural invariants
that must hold under every profile."""

from __future__ import annotations

from ashtakavarga_helpers import load_brihat_jataka_worked_example, natal_longitudes

from pandit_astro_engine.ashtakavarga.calculator import (
    compute_bhinnashtakavarga,
    compute_lagna_chart,
    compute_sarvashtakavarga,
    house_from_contributor,
)
from pandit_astro_engine.ashtakavarga.constants import (
    CHART_TOTAL_INVARIANT,
    CONTRIBUTOR_ORDER,
    GRAND_TOTAL_INVARIANT,
    Contributor,
)
from pandit_astro_engine.ashtakavarga.models import HouseMark
from pandit_astro_engine.ashtakavarga.profiles import (
    BPHS_GRID_ID,
    BPHS_VERSE_ID,
    BRIHAT_JATAKA_ID,
    PHALADEEPIKA_ID,
    PROFILES,
)
from pandit_astro_engine.rashi import RASHI_ORDER, Rashi

_ALL_PROFILE_IDS = (BRIHAT_JATAKA_ID, PHALADEEPIKA_ID, BPHS_GRID_ID, BPHS_VERSE_ID)


def test_house_from_contributor_counts_the_contributors_own_sign_as_house_one() -> None:
    assert house_from_contributor(sign_index=3, contributor_sign_index=3) == 1
    assert house_from_contributor(sign_index=4, contributor_sign_index=3) == 2
    assert house_from_contributor(sign_index=2, contributor_sign_index=3) == 12  # wraps backward
    assert house_from_contributor(sign_index=0, contributor_sign_index=11) == 2  # wraps forward


def test_matches_brihat_jataka_worked_example() -> None:
    """Brihat Jataka Ch. IX sl. 8 / Ch. VII sl. 6, printed p. 205 -- an
    independently source-published example. Its expected values were not
    produced by this calculator; they are the printed dot/stroke counts."""
    example = load_brihat_jataka_worked_example()
    natal = natal_longitudes(example["natal_longitudes_degrees"])
    profile = PROFILES[example["profile_id"]]
    charts = compute_bhinnashtakavarga(profile, {c: _sign_index(natal[c]) for c in natal})
    mars_chart = next(c for c in charts if c.chart == Contributor.MARS)

    for sign_name, expected in example["expected_benefic_count_by_sign"].items():
        rashi = Rashi(sign_name)
        assert mars_chart.benefic_count[rashi] == expected, sign_name
    for sign_name, expected in example["expected_malefic_count_by_sign"].items():
        rashi = Rashi(sign_name)
        assert mars_chart.malefic_count[rashi] == expected, sign_name
    for sign_name, expected in example["expected_effectless_count_by_sign"].items():
        rashi = Rashi(sign_name)
        assert mars_chart.effectless_count[rashi] == expected, sign_name

    assert mars_chart.total_benefic == example["expected_total_benefic"] == 39
    total_malefic = sum(mars_chart.malefic_count.values())
    assert total_malefic == example["expected_total_malefic"] == 56


def _sign_index(longitude: float) -> int:
    from pandit_astro_engine.rashi import sign_index_from_longitude

    return sign_index_from_longitude(longitude)


def test_every_house_gets_exactly_eight_marks_under_brihat_jataka() -> None:
    """Eight contributors, every house of every chart -- no contributor is
    ever silently dropped."""
    natal = {c: float(i * 37) for i, c in enumerate(CONTRIBUTOR_ORDER)}
    profile = PROFILES[BRIHAT_JATAKA_ID]
    signs = {c: _sign_index(lon) for c, lon in natal.items()}
    charts = compute_bhinnashtakavarga(profile, signs)
    for chart in charts:
        for rashi in RASHI_ORDER:
            total = (
                chart.benefic_count[rashi]
                + chart.malefic_count[rashi]
                + chart.effectless_count[rashi]
            )
            assert total == 8, (chart.chart, rashi)
            assert len(chart.marks[rashi]) == 8


def test_chart_total_is_invariant_under_natal_position() -> None:
    """A contributor's benefic-house list is just relabelled by the rotation
    (each house is hit by exactly one sign), so a chart's total over all 12
    signs never depends on where the contributors actually are."""
    natal_a = {c: 0.0 for c in CONTRIBUTOR_ORDER}
    natal_b = {c: float((i * 53) % 360) for i, c in enumerate(CONTRIBUTOR_ORDER)}
    for profile_id in _ALL_PROFILE_IDS:
        profile = PROFILES[profile_id]
        expected_grand_total = GRAND_TOTAL_INVARIANT + (3 if profile_id == BPHS_VERSE_ID else 0)
        for natal in (natal_a, natal_b):
            signs = {c: _sign_index(lon) for c, lon in natal.items()}
            charts = compute_bhinnashtakavarga(profile, signs)
            assert sum(chart.total_benefic for chart in charts) == expected_grand_total
            if profile_id != BPHS_VERSE_ID:
                for chart in charts:
                    assert chart.total_benefic == CHART_TOTAL_INVARIANT[chart.chart]


def test_sarvashtakavarga_sums_the_seven_planet_charts_only() -> None:
    natal = {c: 0.0 for c in CONTRIBUTOR_ORDER}
    signs = {c: _sign_index(lon) for c, lon in natal.items()}
    profile = PROFILES[BRIHAT_JATAKA_ID]
    charts = compute_bhinnashtakavarga(profile, signs)
    sarva = compute_sarvashtakavarga(charts)
    assert sarva.total_benefic == GRAND_TOTAL_INVARIANT
    for rashi in RASHI_ORDER:
        assert sarva.benefic_count[rashi] == sum(c.benefic_count[rashi] for c in charts)


def test_lagna_chart_absent_for_brihat_jataka_and_phaladeepika() -> None:
    natal = {c: 0.0 for c in CONTRIBUTOR_ORDER}
    signs = {c: _sign_index(lon) for c, lon in natal.items()}
    for profile_id in (BRIHAT_JATAKA_ID, PHALADEEPIKA_ID):
        assert compute_lagna_chart(PROFILES[profile_id], signs) is None


def test_lagna_chart_present_and_totals_49_for_bphs_profiles() -> None:
    natal = {c: 0.0 for c in CONTRIBUTOR_ORDER}
    signs = {c: _sign_index(lon) for c, lon in natal.items()}
    for profile_id in (BPHS_GRID_ID, BPHS_VERSE_ID):
        lagna_chart = compute_lagna_chart(PROFILES[profile_id], signs)
        assert lagna_chart is not None
        assert lagna_chart.chart == Contributor.LAGNA
        assert lagna_chart.total_benefic == 49


def test_brihat_jataka_effectless_cell_is_never_marked_benefic_or_malefic() -> None:
    natal = {c: 0.0 for c in CONTRIBUTOR_ORDER}
    signs = {c: _sign_index(lon) for c, lon in natal.items()}
    profile = PROFILES[BRIHAT_JATAKA_ID]
    charts = compute_bhinnashtakavarga(profile, signs)
    mars_chart = next(c for c in charts if c.chart == Contributor.MARS)
    # With every contributor at Aries (sign index 0), house 10 from the Moon
    # ((s - 0) % 12 + 1 == 10 => s == 9) falls at absolute sign index 9, Capricorn.
    assert mars_chart.marks[Rashi.CAPRICORN][Contributor.MOON] == HouseMark.EFFECTLESS
    assert sum(mars_chart.effectless_count.values()) == 1


def test_worked_example_effectless_cell_is_aquarius_for_that_natal_chart() -> None:
    """Cross-check against the printed worked example
    (`ashtakavarga_brihat_jataka_worked_example.json`): there the Moon sits in
    a different sign than in the previous test, so the same
    Ch. IX sl. 3 rule (10th from the Moon, Mars's chart) lands on a different absolute
    sign -- Aquarius, not Capricorn. Confirms the effectless rule follows the Moon's
    actual position rather than a fixed sign."""
    example = load_brihat_jataka_worked_example()
    natal = natal_longitudes(example["natal_longitudes_degrees"])
    profile = PROFILES[example["profile_id"]]
    signs = {c: _sign_index(lon) for c, lon in natal.items()}
    charts = compute_bhinnashtakavarga(profile, signs)
    mars_chart = next(c for c in charts if c.chart == Contributor.MARS)
    assert mars_chart.marks[Rashi.AQUARIUS][Contributor.MOON] == HouseMark.EFFECTLESS


def test_bphs_profiles_have_no_effectless_cells() -> None:
    natal = {c: 0.0 for c in CONTRIBUTOR_ORDER}
    signs = {c: _sign_index(lon) for c, lon in natal.items()}
    for profile_id in (PHALADEEPIKA_ID, BPHS_GRID_ID, BPHS_VERSE_ID):
        charts = compute_bhinnashtakavarga(PROFILES[profile_id], signs)
        for chart in charts:
            assert sum(chart.effectless_count.values()) == 0
