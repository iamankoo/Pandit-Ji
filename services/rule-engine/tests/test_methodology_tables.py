"""Phase 6F-6H: relationships, natural nature, the Ch. 34 table and
Moolatrikona, built from the repository's real methodology tables."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from pandit_rule_engine.derived import TableDerivedFacts
from pandit_rule_engine.loader import RulesetLoadError, load_ruleset
from pandit_rule_engine.tables import FUNCTIONAL_LABELS, Tables, build_tables
from pandit_rule_engine.vocab import CLASSICAL_BODIES, Body, Dignity, Reason, Sign
from tests.chart_builder import chart, full_placements
from tests.helpers import rules_dir


@pytest.fixture(scope="module")
def tables() -> Tables:
    return build_tables(load_ruleset(rules_dir()).tables)


def _derived(tables: Tables, lagna: str = "aries", **placements: object) -> TableDerivedFacts:
    facts = chart(lagna, full_placements(**placements))  # type: ignore[arg-type]
    return TableDerivedFacts(facts, tables)


# --------------------------------------------------------------------------
# 6F: natural, temporal and compound relationships
# --------------------------------------------------------------------------

_FRIENDS = {
    "sun": {"moon", "mars", "jupiter"},
    "moon": {"sun", "mercury"},
    "mars": {"sun", "moon", "jupiter"},
    "mercury": {"sun", "venus"},
    "jupiter": {"sun", "moon", "mars"},
    "venus": {"mercury", "saturn"},
    "saturn": {"mercury", "venus"},
}
_ENEMIES = {
    "sun": {"venus", "saturn"},
    "moon": set(),
    "mars": {"mercury"},
    "mercury": {"moon"},
    "jupiter": {"mercury", "venus"},
    "venus": {"sun", "moon"},
    "saturn": {"sun", "moon", "mars"},
}


def test_natural_relationship_table_matches_the_standard_exactly(tables: Tables) -> None:
    for a in CLASSICAL_BODIES:
        for b in CLASSICAL_BODIES:
            if a is b:
                continue
            expected = (
                "friend"
                if b.value in _FRIENDS[a.value]
                else "enemy"
                if b.value in _ENEMIES[a.value]
                else "equal"
            )
            assert tables.natural_relationships.kind(a, b) == expected, (a, b)


def test_moon_has_no_enemy_and_relationships_are_not_symmetric(tables: Tables) -> None:
    relations = tables.natural_relationships
    assert all(
        relations.kind(Body.MOON, other) != "enemy"
        for other in CLASSICAL_BODIES
        if other is not Body.MOON
    )
    assert relations.kind(Body.MOON, Body.MERCURY) == "friend"
    assert relations.kind(Body.MERCURY, Body.MOON) == "enemy"


def test_moon_row_conflict_is_recorded_as_bounded_source_conflict() -> None:
    document = yaml.safe_load(
        (rules_dir() / "bphs" / "tables" / "relationships_natural_3_55.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert "Benares" in document["data"]["note"]
    assert document["verification_level"] == "IMAGE-TRANSLATION"


def test_temporal_relationship_uses_the_friend_houses(tables: Tables) -> None:
    # Sun in Aries: a planet in the 2nd/3rd/4th/10th/11th/12th sign is a temporal friend.
    for sign, expected in (
        ("taurus", "friend"),
        ("aries", "enemy"),
        ("cancer", "friend"),
        ("leo", "enemy"),
        ("virgo", "enemy"),
        ("libra", "enemy"),
        ("capricorn", "friend"),
        ("pisces", "friend"),
    ):
        derived = _derived(tables, sun="aries", jupiter=sign)
        natural = tables.natural_relationships.kind(Body.SUN, Body.JUPITER)
        assert natural == "friend"
        compound = derived.relationship("compound", Body.SUN, Body.JUPITER).kind
        assert compound == ("great_friend" if expected == "friend" else "equal"), sign


def test_temporal_relationship_is_mutual(tables: Tables) -> None:
    derived = _derived(tables, mars="aries", saturn="gemini")
    forward = derived.relationship("compound", Body.MARS, Body.SATURN).kind
    backward = derived.relationship("compound", Body.SATURN, Body.MARS).kind
    # Mars: Saturn is an equal (natural) and in the 3rd (temporal friend) -> friend.
    assert forward == "friend"
    # Saturn: Mars is a natural enemy and in the 11th (temporal friend) -> equal.
    assert backward == "equal"


@pytest.mark.parametrize(
    ("natural", "temporal", "compound"),
    [
        ("friend", "friend", "great_friend"),
        ("friend", "enemy", "equal"),
        ("equal", "friend", "friend"),
        ("equal", "enemy", "enemy"),
        ("enemy", "friend", "equal"),
        ("enemy", "enemy", "great_enemy"),
    ],
)
def test_compound_relationship_matrix(
    tables: Tables, natural: str, temporal: str, compound: str
) -> None:
    assert tables.compound_relationship.result(natural, temporal) == compound  # type: ignore[arg-type]


def test_nodes_have_no_relationships(tables: Tables) -> None:
    derived = _derived(tables)
    for basis in ("natural", "compound"):
        for pair in ((Body.RAHU, Body.SUN), (Body.SUN, Body.KETU)):
            value = derived.relationship(basis, *pair)
            assert value.kind is None and value.reason is Reason.NOT_SPECIFIED_BY_SOURCE


# --------------------------------------------------------------------------
# 6F: natural benefic / malefic
# --------------------------------------------------------------------------


def test_fixed_natural_natures(tables: Tables) -> None:
    derived = _derived(tables)
    for body in (Body.SUN, Body.SATURN, Body.MARS, Body.RAHU, Body.KETU):
        assert derived.natural_nature(body).value == "malefic", body
    for body in (Body.JUPITER, Body.VENUS):
        assert derived.natural_nature(body).value == "benefic", body


def test_moon_waxing_and_waning_by_elongation(tables: Tables) -> None:
    waxing = _derived(tables, sun=("aries", 10.0), moon=("cancer", 10.0))  # elongation 90
    waning = _derived(tables, sun=("aries", 10.0), moon=("libra", 20.0))  # elongation 200
    assert waxing.natural_nature(Body.MOON).value == "benefic"
    assert waning.natural_nature(Body.MOON).value == "malefic"


@pytest.mark.parametrize(
    ("sun", "moon"),
    [(("aries", 10.0), ("aries", 10.0)), (("aries", 10.0), ("libra", 10.0))],
)
def test_moon_exactly_on_the_boundary_is_reading_ambiguous(
    tables: Tables, sun: tuple[str, float], moon: tuple[str, float]
) -> None:
    value = _derived(tables, sun=sun, moon=moon).natural_nature(Body.MOON)
    assert value.value == "boundary" and value.reason is Reason.READING_AMBIGUOUS


def test_moon_nature_needs_sun_and_moon(tables: Tables) -> None:
    facts = chart("aries", {"moon": "cancer", "mars": "aries"})
    value = TableDerivedFacts(facts, tables).natural_nature(Body.MOON)
    assert value.reason is Reason.MISSING_DEPENDENCY and value.detail == "planet.sun"


def _mercury(tables: Tables, **placements: object) -> str:
    base = {
        "sun": "aries",
        "moon": ("cancer", 10.0),
        "mars": "aries",
        "mercury": "gemini",
        "jupiter": "aries",
        "venus": "aries",
        "saturn": "aries",
        "rahu": "aries",
        "ketu": "libra",
    }
    base.update(placements)
    facts = chart("aries", base)  # type: ignore[arg-type]
    return TableDerivedFacts(facts, tables).natural_nature(Body.MERCURY).value


def test_mercury_nature_follows_his_same_sign_associates(tables: Tables) -> None:
    alone = _mercury(
        tables,
        sun="leo",
        mars="leo",
        jupiter="leo",
        venus="leo",
        saturn="leo",
        rahu="leo",
        ketu="leo",
    )
    assert alone == "benefic"
    assert _mercury(tables, saturn="gemini") == "malefic"
    assert (
        _mercury(
            tables,
            jupiter="gemini",
            sun="leo",
            mars="leo",
            saturn="leo",
            rahu="leo",
            ketu="leo",
            venus="leo",
        )
        == "benefic"
    )


def test_mercury_with_both_malefic_and_benefic_is_ambiguous(tables: Tables) -> None:
    facts = chart(
        "aries",
        {
            "sun": "leo",
            "moon": ("cancer", 10.0),
            "mars": "leo",
            "mercury": "gemini",
            "jupiter": "gemini",
            "venus": "leo",
            "saturn": "gemini",
            "rahu": "leo",
            "ketu": "leo",
        },
    )
    value = TableDerivedFacts(facts, tables).natural_nature(Body.MERCURY)
    assert value.value == "mixed" and value.reason is Reason.READING_AMBIGUOUS


def test_mercury_with_a_node_is_with_a_malefic(tables: Tables) -> None:
    assert _mercury(tables, rahu="gemini") == "malefic"


def test_mercury_needs_every_body_present_to_be_classified(tables: Tables) -> None:
    facts = chart("aries", {"sun": "leo", "moon": "cancer", "mercury": "gemini"})
    value = TableDerivedFacts(facts, tables).natural_nature(Body.MERCURY)
    assert value.reason is Reason.MISSING_DEPENDENCY


# --------------------------------------------------------------------------
# 6G: BPHS Ch. 34 functional-nature table
# --------------------------------------------------------------------------


def test_table_has_84_cells_all_with_source_labels(tables: Tables) -> None:
    cells = [
        (lagna, body, cell)
        for lagna, entry in tables.functional_nature.lagnas.items()
        for body, cell in entry.cells.items()
    ]
    assert len(cells) == 84
    assert {lagna for lagna, _, _ in cells} == set(Sign)
    assert {body for _, body, _ in cells} == set(CLASSICAL_BODIES)
    for _, _, cell in cells:
        assert set(cell.labels) <= FUNCTIONAL_LABELS


def test_exactly_the_five_silent_cells_are_not_specified_by_source(tables: Tables) -> None:
    silent = {
        (lagna, body)
        for lagna, entry in tables.functional_nature.lagnas.items()
        for body, cell in entry.cells.items()
        if cell.status == "not_specified_by_source"
    }
    assert silent == {
        (Sign.ARIES, Body.MOON),
        (Sign.GEMINI, Body.MERCURY),
        (Sign.GEMINI, Body.SATURN),
        (Sign.VIRGO, Body.SATURN),
        (Sign.SAGITTARIUS, Body.MOON),
    }
    for lagna, body in silent:
        value = tables.functional(lagna, body)
        assert value.status == "not_specified_by_source" and value.labels == ()


@pytest.mark.parametrize(
    ("lagna", "body", "labels"),
    [
        (Sign.ARIES, Body.SUN, ("auspicious",)),
        (Sign.ARIES, Body.VENUS, ("malefic", "killer")),
        (Sign.ARIES, Body.MARS, ("helpful_to_auspicious",)),
        (Sign.TAURUS, Body.SATURN, ("auspicious", "rajayoga")),
        (Sign.TAURUS, Body.MERCURY, ("somewhat_auspicious",)),
        (Sign.GEMINI, Body.VENUS, ("auspicious", "only_auspicious_planet")),
        (Sign.CANCER, Body.SUN, ("killer_by_association",)),
        (Sign.LEO, Body.SATURN, ("malefic", "killer_by_association")),
        (Sign.VIRGO, Body.SUN, ("association_dependent",)),
        (Sign.LIBRA, Body.MOON, ("rajayoga_with_mercury",)),
        (Sign.LIBRA, Body.SUN, ("malefic", "killer")),
        (Sign.LIBRA, Body.JUPITER, ("malefic", "killer")),
        (Sign.LIBRA, Body.VENUS, ("neutral",)),
        (Sign.SCORPIO, Body.SUN, ("yogakaraka",)),
        (Sign.SCORPIO, Body.MOON, ("auspicious", "yogakaraka")),
        (Sign.SAGITTARIUS, Body.MERCURY, ("yoga_with_sun",)),
        (Sign.CAPRICORN, Body.SATURN, ("not_killer_of_own",)),
        (Sign.AQUARIUS, Body.MERCURY, ("meddling_mixed",)),
        (Sign.AQUARIUS, Body.VENUS, ("auspicious", "rajayoga", "only_rajayoga_planet")),
        (Sign.PISCES, Body.MARS, ("auspicious", "yoga", "killer_not_independent")),
        (Sign.PISCES, Body.JUPITER, ("yoga_with_mars",)),
    ],
)
def test_source_labels_are_preserved_exactly(
    tables: Tables, lagna: Sign, body: Body, labels: tuple[str, ...]
) -> None:
    value = tables.functional(lagna, body)
    assert value.status == "specified" and value.labels == labels


def test_nodes_are_outside_the_functional_table(tables: Tables) -> None:
    for node in (Body.RAHU, Body.KETU):
        value = tables.functional(Sign.ARIES, node)
        assert value.status == "outside_table" and value.labels == () and value.verse is None


def test_functional_table_has_no_scores() -> None:
    text = (rules_dir() / "bphs" / "tables" / "functional_nature_34_table.yaml").read_text(
        encoding="utf-8"
    )
    document = yaml.safe_load(text)

    def numbers(node: object) -> list[object]:
        if isinstance(node, dict):
            return [n for value in node.values() for n in numbers(value)]
        if isinstance(node, list):
            return [n for value in node for n in numbers(value)]
        return [node] if isinstance(node, (int, float)) and not isinstance(node, bool) else []

    assert numbers(document["data"]) == []


def test_derived_snapshot_reports_functional_cells_for_the_lagna(tables: Tables) -> None:
    snapshot = _derived(tables, lagna="gemini").snapshot()["functional_nature"]
    assert snapshot["lagna"] == "gemini"
    assert snapshot["cells"]["venus"]["labels"] == ["auspicious", "only_auspicious_planet"]
    assert snapshot["cells"]["mercury"]["status"] == "not_specified_by_source"
    assert snapshot["cells"]["rahu"]["status"] == "outside_table"


def test_invalid_table_data_is_rejected_by_the_loader(tmp_path: Path) -> None:
    copy = tmp_path / "rules"
    shutil.copytree(rules_dir(), copy)
    path = copy / "bphs" / "tables" / "functional_nature_34_table.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    del document["data"]["lagnas"]["pisces"]
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(RulesetLoadError, match="table data invalid"):
        load_ruleset(copy)
    document["data"]["lagnas"]["pisces"] = {
        "verse": "34.43-44",
        "cells": {body.value: {"labels": ["superb"]} for body in CLASSICAL_BODIES},
    }
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(RulesetLoadError, match="table data invalid"):
        load_ruleset(copy)


# --------------------------------------------------------------------------
# 6H: Moolatrikona
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "sign", "degree", "expected"),
    [
        ("sun", "leo", 0.0, True),
        ("sun", "leo", 19.99, True),
        ("sun", "leo", 20.0, False),
        ("sun", "aries", 5.0, False),
        ("moon", "taurus", 2.99, False),
        ("moon", "taurus", 3.0, True),
        ("moon", "taurus", 29.9, True),
        ("mars", "aries", 11.99, True),
        ("mars", "aries", 12.0, False),
        ("mercury", "virgo", 14.99, False),
        ("mercury", "virgo", 15.0, True),
        ("mercury", "virgo", 20.0, False),
        ("jupiter", "sagittarius", 9.99, True),
        ("jupiter", "sagittarius", 10.0, False),
        ("venus", "libra", 14.99, True),
        ("venus", "libra", 15.0, False),
        ("saturn", "aquarius", 19.99, True),
        ("saturn", "aquarius", 20.0, False),
        ("saturn", "capricorn", 5.0, False),
    ],
)
def test_moolatrikona_ranges_and_boundaries(
    tables: Tables, body: str, sign: str, degree: float, expected: bool
) -> None:
    derived = _derived(tables, **{body: (sign, degree)})
    fact = derived.moolatrikona(Body(body))
    assert fact.value is expected and fact.reason is None


def test_moolatrikona_is_separate_from_phase5_dignity(tables: Tables) -> None:
    facts = chart("aries", full_placements(sun=("leo", 10.0)))
    sun = facts.planets[Body.SUN]
    assert sun.dignity is Dignity.OWN_SIGN  # Phase 5 dignity is unchanged
    assert TableDerivedFacts(facts, tables).moolatrikona(Body.SUN).value is True
    assert "moolatrikona" not in {member.value for member in Dignity}


def test_moolatrikona_unavailable_for_nodes_and_missing_planets(tables: Tables) -> None:
    derived = _derived(tables)
    for node in (Body.RAHU, Body.KETU):
        fact = derived.moolatrikona(node)
        assert fact.value is None and fact.reason is Reason.REQUIRES_MOOLATRIKONA
    facts = chart("aries", {"moon": "cancer"})
    missing = TableDerivedFacts(facts, tables).moolatrikona(Body.SUN)
    assert missing.reason is Reason.MISSING_DEPENDENCY


def test_repository_ruleset_tables_carry_provenance() -> None:
    ruleset = load_ruleset(rules_dir())
    assert len(ruleset.tables) == 6
    for table in ruleset.tables.values():
        assert table.source_id == "BPHS_SANTHANAM_1984"
        assert table.translator == "R. Santhanam"
        assert table.standards_version == "1.4.0"
        assert table.source_tier == 2
