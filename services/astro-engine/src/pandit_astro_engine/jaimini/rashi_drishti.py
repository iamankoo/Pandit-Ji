"""Rashi Drishti (Phase 9 WP-B-1) -- BPHS Ch. 8 v. 1-3: a static,
longitude-independent sign-to-sign aspect table, kept entirely separate from
Phase 5/6's Vedic graha drishti (planet-to-house aspect, `aspects.py`). See
`profiles.py` for the source citation and the deliberate v. 4-5 exclusion.

The rule, in the source's own words: every movable sign aspects the 3 fixed
signs other than the fixed sign adjacent to it; every fixed sign aspects the
3 movable signs other than the movable sign adjacent to it; every common
(dual) sign aspects the other 3 common signs.

This is derived here from the already-locked Phase 5 `RASHI_MODALITY`
table (`rashi.py`) rather than transcribed sign by sign, so it can never
silently drift from the Chara/Sthira/Dwiswabhava classification the rest of
the engine already uses. `test_rashi_drishti.py` proves the derivation
reproduces BPHS's own printed 12-sign table exactly, cell by cell.
"""

from __future__ import annotations

from pandit_astro_engine.rashi import RASHI_MODALITY, Modality, Rashi, rashi_from_index, rashi_index

#: The two modalities that aspect each other (excluding the adjacent sign),
#: as opposed to Modality.DUAL, which aspects within its own group.
_OPPOSITE_MODALITY: dict[Modality, Modality] = {
    Modality.MOVABLE: Modality.FIXED,
    Modality.FIXED: Modality.MOVABLE,
}


def rashi_drishti(rashi: Rashi) -> tuple[Rashi, ...]:
    """The (always exactly 3) signs that `rashi` casts a Rasi Drishti on,
    in zodiacal order. Deterministic and longitude-independent: the same
    input always produces the same output."""
    modality = RASHI_MODALITY[rashi]
    if modality is Modality.DUAL:
        targets = [r for r in Rashi if RASHI_MODALITY[r] is Modality.DUAL and r != rashi]
    else:
        opposite = _OPPOSITE_MODALITY[modality]
        index = rashi_index(rashi)
        adjacent = {rashi_from_index(index - 1), rashi_from_index(index + 1)}
        targets = [r for r in Rashi if RASHI_MODALITY[r] is opposite and r not in adjacent]
    return tuple(sorted(targets, key=rashi_index))


def has_rashi_drishti(source: Rashi, target: Rashi) -> bool:
    """Whether `source` casts a Rasi Drishti on `target`. The relation is
    always mutual (proven by `test_rashi_drishti.py`): this is equivalent to
    `has_rashi_drishti(target, source)`."""
    return target in rashi_drishti(source)
