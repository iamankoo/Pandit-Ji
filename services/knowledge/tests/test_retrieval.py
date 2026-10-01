"""Retrieval: filters, provenance, bounds, determinism, language behaviour (KB-24 to KB-26)."""

from __future__ import annotations

import pytest

from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import BuildResult, KnowledgeBuilder
from pandit_knowledge.models import (
    MAX_TOP_K,
    KnowledgeDomain,
    RetrievalFilters,
    RetrievalHit,
    RetrievalQuery,
    TextOrigin,
)
from pandit_knowledge.retrieval import RetrievalError, Retriever
from pandit_knowledge.store import InMemoryKnowledgeStore

Built = tuple[InMemoryKnowledgeStore, BuildResult, HashingEmbeddingProvider]


def _retriever(built: Built) -> Retriever:
    store, _, provider = built
    return Retriever(store, provider)


def test_retrieval_returns_the_right_house_with_full_provenance(built: Built) -> None:
    result = _retriever(built).retrieve(RetrievalQuery(text="profession livelihood", top_k=3))
    top = result.hits[0]
    assert top.parent_concept_id == "HOUSE.10"
    assert top.source_id == "SRC.BPHS" and top.edition_id == "BPHS_SANTHANAM_1984"
    assert "Ch. 11" in top.source_location
    assert top.methodology_profile
    assert top.language == "en"
    assert top.knowledge_version_id == built[1].version_id
    assert top.embedding_config_id == built[2].config.embedding_config_id
    assert top.metric == "cosine" and 0.0 <= top.distance < 1.0
    assert top.text_origin is TextOrigin.PROJECT_RENDERING
    assert len(top.content_hash) == 64 and top.chunk_id.startswith("CH-")
    assert top.rank == 1


def test_every_hit_is_stamped_as_not_a_chart_fact(built: Built) -> None:
    result = _retriever(built).retrieve(RetrievalQuery(text="Moon significator", top_k=10))
    assert result.hits
    for hit in result.hits:
        assert hit.authority == "KNOWLEDGE_TEXT_NOT_A_CHART_FACT"
    assert "authority" in RetrievalHit.model_fields
    # the field cannot be set to anything else
    with pytest.raises(ValueError):
        RetrievalHit.model_validate({**result.hits[0].model_dump(), "authority": "CHART_FACT"})


def test_hit_has_no_field_that_could_carry_a_chart_fact() -> None:
    allowed = {
        "rank", "chunk_id", "distance", "metric", "knowledge_version_id", "embedding_config_id",
        "is_semantic", "knowledge_domain", "source_id", "edition_id", "source_location",
        "section_path", "methodology_profile", "language", "text_origin", "text_fidelity",
        "reading_level", "confidence", "parent_concept_id", "content_hash", "text", "authority",
    }  # fmt: skip
    assert set(RetrievalHit.model_fields) == allowed


def test_source_filter(built: Built) -> None:
    result = _retriever(built).retrieve(
        RetrievalQuery(
            text="marriage wife",
            top_k=20,
            max_distance=1.0,
            filters=RetrievalFilters(source_ids=("SRC.PHALADEEPIKA",)),
        )
    )
    assert result.hits
    assert {h.source_id for h in result.hits} == {"SRC.PHALADEEPIKA"}


def test_edition_methodology_language_domain_and_origin_filters(built: Built) -> None:
    r = _retriever(built)
    by_edition = r.retrieve(
        RetrievalQuery(
            text="house",
            top_k=30,
            max_distance=1.0,
            filters=RetrievalFilters(edition_ids=("BRIHAT_JATAKA_SASTRI",)),
        )
    )
    assert by_edition.hits and {h.edition_id for h in by_edition.hits} == {"BRIHAT_JATAKA_SASTRI"}

    by_profile = r.retrieve(
        RetrievalQuery(
            text="house significator",
            top_k=30,
            max_distance=1.0,
            filters=RetrievalFilters(methodology_profiles=("KB_PHALA_SASTRI_HOUSE_KARAKA_XV_17",)),
        )
    )
    assert by_profile.hits
    assert {h.methodology_profile for h in by_profile.hits} == {
        "KB_PHALA_SASTRI_HOUSE_KARAKA_XV_17"
    }

    by_domain = r.retrieve(
        RetrievalQuery(
            text="love marriage",
            top_k=30,
            max_distance=1.0,
            filters=RetrievalFilters(knowledge_domains=(KnowledgeDomain.TAROT,)),
        )
    )
    assert by_domain.hits
    assert {h.knowledge_domain for h in by_domain.hits} == {KnowledgeDomain.TAROT}
    assert {h.text_origin for h in by_domain.hits} == {TextOrigin.SOURCE_TEXT}

    english = r.retrieve(
        RetrievalQuery(
            text="Sun", top_k=5, max_distance=1.0, filters=RetrievalFilters(languages=("en",))
        )
    )
    assert english.hits and {h.language for h in english.hits} == {"en"}
    none = r.retrieve(
        RetrievalQuery(text="Sun", top_k=5, filters=RetrievalFilters(languages=("hi",)))
    )
    assert none.hits == ()  # no Hindi knowledge text exists, and none is faked

    parent = r.retrieve(
        RetrievalQuery(
            text="significations",
            top_k=30,
            max_distance=1.0,
            filters=RetrievalFilters(parent_concept_ids=("HOUSE.07",)),
        )
    )
    assert parent.hits and {h.parent_concept_id for h in parent.hits} == {"HOUSE.07"}


