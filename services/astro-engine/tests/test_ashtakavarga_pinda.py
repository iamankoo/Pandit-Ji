"""Pinda Sadhana tests (Phase 9 WP-A3): Rasi Pinda, Graha Pinda, Yoga Pinda,
and the two deliberately-not-guessed edge cases (Mercury's conflicted
multiplier, multiple classical occupants of one sign)."""

from __future__ import annotations

from pandit_astro_engine.ashtakavarga.constants import Contributor
from pandit_astro_engine.ashtakavarga.models import GrahaPindaReason, GrahaPindaStatus
from pandit_astro_engine.ashtakavarga.pinda import (
    compute_graha_pinda,
    compute_pinda,
    compute_rasi_pinda,
)
from pandit_astro_engine.rashi import Rashi

# BPHS Ch. 69 continued worked example (printed p. 879-880): the Sun's
# Ekadhipatya-corrected values, occupancy from the same reconstructed chart
# used throughout Ch. 67/68 (see test_ashtakavarga_reductions.py).
_SUN_EKADHIPATYA = {
    Rashi.ARIES: 0,
    Rashi.TAURUS: 1,
    Rashi.GEMINI: 1,
    Rashi.CANCER: 4,
    Rashi.LEO: 1,
    Rashi.VIRGO: 0,
    Rashi.LIBRA: 0,
    Rashi.SCORPIO: 4,
    Rashi.SAGITTARIUS: 1,
    Rashi.CAPRICORN: 3,
    Rashi.AQUARIUS: 0,
    Rashi.PISCES: 0,
}


def _occupancy(mapping: dict[Rashi, frozenset[Contributor]]) -> dict[Rashi, frozenset[Contributor]]:
    return {sign: mapping.get(sign, frozenset()) for sign in Rashi}


_SUN_CHART_OCCUPANCY = _occupancy(
    {
        Rashi.TAURUS: frozenset({Contributor.MARS}),
        Rashi.GEMINI: frozenset({Contributor.MOON}),
        Rashi.SCORPIO: frozenset({Contributor.SATURN}),
        Rashi.SAGITTARIUS: frozenset(),  # Ketu only -- not a classical-planet occupant
        Rashi.CAPRICORN: frozenset({Contributor.SUN}),
        Rashi.AQUARIUS: frozenset(
            {Contributor.LAGNA, Contributor.MERCURY, Contributor.JUPITER, Contributor.VENUS}
        ),
    }
)


def test_rasi_pinda_matches_bphs_worked_example() -> None:
    assert compute_rasi_pinda(_SUN_EKADHIPATYA) == 100


def test_graha_pinda_matches_bphs_worked_example() -> None:
    status, reason, total, contributions = compute_graha_pinda(
        _SUN_EKADHIPATYA, _SUN_CHART_OCCUPANCY
    )
    assert status == GrahaPindaStatus.AVAILABLE
    assert reason is None
    assert total == 48
    nonzero = {
        c.sign: (c.occupying_contributor, c.multiplier, c.product)
        for c in contributions
        if c.product
    }
    assert nonzero == {
        Rashi.TAURUS: (Contributor.MARS, 8, 8),
        Rashi.GEMINI: (Contributor.MOON, 5, 5),
        Rashi.SCORPIO: (Contributor.SATURN, 5, 20),
        Rashi.CAPRICORN: (Contributor.SUN, 5, 15),
    }


def test_aquarius_contributes_zero_despite_four_occupants_because_its_value_is_zero() -> None:
    """BPHS's own example silently skips Aquarius (occupied by Lagna, Mercury,
    Jupiter and Venus) without comment -- because its Ekadhipatya value is 0,
    the multi-occupant ambiguity never has to be resolved for this chart."""
    status, reason, total, contributions = compute_graha_pinda(
        _SUN_EKADHIPATYA, _SUN_CHART_OCCUPANCY
    )
    aquarius = next(c for c in contributions if c.sign == Rashi.AQUARIUS)
    assert aquarius.product == 0
    assert aquarius.status == GrahaPindaStatus.AVAILABLE
    assert status == GrahaPindaStatus.AVAILABLE  # the whole chart is unaffected


