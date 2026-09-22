"""Cross-checks that the shipped Ashtakavarga source tables (`constants.py`)
match the reconciled Phase 9 Gate 1 comparison fixture exactly -- protects
the four independent readings from drifting apart from the audited
register, and protects the 9-cell conflict register from drifting apart
from the tables it describes. No calculator code is exercised here; this
is a static-data regression suite."""

from __future__ import annotations

from ashtakavarga_helpers import load_source_comparison

from pandit_astro_engine.ashtakavarga.constants import (
    BJ_TABLE,
    BPHS_GRID_TABLE,
    BPHS_VERSE_TABLE,
    CHART_TOTAL_INVARIANT,
    CROSS_TABLE_CONFLICTS,
    GRAND_TOTAL_INVARIANT,
    LAGNA_CHART_BPHS,
    LAGNA_CHART_TOTAL_INVARIANT,
    PHALADEEPIKA_TABLE,
    PLANET_CHARTS,
    ConflictClassification,
    Contributor,
)

_TABLES = {
    "brihat_jataka": BJ_TABLE,
    "phaladeepika": PHALADEEPIKA_TABLE,
    "bphs_grid": BPHS_GRID_TABLE,
    "bphs_verse": BPHS_VERSE_TABLE,
}


def test_fixture_has_all_56_cells() -> None:
    fixture = load_source_comparison()
    assert len(fixture["cells"]) == 56
    assert len({(c["chart"], c["contributor"]) for c in fixture["cells"]}) == 56


def test_every_fixture_cell_matches_the_shipped_table() -> None:
    fixture = load_source_comparison()
    for cell in fixture["cells"]:
        chart = Contributor(cell["chart"])
        contributor = Contributor(cell["contributor"])
        for key, table in _TABLES.items():
            assert list(table[chart][contributor]) == cell[key], (chart, contributor, key)


def test_independent_totals_match_the_invariant() -> None:
    fixture = load_source_comparison()
    totals = fixture["independent_totals"]
    for key in ("brihat_jataka", "phaladeepika", "bphs_grid"):
        assert totals[key]["grand_total"] == GRAND_TOTAL_INVARIANT
        assert totals[key]["per_chart"] == {c.value: n for c, n in CHART_TOTAL_INVARIANT.items()}
    # BPHS's own printed verse-translation list sums to 340, not 337 -- three of its
    # own internal anomalies (Mars/Saturn, Mars/Venus, Venus/Sun) each add one extra
    # benefic house relative to its own printed grid. This is reported, not corrected.
    assert totals["bphs_verse"]["grand_total"] == GRAND_TOTAL_INVARIANT + 3
    mars_total = CHART_TOTAL_INVARIANT[Contributor.MARS]
    venus_total = CHART_TOTAL_INVARIANT[Contributor.VENUS]
    assert totals["bphs_verse"]["per_chart"]["mars"] == mars_total + 2
    assert totals["bphs_verse"]["per_chart"]["venus"] == venus_total + 1


def test_grand_totals_reproduce_independently_from_the_tables() -> None:
    """Sums the tables directly (not via the fixture) -- an independent arithmetic
    check separate from the fixture-comparison test above."""
    for key, table in _TABLES.items():
        total = sum(len(table[chart][c]) for chart in PLANET_CHARTS for c in table[chart])
        expected = GRAND_TOTAL_INVARIANT if key != "bphs_verse" else GRAND_TOTAL_INVARIANT + 3
        assert total == expected, key


def test_lagna_chart_total_is_49() -> None:
    assert sum(len(v) for v in LAGNA_CHART_BPHS.values()) == LAGNA_CHART_TOTAL_INVARIANT
    assert LAGNA_CHART_TOTAL_INVARIANT == 49


def test_conflict_register_has_exactly_nine_entries() -> None:
    assert len(CROSS_TABLE_CONFLICTS) == 9


def test_conflict_register_classification_distribution() -> None:
    counts: dict[ConflictClassification, int] = {}
    for conflict in CROSS_TABLE_CONFLICTS:
        counts[conflict.classification] = counts.get(conflict.classification, 0) + 1
    assert counts[ConflictClassification.CROSS_SOURCE_VARIANT] == 2
    assert counts[ConflictClassification.BPHS_INTERNALLY_CONSISTENT_VARIANT] == 2
    assert counts[ConflictClassification.BPHS_GRID_ONLY_ANOMALY] == 2
    assert counts[ConflictClassification.BPHS_VERSE_ONLY_ANOMALY] == 3


def test_every_conflict_entry_matches_its_own_four_tables() -> None:
    for conflict in CROSS_TABLE_CONFLICTS:
        for key, table in _TABLES.items():
            assert list(table[conflict.chart][conflict.contributor]) == list(
                conflict.houses[key]
            ), (conflict.chart, conflict.contributor, key)


def test_only_47_of_56_cells_are_absent_from_the_conflict_register() -> None:
    """Every cell where all four readings agree must be absent from the register;
    every cell present in the register must have at least one differing reading."""
    conflict_cells = {(c.chart, c.contributor) for c in CROSS_TABLE_CONFLICTS}
    assert len(conflict_cells) == 9
    agreeing = 0
    for chart in PLANET_CHARTS:
        for contributor in BJ_TABLE[chart]:
            readings = {table[chart][contributor] for table in _TABLES.values()}
            all_agree = len(readings) == 1
            in_register = (chart, contributor) in conflict_cells
            assert all_agree != in_register, (chart, contributor)
            if all_agree:
                agreeing += 1
    assert agreeing == 47


def test_bphs_grid_only_anomalies_have_bj_eq_ph_eq_verse() -> None:
    for conflict in CROSS_TABLE_CONFLICTS:
        if conflict.classification == ConflictClassification.BPHS_GRID_ONLY_ANOMALY:
            h = conflict.houses
            assert h["brihat_jataka"] == h["phaladeepika"] == h["bphs_verse"]
            assert h["bphs_grid"] != h["brihat_jataka"]


def test_bphs_verse_only_anomalies_have_bj_eq_ph_eq_grid() -> None:
    for conflict in CROSS_TABLE_CONFLICTS:
        if conflict.classification == ConflictClassification.BPHS_VERSE_ONLY_ANOMALY:
            h = conflict.houses
            assert h["brihat_jataka"] == h["phaladeepika"] == h["bphs_grid"]
            assert h["bphs_verse"] != h["brihat_jataka"]
