"""Bounded, deterministic retrieval with full provenance (KB-24 to KB-26).

Retrieval answers one question: *which stored knowledge text is closest to this query text?* It
never reads a user's chart, never calls the rule engine, never writes anything (the query text is
not stored or logged) and every hit is stamped ``KNOWLEDGE_TEXT_NOT_A_CHART_FACT``. Chart facts
and rule results come only from the deterministic pipeline.

Behaviour that is deliberately explicit:

* ``top_k`` is capped (``MAX_TOP_K``); ties break by chunk identifier, so results are repeatable;
* a candidate farther than ``max_distance`` (default 0.8; at least 1.0 means no similarity at
  all) is not a hit -- this floor bounds noise, it does not certify relevance;
* a non-semantic provider says so in ``notes`` (``LEXICAL_NOT_SEMANTIC``);
* a Devanagari query against a configuration that declares no Hindi support gets
  ``CROSS_LANGUAGE_RETRIEVAL_NOT_VALIDATED``: the package never pretends cross-language search
  works unless the configuration declares it and a validation says so.
"""

from __future__ import annotations

import re

from pandit_knowledge.embeddings import EmbeddingProvider
from pandit_knowledge.models import (
    ChunkRecord,
    KnowledgeVersion,
    RetrievalHit,
    RetrievalQuery,
    RetrievalResult,
)
from pandit_knowledge.store import KnowledgeStore

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
NO_SIMILARITY = 1.0


class RetrievalError(Exception):
    pass


class Retriever:
    def __init__(self, store: KnowledgeStore, provider: EmbeddingProvider) -> None:
        self._store = store
        self._provider = provider

    def resolve_version(self, version_id: str | None) -> KnowledgeVersion:
        config_id = self._provider.config.embedding_config_id
        if version_id is not None:
            version = self._store.get_version(version_id)
            if version is None:
                raise RetrievalError(f"unknown knowledge version {version_id}")
        else:
            candidates = [
                v
                for v in self._store.list_versions()
                if v.status == "SEALED" and v.manifest.embedding_config_id == config_id
            ]
            if len(candidates) != 1:
                raise RetrievalError(
                    f"{len(candidates)} sealed versions use this embedding configuration; "
                    "name the knowledge version explicitly"
                )
            version = candidates[0]
        if version.status != "SEALED":
            raise RetrievalError("retrieval reads sealed knowledge versions only")
        if version.manifest.embedding_config_id != config_id:
            raise RetrievalError(
                "the knowledge version was embedded with a different configuration "
                "than the provider"
            )
        return version

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        version = self.resolve_version(query.version_id)
        config = self._provider.config
        vector = self._provider.embed_query(query.text)
        rows = self._store.nearest(
            version.version_id, config.embedding_config_id, vector, query.top_k, query.filters
        )
        hits: list[RetrievalHit] = []
        for row, distance in rows:
            if distance >= NO_SIMILARITY or distance > query.max_distance:
                continue
            chunk = ChunkRecord.model_validate(
                {
                    k: v
                    for k, v in row.items()
                    if k not in {"version_id", "content_hash", "char_count"}
                }
            )
            hits.append(
                RetrievalHit(
                    rank=len(hits) + 1,
                    chunk_id=chunk.chunk_id,
                    distance=round(float(distance), 6),
                    metric=config.metric,
                    knowledge_version_id=version.version_id,
                    embedding_config_id=config.embedding_config_id,
                    is_semantic=config.is_semantic,
                    knowledge_domain=chunk.knowledge_domain,
                    source_id=chunk.source_id,
                    edition_id=chunk.edition_id,
                    source_location=chunk.source_location,
                    section_path=chunk.section_path,
                    methodology_profile=chunk.methodology_profile,
                    language=chunk.language,
                    text_origin=chunk.text_origin,
                    text_fidelity=chunk.text_fidelity,
                    reading_level=chunk.reading_level,
                    confidence=chunk.confidence,
                    parent_concept_id=chunk.parent_concept_id,
                    content_hash=str(row["content_hash"]),
                    text=chunk.text,
                )
            )
        notes: list[str] = []
        if getattr(self._store, "exact_search", True) is False:
            notes.append("APPROXIMATE_INDEX_SEARCH")
        if not config.is_semantic:
            notes.append("LEXICAL_NOT_SEMANTIC")
        if _DEVANAGARI.search(query.text) and not any(
            lang.split("-")[0] == "hi" for lang in config.languages_declared
        ):
            notes.append("CROSS_LANGUAGE_RETRIEVAL_NOT_VALIDATED")
        return RetrievalResult(
            knowledge_version_id=version.version_id,
            embedding_config_id=config.embedding_config_id,
            is_semantic=config.is_semantic,
            metric=config.metric,
            hits=tuple(hits),
            notes=tuple(notes),
        )