def test_yoga_pinda_is_rasi_plus_graha() -> None:
    result = compute_pinda(Contributor.SUN, _SUN_EKADHIPATYA, _SUN_CHART_OCCUPANCY)
    assert result.rasi_pinda == 100
    assert result.graha_pinda == 48
    assert result.yoga_pinda == 148


def test_mercury_sole_occupant_of_a_nonzero_sign_is_not_evaluable() -> None:
    """The verse (6) and the printed table (5) disagree and no worked
    example arbitrates -- the conflict is carried forward, not guessed."""
    ekadhipatya = {r: 0 for r in Rashi}
    ekadhipatya[Rashi.GEMINI] = 3
    occupancy = _occupancy({Rashi.GEMINI: frozenset({Contributor.MERCURY})})
    status, reason, total, contributions = compute_graha_pinda(ekadhipatya, occupancy)
    assert status == GrahaPindaStatus.NOT_EVALUABLE
    assert reason == GrahaPindaReason.MERCURY_MULTIPLIER_CONFLICT
    assert total is None
    gemini = next(c for c in contributions if c.sign == Rashi.GEMINI)
    assert gemini.product is None
    assert gemini.multiplier is None


def test_mercury_sole_occupant_of_a_zero_value_sign_is_still_available() -> None:
    """The conflict never materializes when the term would be 0 regardless
    of which multiplier applies -- matching BPHS's own Aquarius example."""
    ekadhipatya = {r: 0 for r in Rashi}
    occupancy = _occupancy({Rashi.GEMINI: frozenset({Contributor.MERCURY})})
    status, _reason, total, _contributions = compute_graha_pinda(ekadhipatya, occupancy)
    assert status == GrahaPindaStatus.AVAILABLE
    assert total == 0


def test_pinda_with_mercury_conflict_has_no_yoga_pinda() -> None:
    ekadhipatya = {r: 0 for r in Rashi}
    ekadhipatya[Rashi.GEMINI] = 3
    occupancy = _occupancy({Rashi.GEMINI: frozenset({Contributor.MERCURY})})
    result = compute_pinda(Contributor.SUN, ekadhipatya, occupancy)
    assert result.rasi_pinda == 3 * 8  # Rasi Pinda is unaffected by the Graha conflict
    assert result.graha_pinda is None
    assert result.graha_pinda_status == GrahaPindaStatus.NOT_EVALUABLE
    assert result.yoga_pinda is None


def test_multiple_classical_occupants_of_a_nonzero_sign_is_not_evaluable() -> None:
    """No source read states an aggregation rule for two classical planets
    sharing one sign; not inferred."""
    ekadhipatya = {r: 0 for r in Rashi}
    ekadhipatya[Rashi.TAURUS] = 2
    occupancy = _occupancy({Rashi.TAURUS: frozenset({Contributor.MARS, Contributor.SATURN})})
    status, reason, total, contributions = compute_graha_pinda(ekadhipatya, occupancy)
    assert status == GrahaPindaStatus.NOT_EVALUABLE
    assert reason == GrahaPindaReason.MULTIPLE_OCCUPANTS_UNSUPPORTED
    assert total is None


def test_multiple_classical_occupants_of_a_zero_value_sign_is_still_available() -> None:
    ekadhipatya = {r: 0 for r in Rashi}
    occupancy = _occupancy({Rashi.TAURUS: frozenset({Contributor.MARS, Contributor.SATURN})})
    status, _reason, total, _contributions = compute_graha_pinda(ekadhipatya, occupancy)
    assert status == GrahaPindaStatus.AVAILABLE
    assert total == 0


def test_lagna_alone_never_contributes_to_graha_pinda() -> None:
    """The Ascendant is not a graha; a sign occupied only by Lagna is treated
    like an unoccupied sign for Graha Pinda purposes."""
    ekadhipatya = {r: 5 for r in Rashi}
    occupancy = _occupancy({Rashi.ARIES: frozenset({Contributor.LAGNA})})
    status, reason, total, contributions = compute_graha_pinda(ekadhipatya, occupancy)
    aries = next(c for c in contributions if c.sign == Rashi.ARIES)
    assert aries.occupying_contributor is None
    assert aries.product == 0
