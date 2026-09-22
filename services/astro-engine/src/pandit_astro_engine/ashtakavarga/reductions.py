"""Trikona Shodhana and Ekadhipatya Shodhana (Phase 9 WP-A2), pure functions
over a chart's benefic-count-per-sign map.

Source: BPHS Ch. 67 "Trikona Shodhana" and Ch. 68 "Ekadhipatya Shodhana"
(printed pp. 867-877, IMAGE-TRANSLATION). Both operations are exact integer
arithmetic (subtraction and a minimum, never negative, never rounded).

The three resolved cases of `apply_ekadhipatya_shodhana` were consolidated
from BPHS's own six numbered verse-rules (Ch. 68 v. 1-5 and the prose rules
1-6): rule 2 (both occupied) is unchanged; rules 1 and 5 (neither occupied,
any relative size including equal) collapse into "subtract the minimum from
both"; rules 3 and 4 (exactly one occupied, unequal values) collapse into
one clamped subtraction.

A fourth case -- exactly one sign occupied, and the two Trikona-corrected
values equal -- is NOT resolved by this function. BPHS's own "abstract
illustration" (Ch. 68 p. 876) prints two different answers for this exact
shape: its Capricorn/Aquarius pair keeps the occupied sign unchanged
(matching rule 6's literal English, "the number of the *latter*
[without-planet sign] should be reduced to zero"), while its Gemini/Virgo
pair, under the identical shape, prints as if *both* signs were zeroed.
Rather than silently choosing either reading, this case is reported back to
the caller as an `EkadhipatyaConflict` per affected lordship pair; see
`apply_ekadhipatya_shodhana`'s return value and
`docs/ASTROLOGY_STANDARDS.md` v1.8.0 AV-10.
"""

from __future__ import annotations

from pandit_astro_engine.ashtakavarga.constants import LORDSHIP_PAIRS, TRIKONA_GROUPS, Contributor
from pandit_astro_engine.ashtakavarga.models import EkadhipatyaConflict
from pandit_astro_engine.rashi import RASHI_ORDER, Rashi


def apply_trikona_shodhana(benefic_count: dict[Rashi, int]) -> dict[Rashi, int]:
    """Ch. 67 v. 3-5: for each of the four trikona (trine) groups, subtract
    the minimum of the three signs' values from all three. Verified exactly
    against BPHS's own worked example (Ch. 67 p. 868-869) on all 12 signs."""
    result = dict(benefic_count)
    for group in TRIKONA_GROUPS:
        minimum = min(benefic_count[sign] for sign in group)
        for sign in group:
            result[sign] = benefic_count[sign] - minimum
    return result


def occupancy_map(natal_sign_index: dict[Contributor, int]) -> dict[Rashi, frozenset[Contributor]]:
    """Every contributor's (7 planets + Lagna) natal sign, grouped by sign.
    Rahu/Ketu are not `Contributor` members and are handled separately by
    the caller (see `is_occupied`)."""
    occupants: dict[Rashi, set[Contributor]] = {sign: set() for sign in RASHI_ORDER}
    for contributor, sign_index in natal_sign_index.items():
        occupants[RASHI_ORDER[sign_index]].add(contributor)
    return {sign: frozenset(members) for sign, members in occupants.items()}


def classical_occupants(
    occupancy: dict[Rashi, frozenset[Contributor]], sign: Rashi
) -> frozenset[Contributor]:
    """The classical (non-Lagna) planets occupying `sign` -- what Graha
    Pinda's multiplier lookup needs; the Ascendant itself is never a graha."""
    return frozenset(c for c in occupancy[sign] if c != Contributor.LAGNA)


def is_occupied(
    occupancy: dict[Rashi, frozenset[Contributor]],
    sign: Rashi,
    rahu_sign: Rashi | None,
    ketu_sign: Rashi | None,
) -> bool:
    """Whether `sign` counts as "with a planet" for Ekadhipatya Shodhana.
    Confirmed by the continued Sun-chart example (Ch. 68 p. 876): Sagittarius,
    occupied only by Ketu, is treated as occupied. The Ascendant alone
    (without any graha) is NOT treated as occupying a sign for this test --
    no worked example isolates this, so it is an explicit, documented
    inference, not a source statement (docs v1.8.0 AV-10 note)."""
    if classical_occupants(occupancy, sign):
        return True
    return sign == rahu_sign or sign == ketu_sign


def apply_ekadhipatya_shodhana(
    trikona_corrected: dict[Rashi, int],
    occupancy: dict[Rashi, frozenset[Contributor]],
    rahu_sign: Rashi | None,
    ketu_sign: Rashi | None,
) -> tuple[dict[Rashi, int] | None, tuple[EkadhipatyaConflict, ...]]:
    """Ch. 68 rules 1-6. Returns `(corrected, conflicts)`: if every lordship
    pair resolves unambiguously, `corrected` is the full 12-sign map and
    `conflicts` is empty. If any pair hits the unresolved equal-value/
    one-occupied case, `corrected` is `None` (the whole chart's Ekadhipatya
    result is withheld, never partially computed) and `conflicts` lists
    every such pair, each with both of BPHS's own printed readings kept
    verbatim (see module docstring and `EkadhipatyaConflict`).

    Sun's and Moon's single-lordship signs (Leo, Cancer) are never touched --
    they simply are not in `LORDSHIP_PAIRS` and pass through unchanged."""
    result = dict(trikona_corrected)
    conflicts: list[EkadhipatyaConflict] = []
    for sign_a, sign_b in LORDSHIP_PAIRS.values():
        value_a, value_b = trikona_corrected[sign_a], trikona_corrected[sign_b]
        occ_a = is_occupied(occupancy, sign_a, rahu_sign, ketu_sign)
        occ_b = is_occupied(occupancy, sign_b, rahu_sign, ketu_sign)
        if occ_a and occ_b:
            continue  # rule 2: no change, for any values, even equal
        if not occ_a and not occ_b:
            minimum = min(value_a, value_b)  # rules 1 and 5, unified
            result[sign_a] = value_a - minimum
            result[sign_b] = value_b - minimum
            continue
        occupied_sign, empty_sign = (sign_a, sign_b) if occ_a else (sign_b, sign_a)
        occupied_value, empty_value = (value_a, value_b) if occ_a else (value_b, value_a)
        if occupied_value == empty_value:
            # Unresolved: BPHS's own table disagrees with itself on this
            # exact shape (see module docstring). Not guessed.
            conflicts.append(
                EkadhipatyaConflict(
                    occupied_sign=occupied_sign,
                    empty_sign=empty_sign,
                    shared_value=occupied_value,
                    reading_a_occupied_value=occupied_value,
                    reading_b_occupied_value=0,
                )
            )
            continue
        if occ_a:  # exactly one occupied, unequal -- rules 3 and 4, unified
            result[sign_a] = value_a
            result[sign_b] = max(0, value_b - value_a)
        else:
            result[sign_b] = value_b
            result[sign_a] = max(0, value_a - value_b)
    if conflicts:
        return None, tuple(conflicts)
    return result, ()
