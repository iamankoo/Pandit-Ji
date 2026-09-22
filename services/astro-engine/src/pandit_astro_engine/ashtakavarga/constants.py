"""Ashtakavarga source tables (Phase 9 WP-A1; `docs/ASTROLOGY_STANDARDS.md`
v1.7.0, AV-01 to AV-08).

Every table here is one printed source's own statement, transcribed from a
page image, never merged with another source and never "corrected" toward
another source's reading. Four independent tables exist because two
independent books (Brihat Jataka, Phaladeepika) and two internally
differing representations of a third (BPHS's own printed dot grid and its
own printed verse-translation list, which disagree with each other on 5 of
56 cells inside the same chapter) were each read from page images. See
`CROSS_TABLE_CONFLICTS` for the complete, reconciled disagreement register
(9 of 56 cells; every profile still returns its own printed value at every
one of them -- no winner is chosen anywhere in this module).

Terminology trap, deliberately not used as a field name anywhere in this
package: BPHS's own text (Ch. 66, printed pp. 845-854, 864-865) calls the
*inauspicious* houses "Karanaprada" (dot-marked) and the *auspicious* ones
"Rekhaprada" (line-marked) -- the opposite of the popular modern shorthand
"bindu = benefic point". This module always stores and reports the
houses each contributor considers BENEFIC directly (the sense Brihat
Jataka and Phaladeepika state outright, and BPHS's dot lists after taking
the complement), and calls the derived per-sign count `benefic_count`,
never "bindu count", so no reader can misapply BPHS's own inverted
vocabulary to the other two sources.
"""

from __future__ import annotations

from enum import Enum

from pandit_astro_engine.rashi import Rashi

SYSTEM_ID = "ashtakavarga"

#: Standards version this module implements (Phase 9 WP-A1 methodology lock,
#: extended by the WP-A2/A3 reductions and Pinda lock).
ASHTAKAVARGA_STANDARDS_VERSION = "1.8.0"


class Contributor(str, Enum):
    """The eight contributors to every Bhinnashtakavarga chart: the seven
    classical planets and the Ascendant. Rahu and Ketu are never
    contributors -- no source read (Brihat Jataka Ch. IX, Phaladeepika
    Ch. XXIII, BPHS Ch. 66) gives either node a table."""

    SUN = "sun"
    MOON = "moon"
    MARS = "mars"
    MERCURY = "mercury"
    JUPITER = "jupiter"
    VENUS = "venus"
    SATURN = "saturn"
    LAGNA = "lagna"


#: Classical ordering, Sun first through the Ascendant last -- matches every
#: source's own presentation order and is used wherever a stable iteration
#: order is needed (evidence, serialization).
CONTRIBUTOR_ORDER: tuple[Contributor, ...] = (
    Contributor.SUN,
    Contributor.MOON,
    Contributor.MARS,
    Contributor.MERCURY,
    Contributor.JUPITER,
    Contributor.VENUS,
    Contributor.SATURN,
    Contributor.LAGNA,
)

#: The seven Bhinnashtakavarga planet charts. Brihat Jataka and Phaladeepika
#: give only these seven; BPHS additionally gives its own eighth chart for
#: the Ascendant (`LAGNA_CHART_BPHS` below), profile-dependent, never
#: synthesized for the other two sources.
PLANET_CHARTS: tuple[Contributor, ...] = CONTRIBUTOR_ORDER[:7]

#: Each source's own stated per-chart benefic total (invariant: 337 grand
#: total for Brihat Jataka, Phaladeepika and the BPHS dot grid; the BPHS
#: verse-translation list sums to 340 because of its own three internal
#: anomalies -- see `CROSS_TABLE_CONFLICTS`). Recorded here as an
#: independent check value, not derived from the tables below.
CHART_TOTAL_INVARIANT: dict[Contributor, int] = {
    Contributor.SUN: 48,
    Contributor.MOON: 49,
    Contributor.MARS: 39,
    Contributor.MERCURY: 54,
    Contributor.JUPITER: 56,
    Contributor.VENUS: 52,
    Contributor.SATURN: 39,
}
GRAND_TOTAL_INVARIANT = 337

# --------------------------------------------------------------------------
# Source tables: chart -> contributor -> the houses (1..12, counted from the
# contributor's own natal sign) that contributor considers benefic.
# --------------------------------------------------------------------------

