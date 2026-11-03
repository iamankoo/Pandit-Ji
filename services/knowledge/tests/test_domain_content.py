"""Phase 17: the life-domain knowledge version, mappings, provenance and boundaries (ADR-012)."""

from __future__ import annotations

import re
from collections import Counter

import pytest
from pandit_contracts.domain import LifeDomain

from pandit_knowledge.content import KnowledgeContent, load_content
from pandit_knowledge.domain_content import (
    DOMAIN_KNOWLEDGE_STANDARDS_VERSION,
    load_domain_content,
)
from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import KnowledgeBuilder
from pandit_knowledge.models import (
    ConceptType,
    RuleKind,
    StatementKind,
    SupportStatus,
)
from pandit_knowledge.palm_content import PALM_KNOWLEDGE_STANDARDS_VERSION, load_palm_content
from pandit_knowledge.store import InMemoryKnowledgeStore
from pandit_knowledge.validation import verify_version

PHASE12_VERSION = "KV-06361d7aba28c1ce"
PALM_VERSION = "KV-a21c2c040abe9663"
LOCKED_VARGAS = {2: "WEALTH", 3: "SIBLINGS", 7: "CHILDREN", 9: "MARRIAGE", 10: "CAREER"}


@pytest.fixture(scope="module")
def domain() -> KnowledgeContent:
    return load_domain_content()


def _build(content: KnowledgeContent, standards: str = DOMAIN_KNOWLEDGE_STANDARDS_VERSION):  # type: ignore[no-untyped-def]
    store = InMemoryKnowledgeStore()
    return store, KnowledgeBuilder(store, HashingEmbeddingProvider(), standards).build(content)


# ---- a separate, additive, deterministic version -----------------------------------------------


def test_the_domain_version_is_separate_from_phase_12_and_phase_13(
    domain: KnowledgeContent,
) -> None:
    _, built = _build(domain)
    phase12 = KnowledgeBuilder(InMemoryKnowledgeStore(), HashingEmbeddingProvider()).build(
        load_content()
    )
    palm = KnowledgeBuilder(
        InMemoryKnowledgeStore(), HashingEmbeddingProvider(), PALM_KNOWLEDGE_STANDARDS_VERSION
    ).build(load_palm_content().knowledge)
    assert phase12.version_id == PHASE12_VERSION  # unchanged by Phase 17
    assert palm.version_id == PALM_VERSION  # unchanged by Phase 17
    assert built.version_id not in {PHASE12_VERSION, PALM_VERSION}
    assert built.snapshot_hash not in {phase12.snapshot_hash, palm.snapshot_hash}


def test_the_domain_version_is_deterministic_sealed_and_intact(domain: KnowledgeContent) -> None:
    store, built = _build(domain)
    _, again = _build(load_domain_content())
    assert (built.version_id, built.snapshot_hash) == (again.version_id, again.snapshot_hash)
    assert re.fullmatch(r"KV-[0-9a-f]{16}", built.version_id)
    version = store.get_version(built.version_id)
    assert version is not None and version.status == "SEALED"
    assert version.manifest.standards_version == DOMAIN_KNOWLEDGE_STANDARDS_VERSION == "1.30.0"
    assert verify_version(store, built.version_id) == []


def test_the_domain_version_has_no_chunks_and_no_prose(domain: KnowledgeContent) -> None:
    assert domain.chunk_units == []
    _, built = _build(domain)
    assert built.outcome == "CREATED"


# ---- the taxonomy: 27 + 9, individually addressable, no inherited support -----------------------


def test_every_domain_has_exactly_one_definition(domain: KnowledgeContent) -> None:
    definitions = [
        s for s in domain.statements if s.statement_kind is StatementKind.DOMAIN_DEFINITION
    ]
    assert len(definitions) == 36 == len(LifeDomain)
    assert {d.concept_id for d in definitions} == {f"DOMAIN.{d.value}" for d in LifeDomain}
    assert len({m.mapping_id for m in domain.domain_mappings}) == len(domain.domain_mappings)
    mapped = {m.domain_id for m in domain.domain_mappings}
    assert mapped <= {f"DOMAIN.{d.value}" for d in LifeDomain}


def _definitions(domain: KnowledgeContent) -> dict[str, dict[str, object]]:
    return {
        s.concept_id: s.attributes
        for s in domain.statements
        if s.statement_kind is StatementKind.DOMAIN_DEFINITION
    }


