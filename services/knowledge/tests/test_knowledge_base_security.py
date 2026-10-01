"""Structured access, privacy and the chart-fact boundary (KB-26, KB-27 to KB-34, KB-37)."""

from __future__ import annotations

import pytest

from pandit_knowledge.content import KnowledgeContent
from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import BuildResult
from pandit_knowledge.knowledge_base import KnowledgeBase
from pandit_knowledge.models import StatementKind, SupportStatus
from pandit_knowledge.store import InMemoryKnowledgeStore
from pandit_knowledge.validation import find_personal_data, personal_data_findings

Built = tuple[InMemoryKnowledgeStore, BuildResult, HashingEmbeddingProvider]


def _kb(built: Built) -> KnowledgeBase:
    return KnowledgeBase(built[0], built[1].version_id)


def test_knowledge_base_reads_sealed_versions_only(
    content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    from pandit_knowledge.ingestion import KnowledgeBuilder

    store = InMemoryKnowledgeStore()
    manifest, _ = KnowledgeBuilder(store, provider).manifest_for(content)
    store.register_embedding_config(provider.config)
    version, _ = store.begin_version(manifest)
    with pytest.raises(ValueError, match="sealed"):
        KnowledgeBase(store, version.version_id)
    with pytest.raises(KeyError):
        KnowledgeBase(store, "KV-none")


def test_planet_statements_keep_one_row_per_source_profile(built: Built) -> None:
    kb = _kb(built)
    sig = kb.statements("PLANET.MERCURY", StatementKind.SIGNIFICATION)
    assert {s.profile_id for s in sig} == {
        "KB_BPHS_SAN_PLANET_KARAKATWA_3_12_13",
        "KB_BJ_SASTRI_PLANET_KARAKATWA_2_1",
        "KB_PHALA_SASTRI_PLANET_KARAKATWA_XV_15_16",
    }
    by_profile = {s.profile_id: [i["id"] for i in s.attributes["items"]] for s in sig}
    assert by_profile["KB_BPHS_SAN_PLANET_KARAKATWA_3_12_13"] == ["SIG.SPEECH"]
    assert "SIG.LEARNING" in by_profile["KB_PHALA_SASTRI_PLANET_KARAKATWA_XV_15_16"]
    one = kb.statements("PLANET.MERCURY", profile_id="KB_BJ_SASTRI_PLANET_KARAKATWA_2_1")
    assert len(one) == 1 and one[0].edition_id == "BRIHAT_JATAKA_SASTRI"
    assert one[0].reading_level.value == "OCR_LEVEL"


def test_rahu_and_ketu_roles_and_phaladeepika_only_significations(built: Built) -> None:
    kb = _kb(built)
    assert {s.profile_id for s in kb.statements("PLANET.RAHU", StatementKind.SIGNIFICATION)} == {
        "KB_PHALA_SASTRI_PLANET_KARAKATWA_XV_15_16"
    }
    role = kb.statements("PLANET.KETU", StatementKind.ROLE)[0]
    assert role.attributes["items"][0]["id"] == "ROLE.PLANETARY_ARMY"


def test_house_statements_and_conflict(built: Built) -> None:
    kb = _kb(built)
    sig = kb.statements("HOUSE.10", StatementKind.SIGNIFICATION)
    assert len(sig) == 1
    assert "SIG.PROFESSION_LIVELIHOOD" in [i["id"] for i in sig[0].attributes["items"]]
    assert sig[0].confidence.value == "HIGH" and sig[0].reading_level.value == "PAGE_IMAGE_LEVEL"
    conflicts = kb.statements("HOUSE.02", StatementKind.SOURCE_VARIANCE)
    assert len(conflicts) == 1 and conflicts[0].support_status is SupportStatus.UNRESOLVED_CONFLICT


def test_domain_mapping_queries(built: Built) -> None:
    kb = _kb(built)
    career = {m.concept_id: m for m in kb.domain_mappings("DOMAIN.CAREER")}
    assert len(career) == 12
    assert career["HOUSE.10"].support_status is SupportStatus.SOURCE_SUPPORTED
    assert career["HOUSE.07"].support_status is SupportStatus.NOT_EVALUABLE
    for_house_5 = {m.domain_id: m.support_status for m in kb.domain_mappings(house_id="HOUSE.05")}
    assert for_house_5["DOMAIN.EDUCATION"] is SupportStatus.SOURCE_SUPPORTED
    assert for_house_5["DOMAIN.CAREER"] is SupportStatus.NOT_EVALUABLE


def test_rule_references_point_at_rules_and_do_not_copy_them(built: Built) -> None:
    kb = _kb(built)
    refs = kb.rule_references("PLANET.MOON")
    ids = {r.rule_id for r in refs}
    assert "PHALADEEPIKA_SASTRI_KEMADRUMA_6_5" in ids and "BPHS_SAN_REL_NATURAL_3_55" in ids
    for r in refs:
        assert set(r.model_dump()) == {
            "reference_id", "concept_id", "rule_id", "rule_kind", "relation", "profile_id",
            "source_location",
        }  # fmt: skip
    strength = {r.rule_id for r in kb.rule_references("CONCEPT.STRENGTH")}
    assert strength == {"SHADBALA_RAMAN_GRAHA_BHAVA_BALAS", "SHADBALA_BPHS_SANTHANAM_27_VERSE"}


def test_exceptions_by_rule(built: Built) -> None:
    kb = _kb(built)
    assert len(kb.exceptions("PHALADEEPIKA_SASTRI_KEMADRUMA_6_5")) == 2
    assert kb.exceptions("BPHS_SAN_KEMADRUMA_37_11_13") == []
    assert len(kb.exceptions("BPHS_SAN_NABHASA_35_GOLA")) == 1
    assert len(kb.exceptions()) == 10


def test_terms_by_concept(built: Built) -> None:
    kb = _kb(built)
    terms = kb.terms("PLANET.JUPITER")
    langs = {t.language for t in terms}
    assert langs == {"en", "sa", "sa-Latn"}
    assert {t.text for t in terms if t.language == "en"} == {"Jupiter"}
    assert not [t for t in terms if t.language.startswith("hi")]


def test_concept_lookup(built: Built) -> None:
    kb = _kb(built)
    assert kb.concept("HOUSE.03").concept_type.value == "HOUSE"
    with pytest.raises(KeyError):
        kb.concept("HOUSE.13")
    assert len(kb.concepts("PLANET")) == 9
    assert len(kb.concepts("TAROT_CARD")) == 78


# ---- privacy and the chart-fact boundary ----------------------------------------------------
@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("write to asha@example.com", "EMAIL"),
        ("call +91 98765 43210 now", "PHONE_LIKE"),
        ("born 14/03/1990", "NUMERIC_DATE"),
        ("born 1990-03-14", "NUMERIC_DATE"),
        ("at 18.520430, 73.856743", "COORDINATES"),
        ("postgres://user:secret@host/db", "URL_CREDENTIALS"),
    ],
)
def test_personal_data_patterns_are_detected(text: str, label: str) -> None:
    assert label in find_personal_data(text)


