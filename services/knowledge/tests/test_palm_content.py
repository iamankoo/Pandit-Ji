"""Phase 13: the palmistry knowledge version, its coverage manifest and its boundaries."""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path

import pytest
import yaml
from pandit_contracts.palm_coverage import BACKING_STATUSES, CoverageStatus

from pandit_knowledge.content import DEFAULT_RULES_DIR, load_content, rule_index
from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import KnowledgeBuilder
from pandit_knowledge.models import (
    ConceptType,
    KnowledgeDomain,
    RuleKind,
    StatementKind,
    SupportStatus,
    TextOrigin,
)
from pandit_knowledge.palm_content import (
    DEFAULT_PALM_CONTENT_DIR,
    PALM_KNOWLEDGE_STANDARDS_VERSION,
    PalmContentError,
    PalmKnowledgeContent,
    load_palm_content,
)
from pandit_knowledge.store import InMemoryKnowledgeStore
from pandit_knowledge.validation import verify_version

REGISTRY = Path(__file__).resolve().parents[3] / "research" / "ASTROLOGY_SOURCES.md"
# The Phase 12 knowledge version (unchanged by Phase 13) and its snapshot.
PHASE12_VERSION = "KV-06361d7aba28c1ce"


@pytest.fixture(scope="module")
def palm() -> PalmKnowledgeContent:
    return load_palm_content()


def _build(palm: PalmKnowledgeContent) -> tuple[InMemoryKnowledgeStore, str, str]:
    store = InMemoryKnowledgeStore()
    result = KnowledgeBuilder(
        store, HashingEmbeddingProvider(), PALM_KNOWLEDGE_STANDARDS_VERSION
    ).build(palm.knowledge)
    return store, result.version_id, result.snapshot_hash


# ---- a separate, additive knowledge version --------------------------------------------------
def test_palm_knowledge_is_a_separate_version_from_phase_12(palm: PalmKnowledgeContent) -> None:
    _, palm_version, palm_hash = _build(palm)
    phase12 = KnowledgeBuilder(InMemoryKnowledgeStore(), HashingEmbeddingProvider()).build(
        load_content()
    )
    assert phase12.version_id == PHASE12_VERSION  # unchanged by Phase 13
    assert palm_version != PHASE12_VERSION and palm_hash != phase12.snapshot_hash


def test_the_palm_version_is_deterministic_sealed_and_intact(palm: PalmKnowledgeContent) -> None:
    store, version_id, snapshot = _build(palm)
    _, again_id, again_snapshot = _build(palm)
    assert (version_id, snapshot) == (again_id, again_snapshot)
    version = store.get_version(version_id)
    assert version is not None and version.status == "SEALED"
    assert version.manifest.standards_version == "1.28.0"
    assert verify_version(store, version_id) == []


def test_the_phase_12_content_loader_never_reads_the_palm_directory() -> None:
    content = load_content()
    assert not [c for c in content.concepts if c.concept_id.startswith("PALM_")]
    assert all(s.source_id != "SRC-HERONALLEN-CHEIROSOPHY" for s in content.sources)
    assert KnowledgeDomain.PALMISTRY not in {u.knowledge_domain for u in content.chunk_units}


def test_the_phase_6_rule_files_are_not_touched_by_palm_knowledge() -> None:
    """Palm knowledge holds rule *references* only; the Phase 6 rules directory has no palm file."""
    assert not [p for p in DEFAULT_RULES_DIR.rglob("*") if "palm" in p.name.lower()]
    assert rule_index(DEFAULT_RULES_DIR)[1] == (
        "245326144f9933e9b3f758e0bbf603d8afedca5a852c1091bd945dfb88d1a736"
    )


