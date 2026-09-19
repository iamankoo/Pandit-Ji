"""Phase 6N: golden fixtures run through the real engine and ruleset."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from pandit_rule_engine.engine import RuleEngine
from tests.golden_cases import CASES, GOLDEN_DIR
from tests.helpers import rules_dir

FILES = sorted(GOLDEN_DIR.glob("*.json"))


@pytest.fixture(scope="module")
def engine() -> RuleEngine:
    return RuleEngine.from_directory(rules_dir())


def _label(result: Any) -> str:
    if result.reason is None:
        return str(result.status.value)
    return f"NOT_EVALUABLE({result.reason.value})"


def test_fixture_files_match_case_definitions() -> None:
    assert [path.stem for path in FILES] == sorted(item["case_id"] for item in CASES)
    for item in CASES:
        stored = json.loads((GOLDEN_DIR / f"{item['case_id']}.json").read_text(encoding="utf-8"))
        assert stored == json.loads(json.dumps(item))


@pytest.mark.parametrize("path", FILES, ids=[path.stem for path in FILES])
def test_golden_case(engine: RuleEngine, path: Path) -> None:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    bundle = engine.evaluate_kundli(fixture["kundli"])
    by_id = {result.rule_id: result for result in bundle.results}
    for rule_id, expected in fixture["expected"].items():
        actual = by_id[rule_id]
        assert _label(actual) == expected.replace("(missing_dependency)", "(missing_dependency)"), (
            fixture["case_id"],
            rule_id,
            _label(actual),
            actual.detail,
        )
        assert actual.provenance.source_id
        assert actual.standards_version == "1.4.0"
    assert bundle.versions.calculation_standards_version == "1.3.0"