def test_combined_filters_intersect(built: Built) -> None:
    result = _retriever(built).retrieve(
        RetrievalQuery(
            text="house",
            top_k=30,
            filters=RetrievalFilters(
                source_ids=("SRC.BPHS",),
                text_origins=(TextOrigin.SOURCE_TEXT,),
            ),
        )
    )
    assert result.hits == ()  # no BPHS text is stored verbatim (copyright)


def test_top_k_is_bounded() -> None:
    with pytest.raises(ValueError):
        RetrievalQuery(text="x", top_k=MAX_TOP_K + 1)
    with pytest.raises(ValueError):
        RetrievalQuery(text="x", top_k=0)
    with pytest.raises(ValueError):
        RetrievalQuery(text="", top_k=3)
    with pytest.raises(ValueError):
        RetrievalQuery(text="x" * 2001)


def test_results_are_deterministic_and_ordered_by_distance(built: Built) -> None:
    r = _retriever(built)
    q = RetrievalQuery(text="wealth income expenses", top_k=15)
    a, b = r.retrieve(q), r.retrieve(q)
    assert a == b
    distances = [h.distance for h in a.hits]
    assert distances == sorted(distances)
    assert [h.rank for h in a.hits] == list(range(1, len(a.hits) + 1))


def test_lexical_provider_never_claims_to_be_semantic(built: Built) -> None:
    result = _retriever(built).retrieve(RetrievalQuery(text="Wheel of Fortune", top_k=3))
    assert result.is_semantic is False
    assert "LEXICAL_NOT_SEMANTIC" in result.notes
    assert result.hits[0].parent_concept_id == "TAROT.major_10_wheel_of_fortune"
    assert all(not h.is_semantic for h in result.hits)


@pytest.mark.parametrize(
    "query",
    [
        "कौन सा भाव आजीविका से जुड़ा है",  # Hindi (Devanagari)
        "kaun sa ghar naukri se juda hai",  # Hinglish (romanised)
        "सूर्य किसका कारक है",
    ],
)
def test_hindi_and_hinglish_are_not_faked_by_the_lexical_provider(built: Built, query: str) -> None:
    result = _retriever(built).retrieve(RetrievalQuery(text=query, top_k=5))
    assert result.hits == ()
    if any("ऀ" <= ch <= "ॿ" for ch in query):
        assert "CROSS_LANGUAGE_RETRIEVAL_NOT_VALIDATED" in result.notes


def test_max_distance_is_a_floor_not_a_relevance_claim(built: Built) -> None:
    r = _retriever(built)
    loose = r.retrieve(RetrievalQuery(text="profession", top_k=50, max_distance=1.0))
    tight = r.retrieve(RetrievalQuery(text="profession", top_k=50, max_distance=0.5))
    assert len(tight.hits) <= len(loose.hits)
    assert all(h.distance <= 0.5 for h in tight.hits)


def test_unknown_unsealed_or_mismatched_versions_are_refused(
    built: Built,
) -> None:
    store, result, provider = built
    r = Retriever(store, provider)
    with pytest.raises(RetrievalError, match="unknown"):
        r.retrieve(RetrievalQuery(text="x", version_id="KV-none"))
    other = Retriever(store, HashingEmbeddingProvider(512))
    with pytest.raises(RetrievalError):
        other.retrieve(RetrievalQuery(text="x"))  # no sealed version for that configuration
    with pytest.raises(RetrievalError, match="different configuration"):
        other.retrieve(RetrievalQuery(text="x", version_id=result.version_id))


def test_two_sealed_versions_require_an_explicit_choice(built: Built) -> None:
    store, result, provider = built
    from pandit_knowledge.content import load_content

    content = load_content()
    content.chunk_units = content.chunk_units[:50]
    second = KnowledgeBuilder(store, provider).build(content)
    assert second.version_id != result.version_id
    r = Retriever(store, provider)
    with pytest.raises(RetrievalError, match="name the knowledge version"):
        r.retrieve(RetrievalQuery(text="profession"))
    explicit = r.retrieve(RetrievalQuery(text="profession", version_id=result.version_id))
    assert explicit.knowledge_version_id == result.version_id


def test_retrieval_writes_nothing_and_never_stores_the_query(built: Built) -> None:
    store, result, provider = built
    secret = "born on 14 March 1990 at 06:30 in Pune, phone 9876543210, mail a@b.example"
    before = {
        t: store.select_rows(result.version_id, t)
        for t in ("chunks", "statements", "concepts", "terms")
    }
    runs_before = store.ingestion_runs(result.version_id)
    Retriever(store, provider).retrieve(RetrievalQuery(text=secret, top_k=5))
    after = {t: store.select_rows(result.version_id, t) for t in before}
    assert before == after
    assert store.ingestion_runs(result.version_id) == runs_before
    flat = repr(store.__dict__)
    assert "9876543210" not in flat and "a@b.example" not in flat and "Pune" not in flat
