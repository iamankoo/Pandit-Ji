"""Phase 6E: EvidenceBundle, provenance and ruleset hashing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from pandit_rule_engine._version import __version__
from pandit_rule_engine.bundle import EvidenceBundle, build_bundle
from pandit_rule_engine.evaluator import evaluate_ruleset
from pandit_rule_engine.hashing import canonical_json
from pandit_rule_engine.loader import Ruleset, load_ruleset
from pandit_rule_engine.vocab import Reason, Status
from tests.chart_builder import chart, full_placements
from tests.helpers import StubDerived, manifest_doc, rule_doc, write_ruleset


def _rule(rule_id: str, houses: list[int], **overrides: Any) -> dict[str, Any]:
    reading = {
        "reading_id": "R1",
        "basis": "translation",
        "conditions": {"op": "planet_house", "planet": "jupiter", "houses": houses},
    }
    return rule_doc(rule_id=rule_id, profile=rule_id, readings=[reading], **overrides)


def _ruleset(tmp_path: Path, extra: dict[str, dict[str, Any]] | None = None) -> Ruleset:
    documents = {
        "ruleset.yaml": manifest_doc(),
        "bphs/a.yaml": _rule("TEST_A", [4], conflict_group="TEST_TOPIC"),
        "bphs/b.yaml": _rule("TEST_B", [5], conflict_group="TEST_TOPIC"),
        "modern/c.yaml": _rule("TEST_C", [1], ambiguity_group="TEST_AMBIG"),
    }
    documents.update(extra or {})
    write_ruleset(tmp_path, documents)
    return load_ruleset(tmp_path)


def _bundle(ruleset: Ruleset, facts: Any) -> EvidenceBundle:
    results = evaluate_ruleset(ruleset, facts, StubDerived())
    return build_bundle(
        ruleset=ruleset,
        facts=facts,
        results=results,
        derived_facts={"note": "stub"},
        rule_engine_version=__version__,
    )


# --------------------------------------------------------------------------
# Ruleset hash
# --------------------------------------------------------------------------


def test_identical_logical_rulesets_have_identical_hashes(tmp_path: Path) -> None:
    first = _ruleset(tmp_path / "one")
    # Same rules, different file layout, file names and YAML key order.
    layout = tmp_path / "two"
    write_ruleset(
        layout,
        {
            "z/manifest.yaml": manifest_doc(),
            "q/1.yaml": _rule("TEST_C", [1], ambiguity_group="TEST_AMBIG"),
            "q/2.yaml": _rule("TEST_B", [5], conflict_group="TEST_TOPIC"),
            "q/3.yaml": _rule("TEST_A", [4], conflict_group="TEST_TOPIC"),
        },
    )
    reordered = layout / "q" / "3.yaml"
    document = yaml.safe_load(reordered.read_text(encoding="utf-8"))
    reordered.write_text(
        yaml.safe_dump(dict(reversed(list(document.items()))), sort_keys=False), encoding="utf-8"
    )
    second = load_ruleset(layout)
    assert first.content_hash == second.content_hash


def test_hash_ignores_comments_and_whitespace(tmp_path: Path) -> None:
    ruleset = _ruleset(tmp_path)
    path = tmp_path / "bphs" / "a.yaml"
    path.write_text("# a comment\n\n" + path.read_text(encoding="utf-8") + "\n\n", encoding="utf-8")
    assert load_ruleset(tmp_path).content_hash == ruleset.content_hash


def test_hash_changes_when_a_rule_changes(tmp_path: Path) -> None:
    baseline = _ruleset(tmp_path / "base").content_hash
    changed = _ruleset(tmp_path / "changed", {"bphs/a.yaml": _rule("TEST_A", [4, 7])})
    assert changed.content_hash != baseline


def test_hash_changes_when_ruleset_version_changes(tmp_path: Path) -> None:
    baseline = _ruleset(tmp_path / "base").content_hash
    bumped = _ruleset(tmp_path / "bumped", {"ruleset.yaml": manifest_doc(ruleset_version="1.0.1")})
    assert bumped.content_hash != baseline


def test_canonical_json_is_key_order_independent() -> None:
    assert canonical_json({"b": 1, "a": [2, 1]}) == canonical_json({"a": [2, 1], "b": 1})
    assert canonical_json({"a": 1}) == '{"a":1}'


# --------------------------------------------------------------------------
# Bundle content
# --------------------------------------------------------------------------


def test_bundle_keeps_every_result_status_and_versions(tmp_path: Path) -> None:
    ruleset = _ruleset(tmp_path)
    facts = chart("aries", full_placements(jupiter="cancer"), timezone="Asia/Kolkata")
    bundle = _bundle(ruleset, facts)
    by_id = {result.rule_id: result for result in bundle.results}
    assert by_id["TEST_A"].status is Status.TRIGGERED
    assert by_id["TEST_B"].status is Status.NOT_TRIGGERED
    assert bundle.summary.triggered == ("TEST_A",)
    assert set(bundle.summary.not_triggered) == {"TEST_B", "TEST_C"}
    versions = bundle.versions
    assert versions.rule_engine_version == __version__
    assert versions.rule_standards_version == "1.4.0"
    assert versions.calculation_standards_version == "1.3.0"
    assert versions.calculation_engine_version == "test-astro"
    assert versions.ruleset_content_hash == ruleset.content_hash
    assert versions.hash_algorithm == "sha256"


def test_bundle_snapshot_carries_calculation_configuration(tmp_path: Path) -> None:
    bundle = _bundle(_ruleset(tmp_path), chart("aries", full_placements()))
    calc = bundle.chart.calculation
    assert (calc.ayanamsa, calc.node_convention, calc.house_system) == (
        "lahiri",
        "mean",
        "vedic_whole_sign",
    )
    assert calc.timezone == "Asia/Kolkata"
    assert (calc.latitude, calc.longitude) == (28.61, 77.2)
    assert [planet.body.value for planet in bundle.chart.planets][:3] == ["sun", "moon", "mars"]


def test_bundle_lists_not_evaluable_results_and_unresolved_dependencies(tmp_path: Path) -> None:
    bundle = _bundle(_ruleset(tmp_path), chart("aries", {"moon": "cancer"}))
    assert set(bundle.summary.not_evaluable) == {"TEST_A", "TEST_B", "TEST_C"}
    record = bundle.dependencies[0]
    assert record.reason is Reason.MISSING_DEPENDENCY
    assert record.detail == "planet.jupiter"
    assert record.rule_ids == ("TEST_A", "TEST_B", "TEST_C")


def test_bundle_preserves_conflict_groups_without_resolving_them(tmp_path: Path) -> None:
    bundle = _bundle(_ruleset(tmp_path), chart("aries", full_placements(jupiter="cancer")))
    groups = {(group.kind, group.group_id): group for group in bundle.conflicts}
    conflict = groups[("conflict", "TEST_TOPIC")]
    assert conflict.rule_ids == ("TEST_A", "TEST_B")
    assert conflict.statuses == {"TEST_A": "TRIGGERED", "TEST_B": "NOT_TRIGGERED"}
    assert ("ambiguity", "TEST_AMBIG") in groups


def test_bundle_records_source_profiles_and_result_provenance(tmp_path: Path) -> None:
    bundle = _bundle(_ruleset(tmp_path), chart("aries", full_placements()))
    assert [record.profile for record in bundle.source_profiles] == ["TEST_A", "TEST_B", "TEST_C"]
    for result in bundle.results:
        assert result.provenance.source_id == "TEST_WORK"
        assert result.provenance.source_location == "Ch. 1 v. 1"
        assert result.standards_version == "1.4.0"
        assert [reading.reading_id for reading in result.readings] == ["R1"]


# --------------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------------


def test_same_inputs_produce_the_same_bundle_and_hash(tmp_path: Path) -> None:
    first_set = _ruleset(tmp_path / "one")
    second_set = _ruleset(tmp_path / "two")
    facts = chart("aries", full_placements(jupiter="cancer"))
    first = _bundle(first_set, facts)
    second = _bundle(second_set, chart("aries", full_placements(jupiter="cancer")))
    assert first.canonical_json() == second.canonical_json()
    assert first.bundle_hash == second.bundle_hash and len(first.bundle_hash) == 64


def test_bundle_hash_changes_with_the_chart_or_the_ruleset(tmp_path: Path) -> None:
    ruleset = _ruleset(tmp_path)
    base = _bundle(ruleset, chart("aries", full_placements(jupiter="cancer")))
    other_chart = _bundle(ruleset, chart("aries", full_placements(jupiter="leo")))
    assert other_chart.bundle_hash != base.bundle_hash
    changed = _ruleset(tmp_path / "x", {"bphs/a.yaml": _rule("TEST_A", [4, 7])})
    other_rules = _bundle(changed, chart("aries", full_placements(jupiter="cancer")))
    assert other_rules.bundle_hash != base.bundle_hash


def test_bundle_has_no_timestamp_or_host_specific_fields(tmp_path: Path) -> None:
    text = _bundle(_ruleset(tmp_path), chart("aries", full_placements())).canonical_json()
    assert str(tmp_path).replace("\\", "/") not in text.replace("\\\\", "/")
    for forbidden in ("evaluated_at", "generated_at", "hostname", "pid"):
        assert forbidden not in text


def test_historical_phase5_standards_version_is_not_upgraded(tmp_path: Path) -> None:
    facts = chart("aries", full_placements(), standards_version="1.3.0")
    bundle = _bundle(_ruleset(tmp_path), facts)
    assert bundle.chart.calculation.standards_version == "1.3.0"
    assert bundle.versions.calculation_standards_version == "1.3.0"
    assert bundle.versions.rule_standards_version == "1.4.0"
