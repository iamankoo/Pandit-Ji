"""Idempotent, auditable knowledge build (KB-15, KB-16, KB-18 to KB-20).

``KnowledgeBuilder.build`` turns curated content plus one embedding configuration into one
sealed knowledge version:

* the version identifier is derived from a snapshot hash over every record hash, the schema,
  ingestion, chunking and standards versions, the embedding configuration and a hash of the
  Phase 6 rule files, so identical inputs always name the same version;
* building identical input again finds the sealed version and changes nothing (``NOOP``);
* a build interrupted before sealing is a ``DRAFT``: the next build resumes it, inserting only
  the missing rows and embeddings (resumable);
* nothing is ever overwritten: a sealed version is immutable and any change is a new version.

Ingestion never calls an embedding model during deterministic chart calculation; it is a batch
job run by the ``knowledge`` service only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from pandit_knowledge.chunking import embedding_text
from pandit_knowledge.content import KnowledgeContent, all_chunks
from pandit_knowledge.embeddings import EmbeddingProvider
from pandit_knowledge.models import (
    CHUNKING_VERSION,
    INGESTION_VERSION,
    KNOWLEDGE_SCHEMA_VERSION,
    STANDARDS_VERSION,
    ChunkRecord,
    VersionManifest,
    sha256_hex,
)
from pandit_knowledge.store import KnowledgeStore

EMBED_BATCH = 64


@dataclass(frozen=True)
class BuildResult:
    version_id: str
    outcome: Literal["CREATED", "RESUMED", "NOOP"]
    record_counts: Mapping[str, int]
    embeddings_written: int
    snapshot_hash: str


def _row(model: Any) -> dict[str, Any]:
    row = model.model_dump(mode="json")
    row["content_hash"] = model.content_hash()
    return row  # type: ignore[no-any-return]


def build_rows(
    content: KnowledgeContent,
) -> tuple[dict[str, list[dict[str, Any]]], list[ChunkRecord]]:
    chunks_by_id: dict[str, ChunkRecord] = {}
    for chunk in all_chunks(content):
        old = chunks_by_id.get(chunk.chunk_id)
        if old is not None and old != chunk:
            raise ValueError(f"chunk identifier collision: {chunk.chunk_id}")
        chunks_by_id[chunk.chunk_id] = chunk
    chunks = [chunks_by_id[c] for c in sorted(chunks_by_id)]
    chunk_rows = []
    for chunk in chunks:
        row = _row(chunk)
        row["char_count"] = chunk.char_count
        chunk_rows.append(row)
    rows: dict[str, list[dict[str, Any]]] = {
        "sources": [_row(m) for m in sorted(content.sources, key=lambda m: m.source_id)],
        "source_editions": [_row(m) for m in sorted(content.editions, key=lambda m: m.edition_id)],
        "concepts": [_row(m) for m in sorted(content.concepts, key=lambda m: m.concept_id)],
        "statements": [_row(m) for m in sorted(content.statements, key=lambda m: m.statement_id)],
        "terms": [_row(m) for m in sorted(content.terms, key=lambda m: m.term_id)],
        "rule_references": [
            _row(m) for m in sorted(content.rule_references, key=lambda m: m.reference_id)
        ],
        "domain_mappings": [
            _row(m) for m in sorted(content.domain_mappings, key=lambda m: m.mapping_id)
        ],
        "exceptions": [_row(m) for m in sorted(content.exceptions, key=lambda m: m.exception_id)],
        "chunks": chunk_rows,
    }
    return rows, chunks


def snapshot_hash(
    rows: Mapping[str, Sequence[Mapping[str, Any]]],
    embedding_config_id: str,
    rules_snapshot_hash: str,
    standards_version: str = STANDARDS_VERSION,
) -> str:
    return sha256_hex(
        {
            "tables": {t: [r["content_hash"] for r in rs] for t, rs in sorted(rows.items())},
            "standards_version": standards_version,
            "schema_version": KNOWLEDGE_SCHEMA_VERSION,
            "ingestion_version": INGESTION_VERSION,
            "chunking_version": CHUNKING_VERSION,
            "embedding_config_id": embedding_config_id,
            "rules_snapshot_hash": rules_snapshot_hash,
        }
    )


class KnowledgeBuilder:
    def __init__(
        self,
        store: KnowledgeStore,
        provider: EmbeddingProvider,
        standards_version: str = STANDARDS_VERSION,
    ) -> None:
        """``standards_version`` defaults to the Phase 12 value, so the Phase 12 snapshot hash is
        unchanged; the Phase 13 palm knowledge version passes its own (v1.28.0)."""
        self._store = store
        self._provider = provider
        self._standards_version = standards_version

    def manifest_for(self, content: KnowledgeContent) -> tuple[VersionManifest, dict[str, Any]]:
        rows, chunks = build_rows(content)
        config = self._provider.config
        snap = snapshot_hash(
            rows, config.embedding_config_id, content.rules_snapshot_hash, self._standards_version
        )
        manifest = VersionManifest(
            standards_version=self._standards_version,
            schema_version=KNOWLEDGE_SCHEMA_VERSION,
            ingestion_version=INGESTION_VERSION,
            chunking_version=CHUNKING_VERSION,
            embedding_config_id=config.embedding_config_id,
            source_ids=content.source_ids(),
            methodology_profiles=content.methodology_profiles(),
            record_counts={t: len(r) for t, r in rows.items()},
            rules_snapshot_hash=content.rules_snapshot_hash,
            snapshot_hash=snap,
        )
        return manifest, {"rows": rows, "chunks": chunks}

    def build(self, content: KnowledgeContent) -> BuildResult:
        manifest, parts = self.manifest_for(content)
        rows: dict[str, list[dict[str, Any]]] = parts["rows"]
        chunks: list[ChunkRecord] = parts["chunks"]
        self._store.register_embedding_config(self._provider.config)
        version, outcome = self._store.begin_version(manifest)
        counts = dict(manifest.record_counts)
        if outcome == "EXISTS_SEALED":
            self._store.record_ingestion_run(
                version.version_id, "NOOP_IDENTICAL", manifest.snapshot_hash, counts, "sealed"
            )
            return BuildResult(version.version_id, "NOOP", counts, 0, manifest.snapshot_hash)

        for table in (
            "sources",
            "source_editions",
            "concepts",
            "statements",
            "terms",
            "rule_references",
            "domain_mappings",
            "exceptions",
            "chunks",
        ):
            self._store.insert_rows(version.version_id, table, rows[table])

        done = self._store.embedded_chunk_ids(
            version.version_id, self._provider.config.embedding_config_id
        )
        pending = [c for c in chunks if c.chunk_id not in done]
        written = 0
        for start in range(0, len(pending), EMBED_BATCH):
            batch = pending[start : start + EMBED_BATCH]
            vectors = self._provider.embed_documents([embedding_text(c) for c in batch])
            written += self._store.insert_embeddings(
                version.version_id,
                self._provider.config.embedding_config_id,
                [(c.chunk_id, c.content_hash(), v) for c, v in zip(batch, vectors, strict=True)],
            )
        self._store.seal_version(version.version_id)
        status = "CREATED" if outcome == "CREATED" else "RESUMED"
        self._store.record_ingestion_run(
            version.version_id,
            status,
            manifest.snapshot_hash,
            {**counts, "embeddings_written": written},
            "sealed",
        )
        return BuildResult(
            version.version_id,
            "CREATED" if outcome == "CREATED" else "RESUMED",
            counts,
            written,
            manifest.snapshot_hash,
        )
