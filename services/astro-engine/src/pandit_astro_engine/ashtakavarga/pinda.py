"""Pinda Sadhana (Phase 9 WP-A3): Rasi Pinda, Graha Pinda and Yoga Pinda,
pure functions over one chart's Ekadhipatya-corrected values.

Source: BPHS Ch. 69 "Pinda Sadhana" (printed pp. 878-880, IMAGE-TRANSLATION).
All three totals are exact-integer sums, verified against the chapter's own
worked example (Rasi Pinda 100, Graha Pinda 48, Yoga Pinda 148 for the same
natal chart used for the WP-A2 reduction fixtures).

Graha Pinda is deliberately left `NOT_EVALUABLE` rather than guessed for two
cases neither the verse nor the worked example resolves:
  - a sign occupied solely by Mercury with a nonzero value (the verse and
    the printed Grahamana Chakra table disagree on Mercury's multiplier,
    5 vs 6, and the chapter's own example never isolates a Mercury-only
    occupied sign to arbitrate);
  - a sign occupied by more than one classical planet at once (no source
    read states an aggregation rule).
A sign whose Ekadhipatya-corrected value is 0 never triggers either case,
since its product is 0 regardless of which multiplier would apply -- this
matches the source's own worked example, which silently skips Aquarius
(occupied by three planets, value 0) without comment.
"""

from __future__ import annotations

from pandit_astro_engine.ashtakavarga.constants import (
    GRAHA_MULTIPLIER,
    RASI_MULTIPLIER,
    Contributor,
)
from pandit_astro_engine.ashtakavarga.models import (
    AshtakavargaStatus,
    GrahaPindaContribution,
    GrahaPindaReason,
    GrahaPindaStatus,
    PindaResult,
)
from pandit_astro_engine.ashtakavarga.reductions import classical_occupants
from pandit_astro_engine.rashi import RASHI_ORDER, Rashi


def compute_rasi_pinda(ekadhipatya_corrected: dict[Rashi, int]) -> int:
    """Ch. 69 v. 1-2: sum over all 12 signs of (Ekadhipatya-corrected value)
    times (that sign's Rasimana multiplier)."""
    return sum(ekadhipatya_corrected[sign] * RASI_MULTIPLIER[sign] for sign in RASHI_ORDER)


def compute_graha_pinda(
    ekadhipatya_corrected: dict[Rashi, int],
    occupancy: dict[Rashi, frozenset[Contributor]],
) -> tuple[
    GrahaPindaStatus, GrahaPindaReason | None, int | None, tuple[GrahaPindaContribution, ...]
]:
    """Ch. 69 v. 1-2: sum over signs occupied by exactly one classical planet
    (Rahu/Ketu excluded, per the source's own words) of (Ekadhipatya-corrected
    value) times (that planet's Grahamana multiplier)."""
    contributions: list[GrahaPindaContribution] = []
    total = 0
    status = GrahaPindaStatus.AVAILABLE
    reason: GrahaPindaReason | None = None

    for sign in RASHI_ORDER:
        value = ekadhipatya_corrected[sign]
        occupants = classical_occupants(occupancy, sign)

        if not occupants:
            contributions.append(
                GrahaPindaContribution(sign=sign, ekadhipatya_value=value, product=0)
            )
            continue

        if len(occupants) > 1:
            if value == 0:
                contributions.append(
                    GrahaPindaContribution(sign=sign, ekadhipatya_value=value, product=0)
                )
                continue
            if status == GrahaPindaStatus.AVAILABLE:
                status, reason = (
                    GrahaPindaStatus.NOT_EVALUABLE,
                    GrahaPindaReason.MULTIPLE_OCCUPANTS_UNSUPPORTED,
                )
            contributions.append(
                GrahaPindaContribution(
                    sign=sign,
                    ekadhipatya_value=value,
                    status=GrahaPindaStatus.NOT_EVALUABLE,
                    reason_code=GrahaPindaReason.MULTIPLE_OCCUPANTS_UNSUPPORTED,
                )
            )
            continue

        occupant = next(iter(occupants))
        if occupant == Contributor.MERCURY:
            if value == 0:
                contributions.append(
                    GrahaPindaContribution(
                        sign=sign, ekadhipatya_value=0, occupying_contributor=occupant, product=0
                    )
                )
                continue
            if status == GrahaPindaStatus.AVAILABLE:
                status, reason = (
                    GrahaPindaStatus.NOT_EVALUABLE,
                    GrahaPindaReason.MERCURY_MULTIPLIER_CONFLICT,
                )
            contributions.append(
                GrahaPindaContribution(
                    sign=sign,
                    ekadhipatya_value=value,
                    occupying_contributor=occupant,
                    status=GrahaPindaStatus.NOT_EVALUABLE,
                    reason_code=GrahaPindaReason.MERCURY_MULTIPLIER_CONFLICT,
                )
            )
            continue

        multiplier = GRAHA_MULTIPLIER[occupant]
        product = value * multiplier
        total += product
        contributions.append(
            GrahaPindaContribution(
                sign=sign,
                ekadhipatya_value=value,
                occupying_contributor=occupant,
                multiplier=multiplier,
                product=product,
            )
        )

    if status == GrahaPindaStatus.NOT_EVALUABLE:
        return status, reason, None, tuple(contributions)
    return status, None, total, tuple(contributions)


def compute_pinda(
    chart: Contributor,
    ekadhipatya_corrected: dict[Rashi, int],
    occupancy: dict[Rashi, frozenset[Contributor]],
) -> PindaResult:
    """Rasi Pinda, Graha Pinda and Yoga Pinda (their sum) for one chart.
    Callable only once `ekadhipatya_corrected` is fully known (a resolved
    12-sign map, never a partial one) -- see `reductions.apply_ekadhipatya_shodhana`
    and `AshtakavargaCalculationService._reduce_and_pinda` for the case
    where it is not (`EkadhipatyaConflict`), which never reaches this
    function at all."""
    rasi_pinda = compute_rasi_pinda(ekadhipatya_corrected)
    status, reason, graha_pinda, contributions = compute_graha_pinda(
        ekadhipatya_corrected, occupancy
    )
    yoga_pinda = rasi_pinda + graha_pinda if graha_pinda is not None else None
    return PindaResult(
        chart=chart,
        status=AshtakavargaStatus.SUCCESS,
        rasi_pinda=rasi_pinda,
        graha_pinda_status=status,
        graha_pinda_reason=reason,
        graha_pinda=graha_pinda,
        graha_contributions=contributions,
        yoga_pinda=yoga_pinda,
    )
