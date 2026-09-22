"""Pure Ashtakavarga calculation (Phase 9 WP-A1): rotation of a profile's
own benefic-house lists onto the natal signs. No ephemeris access here; the
caller supplies natal longitudes (or use `NatalPositions.from_kundli`).

The rotation is the classical rule stated by every source read: a
contributor's list is "the Nth house counted from the contributor's own
sign", so for an absolute sign index `s` (0=Aries..11=Pisces) and a
contributor at natal sign index `p`, the house-from-that-contributor is
`((s - p) % 12) + 1`. This is verified against Brihat Jataka's own worked
example (Ch. IX sl. 8 / Ch. VII sl. 6, printed p. 205): the Mars chart for
that horoscope reproduces the printed dot/stroke counts in all 12 signs,
including the effectless cell (see
`services/astro-engine/tests/test_ashtakavarga_calculator.py`
`test_matches_brihat_jataka_worked_example`).
"""

from __future__ import annotations

from pandit_astro_engine.ashtakavarga.constants import PLANET_CHARTS, Contributor
from pandit_astro_engine.ashtakavarga.models import ChartResult, HouseMark, SarvashtakavargaResult
from pandit_astro_engine.ashtakavarga.profiles import AshtakavargaProfileDef
from pandit_astro_engine.rashi import RASHI_ORDER, Rashi


def house_from_contributor(sign_index: int, contributor_sign_index: int) -> int:
    """1..12, counted from the contributor's own sign (=1)."""
    return (sign_index - contributor_sign_index) % 12 + 1


def _compute_chart(
    chart: Contributor,
    benefic_table: dict[Contributor, tuple[int, ...]],
    effectless: dict[tuple[Contributor, Contributor], tuple[int, ...]],
    natal_sign_index: dict[Contributor, int],
) -> ChartResult:
    marks: dict[Rashi, dict[Contributor, HouseMark]] = {}
    benefic_count: dict[Rashi, int] = {}
    malefic_count: dict[Rashi, int] = {}
    effectless_count: dict[Rashi, int] = {}
    for sign_index, rashi in enumerate(RASHI_ORDER):
        row: dict[Contributor, HouseMark] = {}
        b = m = e = 0
        for contributor, benefic_houses in benefic_table.items():
            house = house_from_contributor(sign_index, natal_sign_index[contributor])
            effectless_houses = effectless.get((chart, contributor), ())
            if house in effectless_houses:
                mark = HouseMark.EFFECTLESS
                e += 1
            elif house in benefic_houses:
                mark = HouseMark.BENEFIC
                b += 1
            else:
                mark = HouseMark.MALEFIC
                m += 1
            row[contributor] = mark
        marks[rashi] = row
        benefic_count[rashi] = b
        malefic_count[rashi] = m
        effectless_count[rashi] = e
    return ChartResult(
        chart=chart,
        marks=marks,
        benefic_count=benefic_count,
        malefic_count=malefic_count,
        effectless_count=effectless_count,
        total_benefic=sum(benefic_count.values()),
    )


def compute_bhinnashtakavarga(
    profile: AshtakavargaProfileDef, natal_sign_index: dict[Contributor, int]
) -> tuple[ChartResult, ...]:
    """The seven planet charts, in `PLANET_CHARTS` order."""
    return tuple(
        _compute_chart(chart, profile.table[chart], profile.effectless_cells, natal_sign_index)
        for chart in PLANET_CHARTS
    )


def compute_sarvashtakavarga(charts: tuple[ChartResult, ...]) -> SarvashtakavargaResult:
    """Per-sign sum of `benefic_count` over the seven planet charts only."""
    benefic_count: dict[Rashi, int] = {
        rashi: sum(chart.benefic_count[rashi] for chart in charts) for rashi in RASHI_ORDER
    }
    return SarvashtakavargaResult(
        benefic_count=benefic_count, total_benefic=sum(benefic_count.values())
    )


def compute_lagna_chart(
    profile: AshtakavargaProfileDef, natal_sign_index: dict[Contributor, int]
) -> ChartResult | None:
    """BPHS's own eighth chart, for the Ascendant -- `None` under a profile
    that does not give the Ascendant its own chart (Brihat Jataka,
    Phaladeepika)."""
    if not profile.has_lagna_chart or profile.lagna_chart is None:
        return None
    return _compute_chart(Contributor.LAGNA, profile.lagna_chart, {}, natal_sign_index)
