"""Phase 12 touches no calculation, rule or evidence-bundle behaviour (KB-38, KB-39).

These tests need the sibling ``astro-engine`` and ``rule-engine`` packages and are skipped
where they are not installed (the knowledge CI matrix job); the dedicated knowledge integration
job installs them and runs everything.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pandit_knowledge.content import DEFAULT_RULES_DIR, KnowledgeContent, rule_index

REPO = Path(__file__).resolve().parents[3]

# Recorded at the Phase 11 stopping point (HEAD 62fd4ac), before any Phase 12 change.
PHASE11_RULESET_CONTENT_HASH = "8d29a18ccd5e57c5d5ec7c70854a9e45997226f5540eb2d3c1a0bc6099b77209"
PHASE11_RULE_FILES_SNAPSHOT = "245326144f9933e9b3f758e0bbf603d8afedca5a852c1091bd945dfb88d1a736"
PHASE11_BUNDLE_FIELDS = [
    "bundle_version", "versions", "chart", "derived_facts", "results", "summary", "conflicts",
    "dependencies", "source_profiles", "dasha", "transit", "ashtakavarga", "kp", "shadbala",
    "jaimini", "chinese", "tarot", "panchang", "compatibility", "numerology", "bundle_hash",
]  # fmt: skip


def test_rule_yaml_files_are_unchanged_since_phase_11() -> None:
    assert rule_index(DEFAULT_RULES_DIR)[1] == PHASE11_RULE_FILES_SNAPSHOT


def test_phase6_ruleset_hash_is_unchanged() -> None:
    loader = pytest.importorskip("pandit_rule_engine.loader")
    ruleset = loader.load_ruleset(DEFAULT_RULES_DIR)
    assert ruleset.content_hash == PHASE11_RULESET_CONTENT_HASH


def test_every_referenced_rule_and_table_is_loaded_by_the_rule_engine(
    content: KnowledgeContent,
) -> None:
    loader = pytest.importorskip("pandit_rule_engine.loader")
    ruleset = loader.load_ruleset(DEFAULT_RULES_DIR)
    known = set(ruleset.rules) | set(ruleset.tables)
    for ref in content.rule_references:
        if ref.rule_kind.value in {"RULE", "TABLE"}:
            assert ref.rule_id in known, ref.rule_id
    for exc in content.exceptions:
        assert exc.affected_rule_id in ruleset.rules, exc.affected_rule_id


def test_exception_summaries_match_the_rules_own_cancellations(
    content: KnowledgeContent,
) -> None:
    """The knowledge exceptions record cancellations the rule already encodes; none is new."""
    loader = pytest.importorskip("pandit_rule_engine.loader")
    ruleset = loader.load_ruleset(DEFAULT_RULES_DIR)
    kem = ruleset.rules["PHALADEEPIKA_SASTRI_KEMADRUMA_6_5"]
    assert {c.cancellation_id for c in kem.cancellations} == {
        "MOON_ASSOCIATED_WITH_A_PLANET",
        "PLANET_IN_KENDRA_FROM_MOON",
    }
    ours = {
        e.exception_id.rsplit(".", 1)[1]
        for e in content.exceptions
        if e.affected_rule_id == "PHALADEEPIKA_SASTRI_KEMADRUMA_6_5"
    }
    assert ours == {"MOON_ASSOCIATED_WITH_A_PLANET", "PLANET_IN_KENDRA_FROM_MOON"}
    for e in content.exceptions:
        if e.affected_rule_id.startswith("BPHS_SAN_NABHASA_35_"):
            rule = ruleset.rules[e.affected_rule_id]
            assert {c.cancellation_id for c in rule.cancellations} == {
                "EARLIER_NABHASA_YOGA_DERIVABLE"
            }


def test_the_evidence_bundle_gained_no_knowledge_section() -> None:
    bundle = pytest.importorskip("pandit_rule_engine.bundle")
    assert list(bundle.EvidenceBundle.model_fields) == PHASE11_BUNDLE_FIELDS
    assert not [f for f in bundle.EvidenceBundle.model_fields if "knowledge" in f]


def test_strength_profile_ids_exist_in_the_astro_engine() -> None:
    shadbala = pytest.importorskip("pandit_astro_engine.shadbala.profiles")
    assert shadbala.PROFILE_ID == "SHADBALA_BPHS_SANTHANAM_27_VERSE"
    assert shadbala.RAMAN_PROFILE_ID == "SHADBALA_RAMAN_GRAHA_BHAVA_BALAS"


def test_tarot_corpus_matches_the_phase9_deck(content: KnowledgeContent) -> None:
    deck = pytest.importorskip("pandit_astro_engine.tarot.deck")
    refs = {
        u.external_ref for u in content.chunk_units if u.methodology_profile.startswith("TAROT")
    }
    assert refs == set(deck.CARDS_BY_ID)
    assert len(refs) == 78
    assert {u.methodology_profile for u in content.chunk_units if u.external_ref in refs} == {
        deck.WAITE_SMITH_DECK_ID
    }


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for py in path.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("service", ["astro-engine", "rule-engine"])
def test_calculation_and_rule_services_never_import_the_knowledge_package(service: str) -> None:
    src = REPO / "services" / service / "src"
    assert src.is_dir()
    assert "pandit_knowledge" not in _imports(src), service


def test_the_server_only_composes_the_knowledge_health_check() -> None:
    """ADR-007: the server composes each service's ``get_health`` and nothing else."""
    imported: set[str] = set()
    for py in (REPO / "server" / "src").rglob("*.py"):
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module == "pandit_knowledge":
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                assert all(a.name.split(".")[0] != "pandit_knowledge" for a in node.names)
    assert imported <= {"get_health"}


def test_knowledge_package_never_imports_calculation_or_rule_code() -> None:
    src = Path(__file__).resolve().parents[1] / "src" / "pandit_knowledge"
    names = _imports(src)
    assert "pandit_astro_engine" not in names
    assert "pandit_rule_engine" not in names
    assert "pandit_agent" not in names and "pandit_verification" not in names


def test_knowledge_package_has_no_http_surface() -> None:
    src = Path(__file__).resolve().parents[1] / "src" / "pandit_knowledge"
    names = _imports(src)
    assert not names & {"fastapi", "starlette", "flask", "aiohttp", "requests", "httpx", "uvicorn"}