def test_the_research_classification_of_the_27_is_not_upgraded(domain: KnowledgeContent) -> None:
    status = {k: v["research_support"] for k, v in _definitions(domain).items()}
    source = {"EDUCATION", "CAREER", "FINANCE", "WEALTH", "MARRIAGE", "FAMILY", "CHILDREN"}
    partial = {
        "PERSONALITY", "SUBJECTS", "JOB", "BUSINESS", "LOVE", "RELATIONSHIP", "SPOUSE",
        "TRAVEL", "FOREIGN_TRAVEL", "FOREIGN_SETTLEMENT", "SPIRITUALITY",
    }  # fmt: skip
    none = {
        "BIRTH", "CHILDHOOD", "SCHOOL", "COLLEGE", "CORPORATE_LIFE", "STARTUP", "GF_BF",
        "FOREIGN_EDUCATION", "PERSONAL_LIFE",
    }  # fmt: skip
    for name in source:
        assert status[f"DOMAIN.{name}"] == "SOURCE_SUPPORTED"
    for name in partial:
        assert status[f"DOMAIN.{name}"] == "PARTIALLY_SUPPORTED"
    for name in none:
        assert status[f"DOMAIN.{name}"] == "NOT_EVALUABLE"
    assert len(source | partial | none) == 27


def test_no_domain_inherits_support_from_its_parent(domain: KnowledgeContent) -> None:
    definitions = _definitions(domain)
    assert all(d["support_inherited_from_parent"] is False for d in definitions.values())
    for name in ("JOB", "SCHOOL", "GF_BF"):
        parent = definitions[f"DOMAIN.{name}"]["parent"]
        assert parent is not None
    assert definitions["DOMAIN.JOB"]["research_support"] != "SOURCE_SUPPORTED"
    assert definitions["DOMAIN.SCHOOL"]["research_support"] == "NOT_EVALUABLE"
    assert definitions["DOMAIN.GF_BF"]["research_support"] == "NOT_EVALUABLE"


def test_unsupported_domains_carry_no_rules_or_supporting_statements(
    domain: KnowledgeContent,
) -> None:
    definitions = _definitions(domain)
    by_domain = Counter(
        r.concept_id for r in domain.rule_references if r.rule_kind is RuleKind.DOMAIN_RULE
    )
    for concept, attrs in definitions.items():
        if attrs["research_support"] == "NOT_EVALUABLE":
            assert attrs["has_approved_mappings"] is False
            assert by_domain[concept] == 0
    for m in domain.domain_mappings:
        if m.support_status is SupportStatus.NOT_EVALUABLE and m.mapping_id.endswith(".DOMAIN"):
            assert m.supporting_statement_ids == ()


def test_every_supporting_statement_of_a_mapping_exists(domain: KnowledgeContent) -> None:
    statements = {s.statement_id for s in domain.statements}
    for mapping in domain.domain_mappings:
        assert set(mapping.supporting_statement_ids) <= statements


# ---- provenance on every mapping ---------------------------------------------------------------


def test_every_supporting_statement_has_provenance(domain: KnowledgeContent) -> None:
    editions = {e.edition_id for e in domain.editions}
    for s in domain.statements:
        assert s.profile_id and s.source_location and s.edition_id in editions
        assert s.registry_verification_level
        assert s.confidence is not None and s.support_status is not None


def test_every_domain_rule_reference_points_at_a_mapping_with_a_profile(
    domain: KnowledgeContent,
) -> None:
    mappings = {m.mapping_id: m for m in domain.domain_mappings}
    refs = [r for r in domain.rule_references if r.rule_kind is RuleKind.DOMAIN_RULE]
    assert len(refs) == 108
    for ref in refs:
        mapping_id = ref.relation.split(":", 1)[1]
        assert mapping_id in mappings
        assert ref.source_location and ref.profile_id
        assert ref.rule_id.startswith("DOM_")


def test_phase_6_rule_references_point_only_at_real_phase_6_rules(domain: KnowledgeContent) -> None:
    from pandit_knowledge.content import DEFAULT_RULES_DIR, rule_index

    ids, _ = rule_index(DEFAULT_RULES_DIR)
    assert sum(1 for kind in ids.values() if kind == "RULE") == 51
    assert domain.rules_snapshot_hash
    for ref in domain.rule_references:
        if ref.rule_kind is RuleKind.RULE:
            assert ref.rule_id in ids


# ---- varga: only the locked BPHS mappings ------------------------------------------------------


