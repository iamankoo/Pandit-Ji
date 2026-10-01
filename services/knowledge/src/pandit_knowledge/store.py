"""Storage interface and the in-memory reference store (KB-14, KB-15, KB-17).

Both the in-memory store and the PostgreSQL store (`pg_store.py`) implement
:class:`KnowledgeStore` and enforce the same rules:

* a version is ``DRAFT`` while it is built and ``SEALED`` afterwards; a sealed version rejects
  every insert (never silently mutated);
* rows are keyed by ``(version_id, natural key)``; re-inserting an identical row is a no-op and
  re-inserting a different row under the same key is an error (never overwritten);
* every foreign key is checked; an embedding must match its configuration's dimension and its
  chunk's content hash.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Protocol

from pandit_knowledge.embeddings import cosine_distance
from pandit_knowledge.models import (
    EmbeddingConfig,
    KnowledgeVersion,
    RetrievalFilters,
    VersionManifest,
)
from pandit_knowledge.schema import VERSIONED_TABLES, TableSpec

BeginOutcome = Literal["CREATED", "EXISTS_SEALED", "RESUME_DRAFT"]


class KnowledgeIntegrityError(Exception):
    """A key, foreign-key, hash or dimension constraint would be violated."""


class SealedVersionError(KnowledgeIntegrityError):
    """A write was attempted on a sealed knowledge version."""


class KnowledgeStore(Protocol):
    def register_embedding_config(self, config: EmbeddingConfig) -> None: ...

    def begin_version(self, manifest: VersionManifest) -> tuple[KnowledgeVersion, BeginOutcome]: ...

    def get_version(self, version_id: str) -> KnowledgeVersion | None: ...

    def list_versions(self) -> list[KnowledgeVersion]: ...

    def insert_rows(
        self, version_id: str, table: str, rows: Sequence[Mapping[str, Any]]
    ) -> int: ...

    def insert_embeddings(
        self,
        version_id: str,
        embedding_config_id: str,
        items: Sequence[tuple[str, str, Sequence[float]]],
    ) -> int: ...

    def seal_version(self, version_id: str) -> None: ...

    def select_rows(
        self,
        version_id: str,
        table: str,
        where: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]: ...

    def nearest(
        self,
        version_id: str,
        embedding_config_id: str,
        vector: Sequence[float],
        top_k: int,
        filters: RetrievalFilters,
    ) -> list[tuple[dict[str, Any], float]]: ...

    def embedded_chunk_ids(self, version_id: str, embedding_config_id: str) -> set[str]: ...

    def record_ingestion_run(
        self,
        version_id: str,
        status: str,
        input_manifest_hash: str,
        counts: Mapping[str, int],
        notes: str,
    ) -> None: ...

    def ingestion_runs(self, version_id: str) -> list[dict[str, Any]]: ...


def chunk_matches_filters(chunk: Mapping[str, Any], filters: RetrievalFilters) -> bool:
    """Single definition of the retrieval filters, used by the in-memory store."""
    if filters.source_ids and chunk["source_id"] not in filters.source_ids:
        return False
    if filters.edition_ids and chunk["edition_id"] not in filters.edition_ids:
        return False
    if filters.methodology_profiles and chunk["methodology_profile"] not in (
        filters.methodology_profiles
    ):
        return False
    if filters.languages and chunk["language"] not in filters.languages:
        return False
    if filters.knowledge_domains and chunk["knowledge_domain"] not in {
        d.value for d in filters.knowledge_domains
    }:
        return False
    if filters.text_origins and chunk["text_origin"] not in {o.value for o in filters.text_origins}:
        return False
    return not (
        filters.parent_concept_ids and chunk["parent_concept_id"] not in filters.parent_concept_ids
    )


class InMemoryKnowledgeStore:
    """Reference implementation; also the store used by unit tests and CI."""

    def __init__(self) -> None:
        self._versions: dict[str, tuple[str, VersionManifest]] = {}
        self._rows: dict[tuple[str, str], dict[tuple[Any, ...], dict[str, Any]]] = {}
        self._configs: dict[str, EmbeddingConfig] = {}
        self._embeddings: dict[tuple[str, str, str], tuple[str, list[float]]] = {}
        self._runs: list[dict[str, Any]] = []

    # -- versions ------------------------------------------------------------------------
    def register_embedding_config(self, config: EmbeddingConfig) -> None:
        self._configs[config.embedding_config_id] = config

    def begin_version(self, manifest: VersionManifest) -> tuple[KnowledgeVersion, BeginOutcome]:
        vid = manifest.version_id
        if manifest.embedding_config_id not in self._configs:
            raise KnowledgeIntegrityError("embedding configuration is not registered")
        existing = self._versions.get(vid)
        if existing is None:
            self._versions[vid] = ("DRAFT", manifest)
            return KnowledgeVersion(version_id=vid, status="DRAFT", manifest=manifest), "CREATED"
        status, _ = existing
        outcome: BeginOutcome = "EXISTS_SEALED" if status == "SEALED" else "RESUME_DRAFT"
        return (
            KnowledgeVersion(
                version_id=vid,
                status="SEALED" if status == "SEALED" else "DRAFT",
                manifest=manifest,
            ),
            outcome,
        )

    def get_version(self, version_id: str) -> KnowledgeVersion | None:
        found = self._versions.get(version_id)
        if found is None:
            return None
        status, manifest = found
        return KnowledgeVersion(
            version_id=version_id,
            status="SEALED" if status == "SEALED" else "DRAFT",
            manifest=manifest,
        )

    def list_versions(self) -> list[KnowledgeVersion]:
        return [v for vid in sorted(self._versions) if (v := self.get_version(vid)) is not None]

    def seal_version(self, version_id: str) -> None:
        status, manifest = self._require_version(version_id)
        if status == "SEALED":
            return
        self._versions[version_id] = ("SEALED", manifest)

    def _require_version(self, version_id: str) -> tuple[str, VersionManifest]:
        found = self._versions.get(version_id)
        if found is None:
            raise KnowledgeIntegrityError(f"unknown knowledge version {version_id}")
        return found

    def _require_draft(self, version_id: str) -> None:
        status, _ = self._require_version(version_id)
        if status == "SEALED":
            raise SealedVersionError(f"knowledge version {version_id} is sealed")

    # -- rows ----------------------------------------------------------------------------
    @staticmethod
    def _spec(table: str) -> TableSpec:
        try:
            return VERSIONED_TABLES[table]
        except KeyError:
            raise KnowledgeIntegrityError(f"unknown knowledge table {table}") from None

    def insert_rows(self, version_id: str, table: str, rows: Sequence[Mapping[str, Any]]) -> int:
        self._require_draft(version_id)
        spec = self._spec(table)
        bucket = self._rows.setdefault((version_id, table), {})
        inserted = 0
        for raw in rows:
            row = copy.deepcopy(dict(raw))
            row["version_id"] = version_id
            if set(row) != set(spec.columns):
                missing = set(spec.columns) - set(row)
                extra = set(row) - set(spec.columns)
                raise KnowledgeIntegrityError(
                    f"{table}: columns mismatch (missing {sorted(missing)}, extra {sorted(extra)})"
                )
            key = tuple(row[c] for c in spec.primary_key)
            old = bucket.get(key)
            if old is not None:
                if old["content_hash"] != row["content_hash"]:
                    raise KnowledgeIntegrityError(
                        f"{table}: key {key[1:]} already exists with different content"
                    )
                continue
            for fk_cols, ref_table in spec.foreign_keys:
                ref_key = tuple(row[c] for c in fk_cols)
                if ref_key not in self._rows.get((version_id, ref_table), {}):
                    raise KnowledgeIntegrityError(
                        f"{table}: foreign key {fk_cols} -> {ref_table} {ref_key[1:]} not found"
                    )
            bucket[key] = row
            inserted += 1
        return inserted

    def select_rows(
        self,
        version_id: str,
        table: str,
        where: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        self._spec(table)  # rejects an unknown table name
        bucket = self._rows.get((version_id, table), {})
        out = []
        for key in sorted(bucket, key=lambda k: tuple(str(x) for x in k)):
            row = bucket[key]
            if where and any(row.get(c) != v for c, v in where.items()):
                continue
            out.append(copy.deepcopy(row))
        return out

    # -- embeddings ----------------------------------------------------------------------
    def insert_embeddings(
        self,
        version_id: str,
        embedding_config_id: str,
        items: Sequence[tuple[str, str, Sequence[float]]],
    ) -> int:
        self._require_draft(version_id)
        config = self._configs.get(embedding_config_id)
        if config is None:
            raise KnowledgeIntegrityError("embedding configuration is not registered")
        _, manifest = self._require_version(version_id)
        if manifest.embedding_config_id != embedding_config_id:
            raise KnowledgeIntegrityError(
                "embedding configuration is not the one of this knowledge version"
            )
        chunks = self._rows.get((version_id, "chunks"), {})
        inserted = 0
        for chunk_id, content_hash, vector in items:
            chunk = chunks.get((version_id, chunk_id))
            if chunk is None:
                raise KnowledgeIntegrityError(f"embedding for unknown chunk {chunk_id}")
            if chunk["content_hash"] != content_hash:
                raise KnowledgeIntegrityError(f"embedding hash mismatch for chunk {chunk_id}")
            if len(vector) != config.dimension:
                raise KnowledgeIntegrityError(
                    f"embedding dimension {len(vector)} != configured {config.dimension}"
                )
            key = (version_id, chunk_id, embedding_config_id)
            if key in self._embeddings:
                continue
            self._embeddings[key] = (content_hash, [float(x) for x in vector])
            inserted += 1
        return inserted

    def embedded_chunk_ids(self, version_id: str, embedding_config_id: str) -> set[str]:
        return {c for (v, c, e) in self._embeddings if v == version_id and e == embedding_config_id}

    def nearest(
        self,
        version_id: str,
        embedding_config_id: str,
        vector: Sequence[float],
        top_k: int,
        filters: RetrievalFilters,
    ) -> list[tuple[dict[str, Any], float]]:
        chunks = self._rows.get((version_id, "chunks"), {})
        scored: list[tuple[dict[str, Any], float]] = []
        for (v, chunk_id, e), (_, stored) in self._embeddings.items():
            if v != version_id or e != embedding_config_id:
                continue
            chunk = chunks[(version_id, chunk_id)]
            if not chunk_matches_filters(chunk, filters):
                continue
            scored.append((copy.deepcopy(chunk), cosine_distance(vector, stored)))
        scored.sort(key=lambda item: (item[1], item[0]["chunk_id"]))
        return scored[:top_k]

    # -- ingestion runs ------------------------------------------------------------------
    def record_ingestion_run(
        self,
        version_id: str,
        status: str,
        input_manifest_hash: str,
        counts: Mapping[str, int],
        notes: str,
    ) -> None:
        self._runs.append(
            {
                "run_id": len(self._runs) + 1,
                "version_id": version_id,
                "status": status,
                "input_manifest_hash": input_manifest_hash,
                "counts": dict(counts),
                "notes": notes,
            }
        )

    def ingestion_runs(self, version_id: str) -> list[dict[str, Any]]:
        return [copy.deepcopy(r) for r in self._runs if r["version_id"] == version_id]
