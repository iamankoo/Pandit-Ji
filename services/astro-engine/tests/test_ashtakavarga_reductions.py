"""Trikona and Ekadhipatya Shodhana tests (Phase 9 WP-A2)."""

from __future__ import annotations

from ashtakavarga_helpers import natal_longitudes

from pandit_astro_engine.ashtakavarga.constants import Contributor
from pandit_astro_engine.ashtakavarga.reductions import (
    apply_ekadhipatya_shodhana,
    apply_trikona_shodhana,
    classical_occupants,
    is_occupied,
    occupancy_map,
)
from pandit_astro_engine.rashi import Rashi

# BPHS Ch. 67 "Example Horoscope" (printed p. 868), the raw benefic counts of
# the Sun's own Bhinnashtakavarga chart, reconstructed from the printed
# "Number of Rekhas" row (p. 869) -- an independent, source-published input.
_SUN_CHART_BENEFIC_COUNT = {
    Rashi.ARIES: 4,
    Rashi.TAURUS: 3,
    Rashi.GEMINI: 4,
    Rashi.CANCER: 6,
    Rashi.LEO: 5,
    Rashi.VIRGO: 2,
    Rashi.LIBRA: 3,
    Rashi.SCORPIO: 6,
    Rashi.SAGITTARIUS: 5,
    Rashi.CAPRICORN: 5,
    Rashi.AQUARIUS: 3,
    Rashi.PISCES: 2,
}
_SUN_CHART_TRIKONA_EXPECTED = {
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


def test_trikona_shodhana_matches_bphs_worked_example() -> None:
    result = apply_trikona_shodhana(_SUN_CHART_BENEFIC_COUNT)
    assert result == _SUN_CHART_TRIKONA_EXPECTED


def test_trikona_shodhana_is_a_no_op_when_a_group_member_is_zero() -> None:
    counts = {r: 5 for r in Rashi}
    counts[Rashi.LEO] = 0  # Aries-Leo-Sagittarius trikona
    result = apply_trikona_shodhana(counts)
    assert result[Rashi.LEO] == 0
    assert result[Rashi.ARIES] == 5
    assert result[Rashi.SAGITTARIUS] == 5


def test_trikona_shodhana_zeros_an_equal_group() -> None:
    counts = {r: 3 for r in Rashi}
    result = apply_trikona_shodhana(counts)
    assert all(v == 0 for v in result.values())


# --------------------------------------------------------------------------
# Ekadhipatya Shodhana -- BPHS Ch. 68 "abstract illustration" (printed p. 876):
# a contributor-agnostic teaching example, tested directly against
# `apply_ekadhipatya_shodhana` without going through a specific planet's
# Bhinnashtakavarga chart (the illustration is not tied to one).
#
# Occupied: Aries (Moon), Taurus (Mars, Saturn), Gemini (Jupiter, Rahu),
# Capricorn (Sun, Mercury, Venus). Everything else empty.
#
# Two of the five lordship pairs in this printed table are "exactly one
# occupied, equal Trikona-corrected value" -- Saturn's (Capricorn/Aquarius,
# 2 and 2) and Mercury's (Gemini/Virgo, 4 and 4) -- and BPHS's own printed
# numbers answer that identical shape two different ways (Capricorn stays
# unchanged; Gemini prints as if zeroed). This is the conflict `docs
# /ASTROLOGY_STANDARDS.md` v1.8.0 AV-10 records: NEITHER reading is applied;
# the function reports both signs of such a pair as unresolved instead
# (`EkadhipatyaConflict`), and the caller is expected to treat the whole
# chart's Ekadhipatya result as unavailable, never silently pick one side.
# --------------------------------------------------------------------------

_ABSTRACT_TRIKONA = {
    Rashi.ARIES: 1,
    Rashi.TAURUS: 2,
    Rashi.GEMINI: 4,
    Rashi.CANCER: 0,
    Rashi.LEO: 0,
    Rashi.VIRGO: 4,
    Rashi.LIBRA: 1,
    Rashi.SCORPIO: 3,
    Rashi.SAGITTARIUS: 1,
    Rashi.CAPRICORN: 2,
    Rashi.AQUARIUS: 2,
    Rashi.PISCES: 2,
}
_ABSTRACT_OCCUPIED_SIGNS = {Rashi.ARIES, Rashi.TAURUS, Rashi.GEMINI, Rashi.CAPRICORN}


def _abstract_occupancy() -> dict[Rashi, frozenset[Contributor]]:
    # Only occupancy (with-a-planet vs without) matters to the formula, not
    # which specific contributor -- a single placeholder contributor per
    # occupied sign exercises the same code path as any real chart.
    return {
        sign: (frozenset({Contributor.SUN}) if sign in _ABSTRACT_OCCUPIED_SIGNS else frozenset())
        for sign in Rashi
    }


def test_ekadhipatya_shodhana_detects_the_capricorn_aquarius_conflict() -> None:
    """Detection: the exact printed data (Capricorn/Aquarius, one occupied,
    both 2) is reported as an unresolved conflict, not silently resolved
    either way. The whole chart's corrected map is withheld (`None`), never
    partially filled in around the disputed pair."""
    corrected, conflicts = apply_ekadhipatya_shodhana(
        _ABSTRACT_TRIKONA, _abstract_occupancy(), rahu_sign=None, ketu_sign=None
    )
    assert corrected is None
    signs_in_conflict = {(c.occupied_sign, c.empty_sign) for c in conflicts}
    assert (Rashi.CAPRICORN, Rashi.AQUARIUS) in signs_in_conflict


def test_ekadhipatya_conflict_preserves_both_readings_with_provenance() -> None:
    """Both of BPHS's own printed readings are kept verbatim on the conflict
    record, with a source citation -- neither is chosen."""
    _corrected, conflicts = apply_ekadhipatya_shodhana(
        _ABSTRACT_TRIKONA, _abstract_occupancy(), rahu_sign=None, ketu_sign=None
    )
    capricorn_conflict = next(c for c in conflicts if c.occupied_sign == Rashi.CAPRICORN)
    assert capricorn_conflict.empty_sign == Rashi.AQUARIUS
    assert capricorn_conflict.shared_value == 2
    # Reading A (Capricorn/Aquarius pair itself, as printed): occupied unchanged.
    assert capricorn_conflict.reading_a_occupied_value == 2
    # Reading B (Gemini/Virgo pair, same table, same shape): occupied zeroed too.
    assert capricorn_conflict.reading_b_occupied_value == 0
    assert "Ch. 68" in capricorn_conflict.source_note
    assert "876" in capricorn_conflict.source_note


def test_ekadhipatya_shodhana_mars_and_venus_pairs_isolated_from_the_conflict() -> None:
    """Mars (Aries/Scorpio) and Venus (Taurus/Libra), both one-occupied and
    UNEQUAL, are unaffected by the Capricorn/Aquarius and Gemini/Virgo
    conflicts. Saturn's pair (Capricorn/Aquarius) AND Mercury's pair
    (Gemini/Virgo) are both equal-one-occupied in the real printed data, so
    both are set to distinct (unequal) values here, deliberately different
    from BPHS's own printed numbers, purely to isolate Mars and Venus from
    the two known conflicts in this one test; the real 2/2 and 4/4 cases are
    exercised by `test_ekadhipatya_shodhana_detects_the_capricorn_aquarius_conflict`
    and the Gemini/Virgo entry it also returns."""
    trikona = dict(_ABSTRACT_TRIKONA)
    trikona[Rashi.CAPRICORN], trikona[Rashi.AQUARIUS] = 2, 5
    trikona[Rashi.GEMINI], trikona[Rashi.VIRGO] = 4, 1
    corrected, conflicts = apply_ekadhipatya_shodhana(
        trikona, _abstract_occupancy(), rahu_sign=None, ketu_sign=None
    )
    assert conflicts == ()
    assert corrected is not None
    assert corrected[Rashi.ARIES] == 1 and corrected[Rashi.SCORPIO] == 2  # Mars pair
    assert corrected[Rashi.TAURUS] == 2 and corrected[Rashi.LIBRA] == 0  # Venus pair


def test_equal_values_one_occupied_is_not_evaluable() -> None:
    """A minimal, isolated reproduction of the conflict shape (not tied to
    the abstract illustration's other signs)."""
    trikona = {r: 0 for r in Rashi}
    trikona[Rashi.CAPRICORN] = trikona[Rashi.AQUARIUS] = 2
    occupancy = {Rashi.CAPRICORN: frozenset({Contributor.SUN})}
    occupancy_full = {r: occupancy.get(r, frozenset()) for r in Rashi}
    corrected, conflicts = apply_ekadhipatya_shodhana(
        trikona, occupancy_full, rahu_sign=None, ketu_sign=None
    )
    assert corrected is None
    assert len(conflicts) == 1
    assert conflicts[0].occupied_sign == Rashi.CAPRICORN
    assert conflicts[0].empty_sign == Rashi.AQUARIUS
    assert conflicts[0].shared_value == 2


def test_rule2_both_occupied_leaves_values_unchanged_even_if_equal() -> None:
    """Mars pair (Aries/Scorpio), both occupied, equal values: rule 2 takes
    precedence and is NOT reported as a conflict (only 'exactly one
    occupied, equal' is ambiguous in the source; 'both occupied' never is)."""
    trikona = dict(_ABSTRACT_TRIKONA)
    trikona[Rashi.CAPRICORN], trikona[Rashi.AQUARIUS] = 2, 5  # avoid the unrelated conflict
    trikona[Rashi.ARIES] = trikona[Rashi.SCORPIO] = 5
    occupancy = {sign: frozenset({Contributor.SUN}) for sign in (Rashi.ARIES, Rashi.SCORPIO)}
    occupancy_full = {r: occupancy.get(r, frozenset()) for r in Rashi}
    corrected, conflicts = apply_ekadhipatya_shodhana(
        trikona, occupancy_full, rahu_sign=None, ketu_sign=None
    )
    assert conflicts == ()
    assert corrected is not None
    assert corrected[Rashi.ARIES] == 5
    assert corrected[Rashi.SCORPIO] == 5


def test_ketu_alone_counts_as_occupied() -> None:
    """BPHS's own continued Sun-chart example (Ch. 68 p. 876): Sagittarius,
    occupied only by Ketu, is treated as 'with a planet'."""
    occupancy = occupancy_map({Contributor.SUN: 9})  # irrelevant sign, just needs a value
    assert not is_occupied(occupancy, Rashi.SAGITTARIUS, rahu_sign=None, ketu_sign=None)
    assert is_occupied(occupancy, Rashi.SAGITTARIUS, rahu_sign=None, ketu_sign=Rashi.SAGITTARIUS)


def test_lagna_alone_does_not_count_as_occupied() -> None:
    """No worked example isolates this; documented as an explicit inference
    (docs v1.8.0 AV-10): the Ascendant is a point, not a graha."""
    occupancy = occupancy_map({Contributor.LAGNA: 0})  # Lagna in Aries, nothing else
    assert classical_occupants(occupancy, Rashi.ARIES) == frozenset()
    assert not is_occupied(occupancy, Rashi.ARIES, rahu_sign=None, ketu_sign=None)


def test_single_lordship_signs_are_never_touched() -> None:
    """Sun (Leo) and Moon (Cancer) own one sign each and are not in
    LORDSHIP_PAIRS -- their Trikona value passes through unchanged. All
    five real lordship pairs are equal here too, but since neither sign in
    any pair is occupied, this is rule 1/5's unambiguous "both empty ->
    subtract the minimum" case, not the disputed "one occupied" case, so no
    conflict is reported."""
    trikona = {r: 7 for r in Rashi}
    corrected, conflicts = apply_ekadhipatya_shodhana(
        trikona, {r: frozenset() for r in Rashi}, rahu_sign=None, ketu_sign=None
    )
    assert conflicts == ()
    assert corrected is not None
    assert corrected[Rashi.LEO] == 7
    assert corrected[Rashi.CANCER] == 7


def test_occupancy_map_groups_contributors_by_sign() -> None:
    natal = natal_longitudes({"sun": 10.0, "moon": 40.0, "lagna": 10.0})
    signs = {c: int(lon // 30) for c, lon in natal.items()}
    occupancy = occupancy_map(signs)
    assert occupancy[Rashi.ARIES] == frozenset({Contributor.SUN, Contributor.LAGNA})
    assert occupancy[Rashi.TAURUS] == frozenset({Contributor.MOON})
    assert occupancy[Rashi.GEMINI] == frozenset()