def test_ordinary_corpus_text_is_clean() -> None:
    assert (
        find_personal_data("The Magician. Skill, diplomacy, address, subtlety; the Querent.") == []
    )
    assert find_personal_data("Ch. 11 v. 2-13 (printed pp. 121-123)") == []


def test_content_and_stored_rows_hold_no_personal_data(
    content: KnowledgeContent, built: Built
) -> None:
    assert personal_data_findings(content) == []
    store, result, _ = built
    for table in ("chunks", "statements", "terms", "exceptions", "domain_mappings", "sources"):
        for row in store.select_rows(result.version_id, table):
            text = repr({k: v for k, v in row.items() if not k.endswith(("hash", "_id"))})
            assert find_personal_data(text) == [], (table, row.get("content_hash"))


def test_the_knowledge_base_has_no_chart_or_user_tables(built: Built) -> None:
    store, result, _ = built
    from pandit_knowledge.schema import VERSIONED_TABLES

    banned = {"birth", "chart", "user", "profile", "person", "dob", "latitude", "longitude"}
    for name, spec in VERSIONED_TABLES.items():
        assert not any(b in name for b in banned), name
        for column in spec.columns:
            assert not any(b in column for b in ("birth", "dob", "latitude", "longitude")), column
    assert store.get_version(result.version_id) is not None


def test_no_chunk_reads_like_a_statement_about_a_user(content: KnowledgeContent) -> None:
    from pandit_knowledge.content import all_chunks

    for chunk in all_chunks(content):
        low = chunk.text.lower()
        assert "your chart" not in low and "your horoscope" not in low and "your birth" not in low
