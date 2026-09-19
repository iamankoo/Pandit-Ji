"""Phase 6B: rule loader, registration and deterministic ordering."""

from __future__ import annotations

from pathlib import Path

import pytest

from pandit_rule_engine.loader import RulesetLoadError, load_ruleset
from tests.helpers import manifest_doc, rule_doc, write_ruleset


def _rule(rule_id: str, **overrides: object) -> dict[str, object]:
    return rule_doc(rule_id=rule_id, profile=rule_id, **overrides)


def test_loads_valid_ruleset(tmp_path: Path) -> None:
    write_ruleset(
        tmp_path,
        {
            "ruleset.yaml": manifest_doc(),
            "bphs/a.yaml": _rule("TEST_A"),
            "modern/b.yaml": _rule("TEST_B"),
        },
    )
    ruleset = load_ruleset(tmp_path)
    assert list(ruleset.rules) == ["TEST_A", "TEST_B"]
    assert ruleset.manifest.ruleset_version == "1.0.0"
    assert ruleset.evaluation_order == ("TEST_A", "TEST_B")


def test_readme_files_are_ignored(tmp_path: Path) -> None:
    write_ruleset(tmp_path, {"ruleset.yaml": manifest_doc()})
    (tmp_path / "README.md").write_text("# not a rule", encoding="utf-8")
    assert load_ruleset(tmp_path).rules == {}


def test_registration_is_independent_of_file_layout(tmp_path: Path) -> None:
    one = tmp_path / "one"
    two = tmp_path / "two"
    write_ruleset(
        one,
        {"ruleset.yaml": manifest_doc(), "a/x.yaml": _rule("TEST_A"), "b/y.yaml": _rule("TEST_B")},
    )
    write_ruleset(
        two,
        {"z/ruleset.yaml": manifest_doc(), "q.yaml": _rule("TEST_B"), "r.yaml": _rule("TEST_A")},
    )
    first = load_ruleset(one)
    second = load_ruleset(two)
    assert list(first.rules) == list(second.rules)
    assert first.evaluation_order == second.evaluation_order


def test_priority_orders_evaluation_but_never_removes_rules(tmp_path: Path) -> None:
    write_ruleset(
        tmp_path,
        {
            "ruleset.yaml": manifest_doc(),
            "a.yaml": _rule("TEST_A", priority=200),
            "b.yaml": _rule("TEST_B", priority=1),
        },
    )
    ruleset = load_ruleset(tmp_path)
    assert ruleset.evaluation_order == ("TEST_B", "TEST_A")
    assert set(ruleset.rules) == {"TEST_A", "TEST_B"}


def test_duplicate_rule_id_is_an_error(tmp_path: Path) -> None:
    write_ruleset(
        tmp_path,
        {"ruleset.yaml": manifest_doc(), "a.yaml": _rule("TEST_A"), "b.yaml": _rule("TEST_A")},
    )
    with pytest.raises(RulesetLoadError, match="duplicate rule_id TEST_A"):
        load_ruleset(tmp_path)


def test_invalid_yaml_is_an_error(tmp_path: Path) -> None:
    write_ruleset(tmp_path, {"ruleset.yaml": manifest_doc()})
    (tmp_path / "broken.yaml").write_text("a: [unclosed", encoding="utf-8")
    with pytest.raises(RulesetLoadError, match="invalid YAML"):
        load_ruleset(tmp_path)


def test_duplicate_yaml_keys_are_an_error(tmp_path: Path) -> None:
    write_ruleset(tmp_path, {"ruleset.yaml": manifest_doc()})
    (tmp_path / "dup.yaml").write_text("rule_id: A\nrule_id: B\n", encoding="utf-8")
    with pytest.raises(RulesetLoadError, match="invalid YAML"):
        load_ruleset(tmp_path)


def test_schema_failure_is_reported_with_file(tmp_path: Path) -> None:
    doc = _rule("TEST_A")
    del doc["source_id"]
    write_ruleset(tmp_path, {"ruleset.yaml": manifest_doc(), "bphs/a.yaml": doc})
    with pytest.raises(RulesetLoadError, match=r"bphs/a\.yaml: schema validation failed"):
        load_ruleset(tmp_path)


def test_unknown_document_type_is_an_error(tmp_path: Path) -> None:
    write_ruleset(tmp_path, {"ruleset.yaml": manifest_doc(), "x.yaml": {"document_type": "script"}})
    with pytest.raises(RulesetLoadError, match="unknown document_type"):
        load_ruleset(tmp_path)


def test_manifest_is_required_and_unique(tmp_path: Path) -> None:
    write_ruleset(tmp_path, {"a.yaml": _rule("TEST_A")})
    with pytest.raises(RulesetLoadError, match="exactly one ruleset manifest"):
        load_ruleset(tmp_path)
    other = tmp_path / "other"
    write_ruleset(other, {"m1.yaml": manifest_doc(), "m2.yaml": manifest_doc(ruleset_id="OTHER")})
    with pytest.raises(RulesetLoadError, match="exactly one ruleset manifest"):
        load_ruleset(other)


def test_standards_version_must_match_manifest(tmp_path: Path) -> None:
    write_ruleset(
        tmp_path,
        {"ruleset.yaml": manifest_doc(), "a.yaml": _rule("TEST_A", standards_version="1.3.0")},
    )
    with pytest.raises(RulesetLoadError, match="does not match ruleset"):
        load_ruleset(tmp_path)


def test_missing_directory_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(RulesetLoadError, match="not found"):
        load_ruleset(tmp_path / "nope")


def _depends_on(rule_id: str, target: str) -> dict[str, object]:
    readings = [
        {
            "reading_id": "R1",
            "basis": "convention",
            "conditions": {"op": "rule_result", "rule_id": target, "in": ["TRIGGERED"]},
        }
    ]
    return _rule(rule_id, readings=readings)


def test_rule_dependencies_are_ordered_before_dependents(tmp_path: Path) -> None:
    write_ruleset(
        tmp_path,
        {
            "ruleset.yaml": manifest_doc(),
            "a.yaml": _depends_on("TEST_A", "TEST_Z"),
            "z.yaml": _rule("TEST_Z", priority=500),
        },
    )
    assert load_ruleset(tmp_path).evaluation_order == ("TEST_Z", "TEST_A")


def test_rule_dependency_cycle_is_an_error(tmp_path: Path) -> None:
    write_ruleset(
        tmp_path,
        {
            "ruleset.yaml": manifest_doc(),
            "a.yaml": _depends_on("TEST_A", "TEST_B"),
            "b.yaml": _depends_on("TEST_B", "TEST_A"),
        },
    )
    with pytest.raises(RulesetLoadError, match="cycle"):
        load_ruleset(tmp_path)


def test_unknown_rule_dependency_is_an_error(tmp_path: Path) -> None:
    write_ruleset(
        tmp_path, {"ruleset.yaml": manifest_doc(), "a.yaml": _depends_on("TEST_A", "TEST_NONE")}
    )
    with pytest.raises(RulesetLoadError, match="unknown rule TEST_NONE"):
        load_ruleset(tmp_path)


def test_deprecated_rules_are_registered_but_not_ordered(tmp_path: Path) -> None:
    write_ruleset(
        tmp_path,
        {
            "ruleset.yaml": manifest_doc(),
            "a.yaml": _rule("TEST_A", status="deprecated"),
            "b.yaml": _rule("TEST_B"),
        },
    )
    ruleset = load_ruleset(tmp_path)
    assert set(ruleset.rules) == {"TEST_A", "TEST_B"}
    assert ruleset.evaluation_order == ("TEST_B",)