#: Brihat Jataka (Varahamihira, Sastri translation) Ch. IX sl. 1-7, all 56
#: cells IMAGE-TRANSLATION verified on the printed pages (pp. 198-202).
BJ_TABLE: dict[Contributor, dict[Contributor, tuple[int, ...]]] = {
    Contributor.SUN: {
        Contributor.SUN: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.MOON: (3, 6, 10, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.MERCURY: (3, 5, 6, 9, 10, 11, 12),
        Contributor.JUPITER: (5, 6, 9, 11),
        Contributor.VENUS: (6, 7, 12),
        Contributor.SATURN: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.LAGNA: (3, 4, 6, 10, 11, 12),
    },
    Contributor.MOON: {
        Contributor.SUN: (3, 6, 7, 8, 10, 11),
        Contributor.MOON: (1, 3, 5, 7, 10, 11),
        Contributor.MARS: (2, 3, 5, 6, 9, 10, 11),
        Contributor.MERCURY: (1, 3, 4, 5, 7, 8, 10, 11),
        Contributor.JUPITER: (1, 4, 7, 8, 10, 11, 12),
        Contributor.VENUS: (3, 4, 5, 7, 9, 10, 11),
        Contributor.SATURN: (3, 5, 6, 11),
        Contributor.LAGNA: (3, 6, 10, 11),
    },
    Contributor.MARS: {
        Contributor.SUN: (3, 5, 6, 10, 11),
        Contributor.MOON: (3, 6, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 10, 11),
        Contributor.MERCURY: (3, 5, 6, 11),
        Contributor.JUPITER: (6, 10, 11, 12),
        Contributor.VENUS: (6, 8, 11, 12),
        Contributor.SATURN: (1, 4, 7, 8, 9, 10, 11),
        Contributor.LAGNA: (1, 3, 6, 10, 11),
    },
    Contributor.MERCURY: {
        Contributor.SUN: (5, 6, 9, 11, 12),
        Contributor.MOON: (2, 4, 6, 8, 10, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.MERCURY: (1, 3, 5, 6, 9, 10, 11, 12),
        Contributor.JUPITER: (6, 8, 11, 12),
        Contributor.VENUS: (1, 2, 3, 4, 5, 8, 9, 11),
        Contributor.SATURN: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.LAGNA: (1, 2, 4, 6, 8, 10, 11),
    },
    Contributor.JUPITER: {
        Contributor.SUN: (1, 2, 3, 4, 7, 8, 9, 10, 11),
        Contributor.MOON: (2, 5, 7, 9, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 10, 11),
        Contributor.MERCURY: (1, 2, 4, 5, 6, 9, 10, 11),
        Contributor.JUPITER: (1, 2, 3, 4, 7, 8, 10, 11),
        Contributor.VENUS: (2, 5, 6, 9, 10, 11),
        Contributor.SATURN: (3, 5, 6, 12),
        Contributor.LAGNA: (1, 2, 4, 5, 6, 7, 9, 10, 11),
    },
    Contributor.VENUS: {
        Contributor.SUN: (8, 11, 12),
        Contributor.MOON: (1, 2, 3, 4, 5, 8, 9, 11, 12),
        Contributor.MARS: (3, 5, 6, 9, 11, 12),
        Contributor.MERCURY: (3, 5, 6, 9, 11),
        Contributor.JUPITER: (5, 8, 9, 10, 11),
        Contributor.VENUS: (1, 2, 3, 4, 5, 8, 9, 10, 11),
        Contributor.SATURN: (3, 4, 5, 8, 9, 10, 11),
        Contributor.LAGNA: (1, 2, 3, 4, 5, 8, 9, 11),
    },
    Contributor.SATURN: {
        Contributor.SUN: (1, 2, 4, 7, 8, 10, 11),
        Contributor.MOON: (3, 6, 11),
        Contributor.MARS: (3, 5, 6, 10, 11, 12),
        Contributor.MERCURY: (6, 8, 9, 10, 11, 12),
        Contributor.JUPITER: (5, 6, 11, 12),
        Contributor.VENUS: (6, 11, 12),
        Contributor.SATURN: (3, 5, 6, 11),
        Contributor.LAGNA: (1, 3, 4, 6, 10, 11),
    },
}

#: Brihat Jataka Ch. IX sl. 3 (page-verified, p. 199): "the 10th place from
#: the Moon is effectless, i.e. neither benefic nor malefic" for Mars's
#: chart. No other source read states an effectless cell anywhere, so this
#: applies only under the Brihat Jataka profile.
BJ_EFFECTLESS_CELLS: dict[tuple[Contributor, Contributor], tuple[int, ...]] = {
    (Contributor.MARS, Contributor.MOON): (10,),
}

#: Phaladeepika (Mantreswara, Sastri translation) Ch. XXIII sl. 3-9, all 56
#: cells IMAGE-TRANSLATION verified on the printed pages (pp. 258-261).
#: Two cells (Moon chart/Jupiter, Venus chart/Mars) carry a translator
#: footnote naming an alternate reading by another named author; the
#: footnote is kept as a `translator_note` and never merged into this table
#: (see `CROSS_TABLE_CONFLICTS`).
PHALADEEPIKA_TABLE: dict[Contributor, dict[Contributor, tuple[int, ...]]] = {
    Contributor.SUN: {
        Contributor.SUN: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.MOON: (3, 6, 10, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.MERCURY: (3, 5, 6, 9, 10, 11, 12),
        Contributor.JUPITER: (5, 6, 9, 11),
        Contributor.VENUS: (6, 7, 12),
        Contributor.SATURN: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.LAGNA: (3, 4, 6, 10, 11, 12),
    },
    Contributor.MOON: {
        Contributor.SUN: (3, 6, 7, 8, 10, 11),
        Contributor.MOON: (1, 3, 6, 7, 10, 11),
        Contributor.MARS: (2, 3, 5, 6, 9, 10, 11),
        Contributor.MERCURY: (1, 3, 4, 5, 7, 8, 10, 11),
        Contributor.JUPITER: (1, 2, 4, 7, 8, 10, 11),
        Contributor.VENUS: (3, 4, 5, 7, 9, 10, 11),
        Contributor.SATURN: (3, 5, 6, 11),
        Contributor.LAGNA: (3, 6, 10, 11),
    },
    Contributor.MARS: {
        Contributor.SUN: (3, 5, 6, 10, 11),
        Contributor.MOON: (3, 6, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 10, 11),
        Contributor.MERCURY: (3, 5, 6, 11),
        Contributor.JUPITER: (6, 10, 11, 12),
        Contributor.VENUS: (6, 8, 11, 12),
        Contributor.SATURN: (1, 4, 7, 8, 9, 10, 11),
        Contributor.LAGNA: (1, 3, 6, 10, 11),
    },
    Contributor.MERCURY: {
        Contributor.SUN: (5, 6, 9, 11, 12),
        Contributor.MOON: (2, 4, 6, 8, 10, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.MERCURY: (1, 3, 5, 6, 9, 10, 11, 12),
        Contributor.JUPITER: (6, 8, 11, 12),
        Contributor.VENUS: (1, 2, 3, 4, 5, 8, 9, 11),
        Contributor.SATURN: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.LAGNA: (1, 2, 4, 6, 8, 10, 11),
    },
    Contributor.JUPITER: {
        Contributor.SUN: (1, 2, 3, 4, 7, 8, 9, 10, 11),
        Contributor.MOON: (2, 5, 7, 9, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 10, 11),
        Contributor.MERCURY: (1, 2, 4, 5, 6, 9, 10, 11),
        Contributor.JUPITER: (1, 2, 3, 4, 7, 8, 10, 11),
        Contributor.VENUS: (2, 5, 6, 9, 10, 11),
        Contributor.SATURN: (3, 5, 6, 12),
        Contributor.LAGNA: (1, 2, 4, 5, 6, 7, 9, 10, 11),
    },
    Contributor.VENUS: {
        Contributor.SUN: (8, 11, 12),
        Contributor.MOON: (1, 2, 3, 4, 5, 8, 9, 11, 12),
        Contributor.MARS: (3, 5, 6, 9, 11, 12),
        Contributor.MERCURY: (3, 5, 6, 9, 11),
        Contributor.JUPITER: (5, 8, 9, 10, 11),
        Contributor.VENUS: (1, 2, 3, 4, 5, 8, 9, 10, 11),
        Contributor.SATURN: (3, 4, 5, 8, 9, 10, 11),
        Contributor.LAGNA: (1, 2, 3, 4, 5, 8, 9, 11),
    },
    Contributor.SATURN: {
        Contributor.SUN: (1, 2, 4, 7, 8, 10, 11),
        Contributor.MOON: (3, 6, 11),
        Contributor.MARS: (3, 5, 6, 10, 11, 12),
        Contributor.MERCURY: (6, 8, 9, 10, 11, 12),
        Contributor.JUPITER: (5, 6, 11, 12),
        Contributor.VENUS: (6, 11, 12),
        Contributor.SATURN: (3, 5, 6, 11),
        Contributor.LAGNA: (1, 3, 4, 6, 10, 11),
    },
}

#: BPHS (Vol II Ch. 66, Kapoor translation) printed **dot grid**
#: ("Chart showing dots in ... Ashtakavarga"), complemented to benefic
#: houses (the source's own note: "the houses without dots are considered
#: auspicious"). All seven planet charts and the Ascendant's own chart
#: IMAGE-TRANSLATION verified (pp. 845-854, 864-865). Disagrees with the
#: printed verse-translation list (`BPHS_VERSE_TABLE`) on 5 of 56 cells.
BPHS_GRID_TABLE: dict[Contributor, dict[Contributor, tuple[int, ...]]] = {
    Contributor.SUN: {
        Contributor.SUN: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.MOON: (3, 6, 10, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.MERCURY: (3, 5, 6, 9, 10, 11, 12),
        Contributor.JUPITER: (5, 6, 9, 11),
        Contributor.VENUS: (6, 7, 12),
        Contributor.SATURN: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.LAGNA: (3, 4, 6, 10, 11, 12),
    },
    Contributor.MOON: {
        Contributor.SUN: (3, 6, 7, 8, 10, 11),
        Contributor.MOON: (1, 3, 6, 7, 9, 10, 11),
        Contributor.MARS: (2, 3, 5, 6, 10, 11),
        Contributor.MERCURY: (1, 3, 4, 5, 7, 8, 10, 11),
        Contributor.JUPITER: (1, 2, 4, 7, 8, 10, 11),
        Contributor.VENUS: (3, 4, 5, 7, 9, 10, 11),
        Contributor.SATURN: (3, 5, 6, 11),
        Contributor.LAGNA: (3, 6, 10, 11),
    },
    Contributor.MARS: {
        Contributor.SUN: (3, 5, 6, 10, 11),
        Contributor.MOON: (3, 6, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 10, 11),
        Contributor.MERCURY: (3, 5, 6, 11),
        Contributor.JUPITER: (6, 10, 11, 12),
        Contributor.VENUS: (6, 8, 11, 12),
        Contributor.SATURN: (1, 4, 7, 8, 9, 10, 11),
        Contributor.LAGNA: (1, 3, 6, 10, 11),
    },
    Contributor.MERCURY: {
        Contributor.SUN: (5, 6, 9, 11, 12),
        Contributor.MOON: (2, 4, 6, 8, 10, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.MERCURY: (1, 3, 5, 6, 9, 10, 11, 12),
        Contributor.JUPITER: (6, 8, 11, 12),
        Contributor.VENUS: (1, 2, 3, 4, 5, 8, 9, 11),
        Contributor.SATURN: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.LAGNA: (1, 2, 4, 6, 8, 10, 11),
    },
    Contributor.JUPITER: {
        Contributor.SUN: (1, 2, 3, 4, 7, 8, 9, 10, 11),
        Contributor.MOON: (2, 5, 7, 9, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 10, 11),
        Contributor.MERCURY: (1, 2, 4, 5, 6, 9, 10, 11),
        Contributor.JUPITER: (1, 2, 3, 4, 7, 8, 10, 11),
        Contributor.VENUS: (2, 5, 6, 9, 10, 11),
        Contributor.SATURN: (3, 5, 6, 12),
        Contributor.LAGNA: (1, 2, 4, 5, 6, 7, 9, 10, 11),
    },
    Contributor.VENUS: {
        Contributor.SUN: (8, 11, 12),
        Contributor.MOON: (1, 2, 3, 4, 5, 9, 11, 12),
        Contributor.MARS: (3, 4, 6, 9, 11, 12),
        Contributor.MERCURY: (3, 5, 6, 8, 9, 11),
        Contributor.JUPITER: (5, 8, 9, 10, 11),
        Contributor.VENUS: (1, 2, 3, 4, 5, 8, 9, 10, 11),
        Contributor.SATURN: (3, 4, 5, 8, 9, 10, 11),
        Contributor.LAGNA: (1, 2, 3, 4, 5, 8, 9, 11),
    },
    Contributor.SATURN: {
        Contributor.SUN: (1, 2, 4, 7, 8, 10, 11),
        Contributor.MOON: (3, 6, 11),
        Contributor.MARS: (3, 5, 6, 10, 11, 12),
        Contributor.MERCURY: (6, 8, 9, 10, 11, 12),
        Contributor.JUPITER: (5, 6, 11, 12),
        Contributor.VENUS: (6, 11, 12),
        Contributor.SATURN: (3, 5, 6, 11),
        Contributor.LAGNA: (1, 3, 4, 6, 10, 11),
    },
}

#: BPHS printed **verse-translation list** ("Thus [contributors], these N in
#: the Kth ..."), complemented to benefic houses. Same page range as
#: `BPHS_GRID_TABLE`. Kept as its own profile rather than folded into the
#: grid because the two disagree on 5 of 56 cells inside the same printed
#: chapter and there is no basis, without Sanskrit review, to prefer one
#: printed representation over the other.
BPHS_VERSE_TABLE: dict[Contributor, dict[Contributor, tuple[int, ...]]] = {
    Contributor.SUN: {
        Contributor.SUN: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.MOON: (3, 6, 10, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.MERCURY: (3, 5, 6, 9, 10, 11, 12),
        Contributor.JUPITER: (5, 6, 9, 11),
        Contributor.VENUS: (6, 7, 12),
        Contributor.SATURN: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.LAGNA: (3, 4, 6, 10, 11, 12),
    },
    Contributor.MOON: {
        Contributor.SUN: (3, 6, 7, 8, 10, 11),
        Contributor.MOON: (1, 3, 6, 7, 9, 10, 11),
        Contributor.MARS: (2, 3, 5, 6, 10, 11),
        Contributor.MERCURY: (1, 3, 4, 5, 7, 8, 10, 11),
        Contributor.JUPITER: (1, 2, 4, 7, 8, 10, 11),
        Contributor.VENUS: (3, 4, 5, 7, 9, 10, 11),
        Contributor.SATURN: (3, 5, 6, 11),
        Contributor.LAGNA: (3, 6, 10, 11),
    },
    Contributor.MARS: {
        Contributor.SUN: (3, 5, 6, 10, 11),
        Contributor.MOON: (3, 6, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 10, 11),
        Contributor.MERCURY: (3, 5, 6, 11),
        Contributor.JUPITER: (6, 10, 11, 12),
        Contributor.VENUS: (2, 6, 8, 11, 12),
        Contributor.SATURN: (1, 4, 5, 7, 8, 9, 10, 11),
        Contributor.LAGNA: (1, 3, 6, 10, 11),
    },
    Contributor.MERCURY: {
        Contributor.SUN: (5, 6, 9, 11, 12),
        Contributor.MOON: (2, 4, 6, 8, 10, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.MERCURY: (1, 3, 5, 6, 9, 10, 11, 12),
        Contributor.JUPITER: (6, 8, 11, 12),
        Contributor.VENUS: (1, 2, 3, 4, 5, 8, 9, 11),
        Contributor.SATURN: (1, 2, 4, 7, 8, 9, 10, 11),
        Contributor.LAGNA: (1, 2, 4, 6, 8, 10, 11),
    },
    Contributor.JUPITER: {
        Contributor.SUN: (1, 2, 3, 4, 7, 8, 9, 10, 11),
        Contributor.MOON: (2, 5, 7, 9, 11),
        Contributor.MARS: (1, 2, 4, 7, 8, 10, 11),
        Contributor.MERCURY: (1, 2, 4, 5, 6, 9, 10, 11),
        Contributor.JUPITER: (1, 2, 3, 4, 7, 8, 10, 11),
        Contributor.VENUS: (2, 5, 6, 9, 10, 11),
        Contributor.SATURN: (3, 5, 6, 12),
        Contributor.LAGNA: (1, 2, 4, 5, 6, 7, 9, 10, 11),
    },
    Contributor.VENUS: {
        Contributor.SUN: (8, 9, 11, 12),
        Contributor.MOON: (1, 2, 3, 4, 5, 8, 9, 11, 12),
        Contributor.MARS: (3, 4, 6, 9, 11, 12),
        Contributor.MERCURY: (3, 5, 6, 9, 11),
        Contributor.JUPITER: (5, 8, 9, 10, 11),
        Contributor.VENUS: (1, 2, 3, 4, 5, 8, 9, 10, 11),
        Contributor.SATURN: (3, 4, 5, 8, 9, 10, 11),
        Contributor.LAGNA: (1, 2, 3, 4, 5, 8, 9, 11),
    },
    Contributor.SATURN: {
        Contributor.SUN: (1, 2, 4, 7, 8, 10, 11),
        Contributor.MOON: (3, 6, 11),
        Contributor.MARS: (3, 5, 6, 10, 11, 12),
        Contributor.MERCURY: (6, 8, 9, 10, 11, 12),
        Contributor.JUPITER: (5, 6, 11, 12),
        Contributor.VENUS: (6, 11, 12),
        Contributor.SATURN: (3, 5, 6, 11),
        Contributor.LAGNA: (1, 3, 4, 6, 10, 11),
    },
}

#: BPHS Ch. 66 v. 65-68's own eighth chart, for the Ascendant itself
#: (IMAGE-TRANSLATION verified, pp. 864-865; grid and verse-translation list
#: agree here, 49 benefic houses total). Neither Brihat Jataka nor
#: Phaladeepika gives the Ascendant its own chart -- both are silent, not
#: excluding it -- so this table is used only under the two BPHS profiles
#: and is never synthesized for the other two.
LAGNA_CHART_BPHS: dict[Contributor, tuple[int, ...]] = {
    Contributor.SUN: (3, 4, 6, 10, 11, 12),
    Contributor.MOON: (3, 6, 10, 11, 12),
    Contributor.MARS: (1, 3, 6, 10, 11),
    Contributor.MERCURY: (1, 2, 4, 6, 8, 10, 11),
    Contributor.JUPITER: (1, 2, 4, 5, 6, 7, 9, 10, 11),
    Contributor.VENUS: (1, 2, 3, 4, 5, 8, 9),
    Contributor.SATURN: (1, 3, 4, 6, 10, 11),
    Contributor.LAGNA: (3, 6, 10, 11),
}
LAGNA_CHART_TOTAL_INVARIANT = 49


class ConflictClassification(str, Enum):
    """How a disagreement among the four readings arises -- see the
    Phase 9 Gate 1 reconciliation report for the full derivation."""

    #: Brihat Jataka and Phaladeepika disagree with each other; BPHS's own
    #: grid and verse-translation list agree with each other and side with
    #: one of the two (or with neither).
    CROSS_SOURCE_VARIANT = "cross_source_variant"
    #: Brihat Jataka and Phaladeepika agree with each other; BPHS's own grid
    #: and verse-translation list agree with each other but differ from both.
    BPHS_INTERNALLY_CONSISTENT_VARIANT = "bphs_internally_consistent_variant"
    #: Brihat Jataka, Phaladeepika and BPHS's own verse-translation list all
    #: agree; only BPHS's printed dot grid differs.
    BPHS_GRID_ONLY_ANOMALY = "bphs_grid_only_anomaly"
    #: Brihat Jataka, Phaladeepika and BPHS's own printed dot grid all
    #: agree; only BPHS's printed verse-translation list differs.
    BPHS_VERSE_ONLY_ANOMALY = "bphs_verse_only_anomaly"


class CrossTableConflict:
    """One of the 9 (of 56) cells where the four readings do not all agree.
    `houses` gives each reading's own benefic-house set exactly as printed;
    nothing here picks a winner. `translator_note` records a named
    attribution a translator's footnote gives for the non-default reading,
    when one exists -- itself only a `translator_note`-level statement,
    never a resolution."""

    __slots__ = ("chart", "contributor", "classification", "houses", "translator_note")

    def __init__(
        self,
        chart: Contributor,
        contributor: Contributor,
        classification: ConflictClassification,
        houses: dict[str, tuple[int, ...]],
        translator_note: str | None = None,
    ) -> None:
        self.chart = chart
        self.contributor = contributor
        self.classification = classification
        self.houses = houses
        self.translator_note = translator_note


#: The complete, reconciled 9-cell disagreement register (Phase 9 Gate 1
#: reconciliation audit). `houses` keys are "brihat_jataka",
#: "phaladeepika", "bphs_grid", "bphs_verse". Every value is copied
#: verbatim from the tables above; this register exists for evidence and
#: cross-profile documentation only and is never consulted by the
#: calculator (each profile already uses its own table unconditionally).
CROSS_TABLE_CONFLICTS: tuple[CrossTableConflict, ...] = (
    CrossTableConflict(
        Contributor.MOON,
        Contributor.JUPITER,
        ConflictClassification.CROSS_SOURCE_VARIANT,
        {
            "brihat_jataka": (1, 4, 7, 8, 10, 11, 12),
            "phaladeepika": (1, 2, 4, 7, 8, 10, 11),
            "bphs_grid": (1, 2, 4, 7, 8, 10, 11),
            "bphs_verse": (1, 2, 4, 7, 8, 10, 11),
        },
        translator_note=(
            "Phaladeepika Ch. XXIII sl. 4 footnote (printed p. 258): 'According to "
            "Varahamihira, 1st, 4th, 7th, 8th, 10th, 11th and 12th places from Jupiter' -- "
            "attributes the Brihat-Jataka reading to Varahamihira by name; not independently "
            "checked against a Varahamihira text"
        ),
    ),
    CrossTableConflict(
        Contributor.MOON,
        Contributor.MOON,
        ConflictClassification.CROSS_SOURCE_VARIANT,
        {
            "brihat_jataka": (1, 3, 5, 7, 10, 11),
            "phaladeepika": (1, 3, 6, 7, 10, 11),
            "bphs_grid": (1, 3, 6, 7, 9, 10, 11),
            "bphs_verse": (1, 3, 6, 7, 9, 10, 11),
        },
    ),
    CrossTableConflict(
        Contributor.MOON,
        Contributor.MARS,
        ConflictClassification.BPHS_INTERNALLY_CONSISTENT_VARIANT,
        {
            "brihat_jataka": (2, 3, 5, 6, 9, 10, 11),
            "phaladeepika": (2, 3, 5, 6, 9, 10, 11),
            "bphs_grid": (2, 3, 5, 6, 10, 11),
            "bphs_verse": (2, 3, 5, 6, 10, 11),
        },
    ),
    CrossTableConflict(
        Contributor.VENUS,
        Contributor.MARS,
        ConflictClassification.BPHS_INTERNALLY_CONSISTENT_VARIANT,
        {
            "brihat_jataka": (3, 5, 6, 9, 11, 12),
            "phaladeepika": (3, 5, 6, 9, 11, 12),
            "bphs_grid": (3, 4, 6, 9, 11, 12),
            "bphs_verse": (3, 4, 6, 9, 11, 12),
        },
        translator_note=(
            "Phaladeepika Ch. XXIII sl. 8 footnote (printed p. 260): 'According to Parasara, "
            "the 3rd, 4th, 6th, 9th, 11th and 12th places from Mars' -- attributes the "
            "BPHS-side reading to Parasara by name; not independently checked"
        ),
    ),
    CrossTableConflict(
        Contributor.VENUS,
        Contributor.MOON,
        ConflictClassification.BPHS_GRID_ONLY_ANOMALY,
        {
            "brihat_jataka": (1, 2, 3, 4, 5, 8, 9, 11, 12),
            "phaladeepika": (1, 2, 3, 4, 5, 8, 9, 11, 12),
            "bphs_grid": (1, 2, 3, 4, 5, 9, 11, 12),
            "bphs_verse": (1, 2, 3, 4, 5, 8, 9, 11, 12),
        },
    ),
    CrossTableConflict(
        Contributor.VENUS,
        Contributor.MERCURY,
        ConflictClassification.BPHS_GRID_ONLY_ANOMALY,
        {
            "brihat_jataka": (3, 5, 6, 9, 11),
            "phaladeepika": (3, 5, 6, 9, 11),
            "bphs_grid": (3, 5, 6, 8, 9, 11),
            "bphs_verse": (3, 5, 6, 9, 11),
        },
    ),
    CrossTableConflict(
        Contributor.MARS,
        Contributor.SATURN,
        ConflictClassification.BPHS_VERSE_ONLY_ANOMALY,
        {
            "brihat_jataka": (1, 4, 7, 8, 9, 10, 11),
            "phaladeepika": (1, 4, 7, 8, 9, 10, 11),
            "bphs_grid": (1, 4, 7, 8, 9, 10, 11),
            "bphs_verse": (1, 4, 5, 7, 8, 9, 10, 11),
        },
    ),
    CrossTableConflict(
        Contributor.MARS,
        Contributor.VENUS,
        ConflictClassification.BPHS_VERSE_ONLY_ANOMALY,
        {
            "brihat_jataka": (6, 8, 11, 12),
            "phaladeepika": (6, 8, 11, 12),
            "bphs_grid": (6, 8, 11, 12),
            "bphs_verse": (2, 6, 8, 11, 12),
        },
    ),
    CrossTableConflict(
        Contributor.VENUS,
        Contributor.SUN,
        ConflictClassification.BPHS_VERSE_ONLY_ANOMALY,
        {
            "brihat_jataka": (8, 11, 12),
            "phaladeepika": (8, 11, 12),
            "bphs_grid": (8, 11, 12),
            "bphs_verse": (8, 9, 11, 12),
        },
    ),
)


# ==========================================================================
# WP-A2 / WP-A3 -- Trikona Shodhana, Ekadhipatya Shodhana, Pinda Sadhana
# (docs/ASTROLOGY_STANDARDS.md v1.8.0, AV-09 to AV-13)
#
# Source: BPHS Vol II (Kapoor), Ch. 67 "Trikona Shodhana", Ch. 68
# "Ekadhipatya Shodhana", Ch. 69 "Pinda Sadhana" (printed pp. 867-880),
# IMAGE-TRANSLATION. Brihat Jataka and Phaladeepika give no reduction
# procedure at all -- this whole section applies only under the two BPHS
# profiles (`BPHS_GRID_ID`, `BPHS_VERSE_ID`); it is never applied to, or
# silently combined with, the Brihat Jataka or Phaladeepika tables.
# ==========================================================================

#: Ch. 67 v. 1-2: the four trikona (trine) groups, equidistant sign triads.
TRIKONA_GROUPS: tuple[tuple[Rashi, Rashi, Rashi], ...] = (
    (Rashi.ARIES, Rashi.LEO, Rashi.SAGITTARIUS),
    (Rashi.TAURUS, Rashi.VIRGO, Rashi.CAPRICORN),
    (Rashi.GEMINI, Rashi.LIBRA, Rashi.AQUARIUS),
    (Rashi.CANCER, Rashi.SCORPIO, Rashi.PISCES),
)

#: Ch. 68: the five planets that own two signs each, and their pair. Sun and
#: Moon (one sign each) are handled separately -- see `SINGLE_LORDSHIP_SIGN`.
LORDSHIP_PAIRS: dict[Contributor, tuple[Rashi, Rashi]] = {
    Contributor.MARS: (Rashi.ARIES, Rashi.SCORPIO),
    Contributor.VENUS: (Rashi.TAURUS, Rashi.LIBRA),
    Contributor.MERCURY: (Rashi.GEMINI, Rashi.VIRGO),
    Contributor.JUPITER: (Rashi.SAGITTARIUS, Rashi.PISCES),
    Contributor.SATURN: (Rashi.CAPRICORN, Rashi.AQUARIUS),
}

#: Ch. 68 rule 6's closing sentence: Sun and Moon own one sign only and their
#: Ekadhipatya-corrected number is always the unreduced Trikona value.
SINGLE_LORDSHIP_SIGN: dict[Contributor, Rashi] = {
    Contributor.SUN: Rashi.LEO,
    Contributor.MOON: Rashi.CANCER,
}

#: Ch. 69 "Rasimana Chakra" -- IMAGE-TRANSLATION verified, verse and printed
#: table agree exactly, no conflict. Used by both Rasi Pinda and (as the
#: per-sign multiplicand) nowhere else.
RASI_MULTIPLIER: dict[Rashi, int] = {
    Rashi.ARIES: 7,
    Rashi.TAURUS: 10,
    Rashi.GEMINI: 8,
    Rashi.CANCER: 4,
    Rashi.LEO: 10,
    Rashi.VIRGO: 6,
    Rashi.LIBRA: 7,
    Rashi.SCORPIO: 8,
    Rashi.SAGITTARIUS: 9,
    Rashi.CAPRICORN: 5,
    Rashi.AQUARIUS: 11,
    Rashi.PISCES: 12,
}

#: Ch. 69 "Grahamana Chakra" (planet multipliers for Graha Pinda). Six of
#: seven values are IMAGE-TRANSLATION verified AND independently proven by
#: the chapter's own worked example (Sun=5, Mars=8, Moon=5, Saturn=5 all
#: reproduce the example's stated Graha Pinda total of 48 exactly; using the
#: verse's own alternate reading of 6 for Sun/Moon/Saturn instead gives 56,
#: not 48, so the verse's "6" is treated as a translation/printing error for
#: those three, never applied). Jupiter=10 and Venus=7 agree between the
#: verse and the table but are not tested by any worked example.
#: Mercury is deliberately absent here -- see `MERCURY_GRAHA_MULTIPLIER_CANDIDATES`.
GRAHA_MULTIPLIER: dict[Contributor, int] = {
    Contributor.SUN: 5,
    Contributor.MARS: 8,
    Contributor.MOON: 5,
    Contributor.JUPITER: 10,
    Contributor.VENUS: 7,
    Contributor.SATURN: 5,
}

#: Unresolved source conflict (Ch. 69 v. 1-4 vs the printed Grahamana Chakra
#: table): the verse states 6 for Mercury, the table states 5, and no
#: worked example in the chapter isolates a Mercury-only occupied sign to
#: arbitrate between them (Mercury only ever co-occupies a sign whose value
#: is 0 in the chapter's own example). No value is silently chosen; a sign
#: occupied solely by Mercury makes the whole Graha/Yoga Pinda result for
#: that chart `NOT_EVALUABLE(mercury_multiplier_conflict)`.
MERCURY_GRAHA_MULTIPLIER_CANDIDATES: dict[str, int] = {
    "grahamana_chakra_table": 5,
    "verse_1_4": 6,
}