def test_varga_use_statements_map_only_the_locked_domains(domain: KnowledgeContent) -> None:
    uses = [s for s in domain.statements if s.statement_kind is StatementKind.VARGA_USE]
    mapped: dict[str, set[str]] = {}
    for s in uses:
        term = s.attributes["source_term"]
        for name in s.attributes["mapped_domains"]:
            mapped.setdefault(name, set()).add(term)
    allowed = {
        "WEALTH", "FINANCE", "SIBLINGS", "CHILDREN", "MARRIAGE", "SPOUSE", "CAREER", "PARENTS",
        "SPIRITUALITY", "EDUCATION",
    }  # fmt: skip
    assert set(mapped) <= allowed
    # D4 'fortunes' is not property and not foreign settlement.
    for name in ("FOREIGN_SETTLEMENT", "PERSONAL_LIFE", "FAMILY"):
        assert name not in mapped
    assert not any("Chaturthamsa" in t for terms in mapped.values() for t in terms)


def test_d10_keeps_the_source_wording_power_and_position(domain: KnowledgeContent) -> None:
    uses = [s for s in domain.statements if s.statement_kind is StatementKind.VARGA_USE]
    d10 = [s for s in uses if "CAREER" in s.attributes["mapped_domains"]]
    assert d10
    assert all("power" in s.attributes["source_term"].lower() for s in d10)


# ---- conflicts and policy are preserved --------------------------------------------------------


def test_source_variance_statements_keep_both_profiles_and_resolve_nothing(
    domain: KnowledgeContent,
) -> None:
    variance = [s for s in domain.statements if s.statement_kind is StatementKind.SOURCE_VARIANCE]
    assert {s.attributes["conflict_id"] for s in variance} >= {
        "DC-01", "DC-02", "DC-03", "DC-04", "DC-05",
    }  # fmt: skip
    for s in variance:
        assert len(s.attributes["profiles"]) >= 2
        assert s.attributes["resolution"] == "NONE"
    conflicted = [
        m for m in domain.domain_mappings if m.support_status is SupportStatus.UNRESOLVED_CONFLICT
    ]
    assert conflicted


def test_policy_notes_exist_for_children_finance_and_longevity(domain: KnowledgeContent) -> None:
    notes = [s for s in domain.statements if s.statement_kind is StatementKind.POLICY_NOTE]
    blob = " ".join(str(s.attributes) for s in notes)
    assert "CHILDREN_STRUCTURAL_ONLY" in blob
    assert "FINANCE_INTERPRETIVE_ONLY" in blob
    assert "LIFESPAN_BLOCKED" in blob


def test_withheld_historical_text_is_never_stored_verbatim(domain: KnowledgeContent) -> None:
    for s in domain.statements:
        if s.statement_kind is StatementKind.POLICY_NOTE:
            for value in s.attributes.values():
                if isinstance(value, str):
                    assert len(value) <= 120


def test_no_vastu_and_no_report_content_exists(domain: KnowledgeContent) -> None:
    blob = " ".join(
        [c.canonical_key for c in domain.concepts] + [m.mapping_id for m in domain.domain_mappings]
    ).lower()
    assert "vastu" not in blob and "report" not in blob


def test_concept_types_are_the_expected_vocabulary(domain: KnowledgeContent) -> None:
    kinds = {c.concept_type for c in domain.concepts}
    assert ConceptType.DOMAIN in kinds
    assert all(isinstance(k, ConceptType) for k in kinds)


# ---- cross-package consistency: the rule-engine ruleset == the knowledge mappings ----------------


def test_the_rule_engine_ruleset_and_the_knowledge_mappings_agree(domain: KnowledgeContent) -> None:
    from pathlib import Path

    load_domain_ruleset = pytest.importorskip("pandit_rule_engine.domain").load_domain_ruleset

    rules_dir = Path(__file__).resolve().parents[2] / "rule-engine" / "domain_rules"
    ruleset = load_domain_ruleset(rules_dir)
    mappings = {m.mapping_id: m for m in domain.domain_mappings}
    refs = {r.rule_id: r for r in domain.rule_references if r.rule_kind is RuleKind.DOMAIN_RULE}
    assert set(refs) == set(ruleset.rules)
    for rule_id, rule in ruleset.rules.items():
        ref = refs[rule_id]
        assert ref.relation == f"EXECUTES_MAPPING:{rule.mapping_id}"
        assert ref.profile_id == rule.profile
        if rule.kind.value != "PHASE6_RULE_APPLICABILITY":
            assert ref.source_location == rule.source_location
        mapping = mappings[rule.mapping_id]
        assert mapping.domain_id == f"DOMAIN.{rule.domain.value}"
        assert mapping.support_status.value == rule.support.value
        assert mapping.profile_id == rule.profile