# ---- vocabulary and structure ------------------------------------------------------------------
def test_palm_content_uses_the_palm_vocabulary(palm: PalmKnowledgeContent) -> None:
    k = palm.knowledge
    assert {c.concept_type for c in k.concepts} == {
        ConceptType.PALM_LINE,
        ConceptType.PALM_REGION,
        ConceptType.PALM_FEATURE,
    }
    assert {u.knowledge_domain for u in k.chunk_units} == {KnowledgeDomain.PALMISTRY}
    assert {r.rule_kind for r in k.rule_references} == {RuleKind.PALM_RULE}
    kinds = {s.statement_kind for s in k.statements}
    assert {
        StatementKind.LOCATION_DEFINITION,
        StatementKind.READING_CONVENTION,
        StatementKind.SIGNIFICATION,
        StatementKind.SOURCE_VARIANCE,
        StatementKind.COVERAGE,
    } == kinds
    assert all(u.text_origin is TextOrigin.PROJECT_RENDERING for u in k.chunk_units)


def test_every_statement_is_profile_specific_and_every_source_is_registered(
    palm: PalmKnowledgeContent,
) -> None:
    registry = REGISTRY.read_text(encoding="utf-8")
    for source in palm.knowledge.sources:
        assert source.registry_ref in registry, source.source_id
    profiles = {s.profile_id for s in palm.knowledge.statements}
    profiles |= {t.profile_id for t in palm.knowledge.terms}
    section = registry[registry.index("### 6.11 Phase 13 palmistry profile IDs") :]
    for profile in profiles:
        if profile.startswith("PALM_CROSS_SOURCE"):
            continue
        assert f"`{profile}`" in section or profile in section, profile


def test_source_variances_are_recorded_and_no_winner_is_chosen(palm: PalmKnowledgeContent) -> None:
    variances = [
        s for s in palm.knowledge.statements if s.statement_kind is StatementKind.SOURCE_VARIANCE
    ]
    assert len(variances) == 7
    for v in variances:
        assert v.support_status is SupportStatus.UNRESOLVED_CONFLICT
        assert v.attributes["resolved"] is False and v.attributes["winner"] is None
        assert len(v.attributes["profiles"]) >= 2
    concepts = {v.concept_id for v in variances}
    assert "PALM_LINE.MERCURY_LINE_VARIANT" in concepts and "PALM_REGION.MOUNT_MARS" in concepts


def test_statements_are_never_merged_across_profiles(palm: PalmKnowledgeContent) -> None:
    by_key = Counter(
        (s.concept_id, s.statement_kind, s.profile_id)
        for s in palm.knowledge.statements
        if s.statement_kind is not StatementKind.COVERAGE
    )
    assert max(by_key.values()) == 1
    mercury = [
        s.profile_id
        for s in palm.knowledge.statements
        if s.concept_id == "PALM_LINE.MERCURY_LINE_VARIANT"
        and s.statement_kind is StatementKind.LOCATION_DEFINITION
    ]
    assert len(set(mercury)) == len(mercury) == 3  # three profiles, three statements, no merge


# ---- the source coverage manifest -------------------------------------------------------------
def test_the_manifest_is_part_of_the_version(palm: PalmKnowledgeContent) -> None:
    coverage = [s for s in palm.knowledge.statements if s.statement_kind is StatementKind.COVERAGE]
    assert len(coverage) == len(palm.coverage.records)
    for stmt, rec in zip(coverage, palm.coverage.records, strict=True):
        assert stmt.attributes["coverage_status"] == rec.status.value
        assert stmt.attributes["read"] is rec.read


def test_unread_and_excluded_concepts_back_nothing(palm: PalmKnowledgeContent) -> None:
    statuses = {r.status for r in palm.coverage.records}
    assert {
        CoverageStatus.SUPPORTED,
        CoverageStatus.PARTIALLY_SUPPORTED,
        CoverageStatus.NOT_READ,
        CoverageStatus.NOT_EVALUABLE,
        CoverageStatus.EXCLUDED_BY_POLICY,
        CoverageStatus.RESEARCH_PENDING,
    } <= statuses
    for rec in palm.coverage.records:
        if rec.status not in BACKING_STATUSES:
            assert (
                palm.coverage.problems_for_rule(rec.profile_id, rec.location, [rec.concept_id])
                != ()
            ), rec.concept_id
    for rec in palm.coverage.records:
        if rec.status is CoverageStatus.NOT_READ:
            assert rec.read is False


