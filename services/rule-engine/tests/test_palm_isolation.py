"""The palm ruleset and the Vedic ruleset cannot load, shadow or change each other (Phase 13)."""

from __future__ import annotations

import ast
import shutil
from pathlib import Path

import pytest

from pandit_rule_engine.loader import RulesetLoadError, load_ruleset
from pandit_rule_engine.palm import PalmRulesetLoadError, load_palm_ruleset
from tests.palm_helpers import PALM_RULES_DIR, REPO, VEDIC_RULES_DIR, load_coverage

COVERAGE = load_coverage()
# The Phase 6 Vedic ruleset hash, as recorded when the rules were sealed.
PHASE6_RULESET_HASH = "8d29a18ccd5e57c5d5ec7c70854a9e45997226f5540eb2d3c1a0bc6099b77209"


def test_the_vedic_ruleset_is_unchanged_by_phase_13() -> None:
    assert load_ruleset(VEDIC_RULES_DIR).content_hash == PHASE6_RULESET_HASH


def test_the_two_rule_id_namespaces_are_disjoint() -> None:
    vedic = set(load_ruleset(VEDIC_RULES_DIR).rules)
    palm = set(load_palm_ruleset(PALM_RULES_DIR, COVERAGE).rules)
    assert vedic and palm and not vedic & palm
    assert all(i.startswith("PALMR_") for i in palm)
    assert not any(i.startswith("PALMR_") for i in vedic)


def test_the_vedic_loader_rejects_a_palm_directory() -> None:
    with pytest.raises(RulesetLoadError) as caught:
        load_ruleset(PALM_RULES_DIR)
    assert "unknown document_type" in str(caught.value)


def test_the_palm_loader_rejects_the_vedic_directory() -> None:
    with pytest.raises(PalmRulesetLoadError) as caught:
        load_palm_ruleset(VEDIC_RULES_DIR, COVERAGE)
    assert "is not a palm document type" in str(caught.value)


def test_a_palm_file_dropped_into_a_copy_of_the_vedic_directory_breaks_it(tmp_path: Path) -> None:
    copy = tmp_path / "rules"
    shutil.copytree(VEDIC_RULES_DIR, copy)
    load_ruleset(copy)  # the copy is valid before the palm file arrives
    shutil.copy(
        PALM_RULES_DIR / "rules" / "ch_left_hand_inherited_tendencies.yaml", copy / "p.yaml"
    )
    with pytest.raises(RulesetLoadError):
        load_ruleset(copy)


def test_a_vedic_file_dropped_into_a_copy_of_the_palm_directory_breaks_it(tmp_path: Path) -> None:
    copy = tmp_path / "palm_rules"
    shutil.copytree(PALM_RULES_DIR, copy)
    vedic = next(
        p for p in sorted(VEDIC_RULES_DIR.rglob("*.yaml")) if "BPHS" in p.read_text("utf-8")
    )
    shutil.copy(vedic, copy / "v.yaml")
    with pytest.raises(PalmRulesetLoadError):
        load_palm_ruleset(copy, COVERAGE)


def test_the_palm_ruleset_hash_is_independent_of_the_vedic_hash() -> None:
    palm = load_palm_ruleset(PALM_RULES_DIR, COVERAGE).content_hash
    assert palm != PHASE6_RULESET_HASH


def test_palm_rules_live_outside_every_vedic_loader_root() -> None:
    assert PALM_RULES_DIR.parent == REPO / "services" / "rule-engine"
    roots = [VEDIC_RULES_DIR, REPO / "services" / "rule-engine" / "src"]
    for root in roots:
        assert not [
            p
            for p in root.rglob("*.yaml")
            if "palm" in p.read_text("utf-8").lower()[:400]
            and "document_type: palm" in p.read_text("utf-8")
        ]
    assert not [p for p in VEDIC_RULES_DIR.rglob("*") if "palm" in p.name.lower()]


def test_the_palm_package_never_imports_the_vedic_evaluator() -> None:
    palm_dir = REPO / "services" / "rule-engine" / "src" / "pandit_rule_engine" / "palm"
    forbidden = {"engine", "evaluator", "tables", "evidence"}
    for path in palm_dir.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text("utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module:
                parts = node.module.split(".")
                if parts[0] == "pandit_rule_engine" and len(parts) > 1 and parts[1] != "palm":
                    pytest.fail(f"{path.name} imports {node.module}")
                assert parts[0] not in {"pandit_astro", "pandit_knowledge", "cv2", "numpy"}, (
                    path.name,
                    node.module,
                )
            if isinstance(node, ast.Import):
                assert not any(
                    a.name.split(".")[0] in {"cv2", "numpy", "torch"} for a in node.names
                )
    assert forbidden  # documented list of the Vedic modules the palm package must not touch
