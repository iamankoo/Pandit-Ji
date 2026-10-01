"""Deterministic chunking and the embedding-provider abstraction (KB-18 to KB-22)."""

from __future__ import annotations

import math

import pytest

from pandit_knowledge.chunking import ChunkUnit, chunk_unit, embedding_text, split_text
from pandit_knowledge.content import KnowledgeContent, all_chunks
from pandit_knowledge.embeddings import HashingEmbeddingProvider, cosine_distance
from pandit_knowledge.models import (
    Confidence,
    EmbeddingConfig,
    KnowledgeDomain,
    ReadingLevel,
    TextFidelity,
    TextOrigin,
)


def _unit(text: str, location: str = "Part III, The Fool", source: str = "SRC.X") -> ChunkUnit:
    return ChunkUnit(
        text=text,
        knowledge_domain=KnowledgeDomain.TAROT,
        language="en",
        text_origin=TextOrigin.SOURCE_TEXT,
        text_fidelity=TextFidelity.PROOFREAD_TRANSCRIPTION,
        source_id=source,
        edition_id="ED.X",
        source_location=location,
        section_path="A/B",
        parent_concept_id="TAROT.major_00_fool",
        methodology_profile="PROFILE.X",
        reading_level=ReadingLevel.TRANSCRIPTION_LEVEL,
        confidence=Confidence.MEDIUM,
        external_ref="major_00_fool",
    )


def test_short_unit_is_one_chunk_with_full_provenance() -> None:
    chunks = chunk_unit(_unit("Folly, mania. Reversed: Negligence."))
    assert len(chunks) == 1
    c = chunks[0]
    assert (c.source_id, c.edition_id, c.source_location, c.section_path) == (
        "SRC.X",
        "ED.X",
        "Part III, The Fool",
        "A/B",
    )
    assert c.language == "en" and c.methodology_profile == "PROFILE.X"
    assert c.sequence == 0 and c.parent_concept_id == "TAROT.major_00_fool"
    assert c.content_hash() and len(c.content_hash()) == 64


def test_chunking_is_deterministic_and_rerunnable() -> None:
    text = " ".join(f"Sentence number {i} is here." for i in range(80))
    first = chunk_unit(_unit(text), max_chars=300)
    second = chunk_unit(_unit(text), max_chars=300)
    assert first == second
    assert len(first) > 3
    assert [c.sequence for c in first] == list(range(len(first)))
    assert len({c.chunk_id for c in first}) == len(first)


def test_split_happens_only_at_sentence_boundaries_and_loses_nothing() -> None:
    text = " ".join(f"This is sentence {i}." for i in range(60))
    pieces = split_text(text, 200)
    assert all(p.endswith(".") for p in pieces)
    assert " ".join(pieces) == text
    assert all(len(p) <= 200 for p in pieces)


def test_a_single_overlong_sentence_stays_whole() -> None:
    long = "word " * 100 + "end."
    assert split_text(long, 50) == [long.strip()]


def test_units_are_never_merged_and_ids_depend_on_provenance_and_text() -> None:
    a = chunk_unit(_unit("Same text."))[0]
    b = chunk_unit(_unit("Same text.", source="SRC.Y"))[0]
    c = chunk_unit(_unit("Same text.", location="Part III, The Magician"))[0]
    d = chunk_unit(_unit("Other text."))[0]
    assert len({a.chunk_id, b.chunk_id, c.chunk_id, d.chunk_id}) == 4
    assert a.chunk_id == chunk_unit(_unit("Same text."))[0].chunk_id


def test_blank_text_makes_no_chunk() -> None:
    assert chunk_unit(_unit("   \n  ")) == []


def test_all_corpus_chunks_keep_their_unit_provenance(content: KnowledgeContent) -> None:
    chunks = all_chunks(content)
    assert len(chunks) == len(content.chunk_units)  # nothing needed splitting
    for chunk in chunks:
        assert chunk.source_id and chunk.edition_id and chunk.source_location
        assert chunk.methodology_profile and chunk.language
        assert chunk.chunking_version == "1.0.0"
    assert len({c.chunk_id for c in chunks}) == len(chunks)


def test_embedding_text_uses_location_and_text_only(content: KnowledgeContent) -> None:
    chunk = next(c for c in all_chunks(content) if c.external_ref == "major_06_lovers")
    assert embedding_text(chunk).startswith("Part III §3, The Lovers.")
    assert embedding_text(chunk).endswith(chunk.text)


# ---- embedding providers ------------------------------------------------------------------
def test_hashing_provider_is_deterministic_normalised_and_dimensioned() -> None:
    p = HashingEmbeddingProvider(128)
    a = p.embed_query("the tenth house and profession")
    assert a == p.embed_query("the tenth house and profession")
    assert len(a) == 128
    assert math.isclose(sum(x * x for x in a), 1.0, rel_tol=1e-9)
    assert p.embed_documents(["x y z"]) == [p.embed_query("x y z")]


def test_hashing_provider_is_lexical_and_declares_no_language() -> None:
    cfg = HashingEmbeddingProvider().config
    assert cfg.is_semantic is False
    assert cfg.languages_declared == ()
    assert cfg.metric == "cosine"


def test_identical_text_is_closest_and_unrelated_text_is_far() -> None:
    p = HashingEmbeddingProvider(512)
    q = p.embed_query("profession livelihood")
    near = p.embed_documents(["profession livelihood"])[0]
    far = p.embed_documents(["horses river granite"])[0]
    assert cosine_distance(q, near) < 1e-9
    assert cosine_distance(q, far) > 0.8


def test_empty_vector_distance_is_maximal() -> None:
    assert cosine_distance([0.0, 0.0], [1.0, 0.0]) == 1.0


def test_embedding_config_identity_changes_with_every_field() -> None:
    base = EmbeddingConfig(
        provider="p",
        model="m",
        model_version="1",
        dimension=8,
        config_version="1",
        is_semantic=True,
    )
    variants = [
        base.model_copy(update={"provider": "q"}),
        base.model_copy(update={"model": "n"}),
        base.model_copy(update={"model_version": "2"}),
        base.model_copy(update={"dimension": 16}),
        base.model_copy(update={"config_version": "2"}),
        base.model_copy(update={"is_semantic": False}),
        base.model_copy(update={"languages_declared": ("en",)}),
    ]
    ids = {base.embedding_config_id} | {v.embedding_config_id for v in variants}
    assert len(ids) == 8
    assert base.embedding_config_id.startswith("EC-")


def test_provider_dimension_must_be_reasonable() -> None:
    with pytest.raises(ValueError):
        HashingEmbeddingProvider(4)