@pytest.mark.parametrize(
    "concept",
    [
        "PALM_FEATURE.THUMB",
        "PALM_FEATURE.NAILS",
        "PALM_FEATURE.HAND_COLOUR_TEXTURE",
        "PALM_FEATURE.MOUNT_INTERPRETATIONS",
        "PALM_FEATURE.OTHER_SIGNS",
    ],
)
def test_unread_concepts_have_no_statement_but_their_coverage(
    palm: PalmKnowledgeContent, concept: str
) -> None:
    statements = [s for s in palm.knowledge.statements if s.concept_id == concept]
    assert statements and all(s.statement_kind is StatementKind.COVERAGE for s in statements)
    assert all(s.attributes["coverage_status"] == "NOT_READ" for s in statements)
    assert all(s.support_status is SupportStatus.NOT_EVALUABLE for s in statements)


def test_mount_development_and_the_hand_shape_are_not_evaluable(
    palm: PalmKnowledgeContent,
) -> None:
    for concept in ("PALM_FEATURE.MOUNT_DEVELOPMENT", "PALM_FEATURE.HAND_SHAPE"):
        assert palm.coverage.status_of(concept) == (CoverageStatus.NOT_EVALUABLE,)


def test_the_indian_profile_is_research_pending_with_no_statement(
    palm: PalmKnowledgeContent,
) -> None:
    indian = [
        s
        for s in palm.knowledge.statements
        if s.attributes.get("methodology_profile") == "PALM_INDIAN_HASTA_SAMUDRIKA"
    ]
    assert len(indian) == 1 and indian[0].statement_kind is StatementKind.COVERAGE
    assert indian[0].attributes["coverage_status"] == "RESEARCH_PENDING"
    assert indian[0].support_status is SupportStatus.NOT_EVALUABLE
    western = {
        s.attributes["methodology_profile"]
        for s in palm.knowledge.statements
        if s.statement_kind is not StatementKind.COVERAGE
    }
    assert western == {"PALM_WESTERN"}  # the traditions are never merged


# ---- the load-time guards ----------------------------------------------------------------------
def _copy(tmp_path: Path) -> Path:
    target = tmp_path / "palm"
    shutil.copytree(DEFAULT_PALM_CONTENT_DIR, target)
    return target


def test_a_statement_not_backed_by_the_manifest_cannot_be_loaded(tmp_path: Path) -> None:
    content = _copy(tmp_path)
    path = content / "statements.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["statements"].append(
        {
            "concept": "PALM_FEATURE.THUMB",
            "kind": "SIGNIFICATION",
            "profile": "PALM_HA_UNREAD",
            "edition": "ED.HERONALLEN_TENTH_ARCHIVE_UC",
            "location": "pp. 116-121",
            "location_kind": "page",
            "reading_level": "OCR_LEVEL",
            "verification": "OCR-ORIGINAL-ENGLISH",
            "confidence": "LOW",
            "support": "SOURCE_SUPPORTED",
            "tags": ["WILL_POWER_INDICATED"],
        }
    )
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(PalmContentError, match="not backed"):
        load_palm_content(content)


@pytest.mark.parametrize(
    "tag", ["DISEASE_RISK", "SHORT_LIFESPAN", "CRIMINAL_TENDENCY", "FERTILITY_SIGN"]
)
def test_a_prohibited_tag_cannot_be_loaded(tmp_path: Path, tag: str) -> None:
    content = _copy(tmp_path)
    path = content / "statements.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["statements"][0]["tags"].append(tag)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(PalmContentError, match="prohibited"):
        load_palm_content(content)


def test_an_indian_statement_cannot_be_loaded(tmp_path: Path) -> None:
    content = _copy(tmp_path)
    path = content / "source_coverage.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["records"][-1]["status"] = "SUPPORTED"
    data["records"][-1]["read"] = True
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_palm_content(content)


def test_no_palm_file_lives_in_the_phase_6_rules_or_the_phase_12_content_root() -> None:
    content_root = DEFAULT_PALM_CONTENT_DIR.parent
    assert {p.name for p in content_root.iterdir()} >= {"palm", "planets.yaml", "sources.yaml"}
    assert not [
        p for p in content_root.glob("*.yaml") if "palm" in p.read_text(encoding="utf-8").lower()
    ]
