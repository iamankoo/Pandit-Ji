"""PostgreSQL + pgvector implementation of :class:`~pandit_knowledge.store.KnowledgeStore`.

The DDL lives in ``infrastructure/migrations/versions/0002_knowledge_schema.py``; database
triggers (not only this code) reject writes to a sealed version, row updates, wrong embedding
dimensions and embeddings whose hash does not match their chunk. This module needs the optional
``postgres`` extra (``sqlalchemy`` and ``psycopg``) and is imported only by code that uses it.

Index strategy (KB-35): the ANN index is created per embedding configuration, on demand, as a
*partial expression* index::

    CREATE INDEX ... USING hnsw ((embedding::vector(D)) vector_cosine_ops)
        WHERE embedding_config_id = '<id>'

so the untyped ``vector`` column can serve several dimensions and the model can change without a
table change. HNSW is the default because it needs no training step and works on an empty or
growing table (IVFFlat needs representative rows to build its lists and degrades as the corpus
changes); at the expected corpus size (hundreds to a few thousand chunks) an exact scan is also
fast, so retrieval stays exact when an index is not used.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from pandit_knowledge.models import (
    EmbeddingConfig,
    KnowledgeVersion,
    RetrievalFilters,
    VersionManifest,
    sha256_hex,
)
from pandit_knowledge.schema import (
    EMBEDDING_CONFIG_COLUMNS,
    VERSIONED_TABLES,
    TableSpec,
)
from pandit_knowledge.store import BeginOutcome, KnowledgeIntegrityError, SealedVersionError

_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def _vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


def _translate(exc: DBAPIError) -> KnowledgeIntegrityError:
    message = str(exc.orig) if exc.orig is not None else str(exc)
    if "is sealed" in message:
        return SealedVersionError(message.strip().splitlines()[0])
    return KnowledgeIntegrityError(message.strip().splitlines()[0])


class PostgresKnowledgeStore:
    """``approximate=False`` (the default) makes every search exact: index scans are switched
    off for the query, so an ANN index can never silently lower recall. ``approximate=True`` lets
    the planner use an ANN index (HNSW ``ef_search`` is raised to ``hnsw_ef_search``) and the
    retriever then reports ``APPROXIMATE_INDEX_SEARCH``."""

    def __init__(
        self, engine: Engine, *, approximate: bool = False, hnsw_ef_search: int = 200
    ) -> None:
        self._engine = engine
        self._approximate = approximate
        self._ef_search = int(hnsw_ef_search)

    @property
    def exact_search(self) -> bool:
        return not self._approximate

    # -- configurations and versions -------------------------------------------------------
    def register_embedding_config(self, config: EmbeddingConfig) -> None:
        values = {
            "embedding_config_id": config.embedding_config_id,
            "provider": config.provider,
            "model": config.model,
            "model_version": config.model_version,
            "dimension": config.dimension,
            "metric": config.metric,
            "config_version": config.config_version,
            "is_semantic": config.is_semantic,
            "languages_declared": json.dumps(list(config.languages_declared)),
            "config_hash": sha256_hex(config.model_dump(mode="json")),
        }
        cols = ", ".join(EMBEDDING_CONFIG_COLUMNS)
        params = ", ".join(
            "CAST(:languages_declared AS jsonb)" if c == "languages_declared" else f":{c}"
            for c in EMBEDDING_CONFIG_COLUMNS
        )
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"INSERT INTO knowledge.embedding_configs ({cols}) VALUES ({params}) "
                    "ON CONFLICT (embedding_config_id) DO NOTHING"
                ),
                values,
            )

    def begin_version(self, manifest: VersionManifest) -> tuple[KnowledgeVersion, BeginOutcome]:
        vid = manifest.version_id
        with self._engine.begin() as conn:
            inserted = conn.execute(
                text(
                    "INSERT INTO knowledge.knowledge_versions (version_id, status, snapshot_hash, "
                    "standards_version, schema_version, ingestion_version, chunking_version, "
                    "embedding_config_id, manifest) VALUES (:v, 'DRAFT', :h, :sv, :sc, :iv, :cv, "
                    ":ec, CAST(:m AS jsonb)) ON CONFLICT (version_id) DO NOTHING"
                ),
                {
                    "v": vid,
                    "h": manifest.snapshot_hash,
                    "sv": manifest.standards_version,
                    "sc": manifest.schema_version,
                    "iv": manifest.ingestion_version,
                    "cv": manifest.chunking_version,
                    "ec": manifest.embedding_config_id,
                    "m": manifest.model_dump_json(),
                },
            ).rowcount
            status: Any = conn.execute(
                text("SELECT status FROM knowledge.knowledge_versions WHERE version_id = :v"),
                {"v": vid},
            ).scalar_one()
        outcome: BeginOutcome
        if inserted:
            outcome = "CREATED"
        elif status == "SEALED":
            outcome = "EXISTS_SEALED"
        else:
            outcome = "RESUME_DRAFT"
        return (
            KnowledgeVersion(
                version_id=vid,
                status="SEALED" if status == "SEALED" else "DRAFT",
                manifest=manifest,
            ),
            outcome,
        )

    def get_version(self, version_id: str) -> KnowledgeVersion | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT status, manifest FROM knowledge.knowledge_versions "
                    "WHERE version_id = :v"
                ),
                {"v": version_id},
            ).first()
        if row is None:
            return None
        manifest = VersionManifest.model_validate(row[1])
        status: Literal["DRAFT", "SEALED"] = "SEALED" if row[0] == "SEALED" else "DRAFT"
        return KnowledgeVersion(version_id=version_id, status=status, manifest=manifest)

    def list_versions(self) -> list[KnowledgeVersion]:
        with self._engine.connect() as conn:
            ids = [
                r[0]
                for r in conn.execute(
                    text("SELECT version_id FROM knowledge.knowledge_versions ORDER BY version_id")
                )
            ]
        return [v for vid in ids if (v := self.get_version(vid)) is not None]

    def seal_version(self, version_id: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE knowledge.knowledge_versions SET status = 'SEALED', sealed_at = now() "
                    "WHERE version_id = :v AND status = 'DRAFT'"
                ),
                {"v": version_id},
            )

    # -- rows ------------------------------------------------------------------------------
    @staticmethod
    def _spec(table: str) -> TableSpec:
        try:
            return VERSIONED_TABLES[table]
        except KeyError:
            raise KnowledgeIntegrityError(f"unknown knowledge table {table}") from None

    def insert_rows(self, version_id: str, table: str, rows: Sequence[Mapping[str, Any]]) -> int:
        spec = self._spec(table)
        cols = ", ".join(spec.columns)
        params = ", ".join(
            f"CAST(:{c} AS jsonb)" if c in spec.json_columns else f":{c}" for c in spec.columns
        )
        pk = ", ".join(spec.primary_key)
        sql = text(
            f"INSERT INTO knowledge.{table} ({cols}) VALUES ({params}) "
            f"ON CONFLICT ({pk}) DO NOTHING"
        )
        inserted = 0
        try:
            with self._engine.begin() as conn:
                for raw in rows:
                    row = dict(raw)
                    row["version_id"] = version_id
                    if set(row) != set(spec.columns):
                        raise KnowledgeIntegrityError(f"{table}: columns mismatch")
                    values = {
                        c: (
                            json.dumps(row[c], sort_keys=True) if c in spec.json_columns else row[c]
                        )
                        for c in spec.columns
                    }
                    if conn.execute(sql, values).rowcount:
                        inserted += 1
                        continue
                    where = " AND ".join(f"{c} = :{c}" for c in spec.primary_key)
                    stored: Any = conn.execute(
                        text(f"SELECT content_hash FROM knowledge.{table} WHERE {where}"),
                        {c: row[c] for c in spec.primary_key},
                    ).scalar_one()
                    if stored != row["content_hash"]:
                        raise KnowledgeIntegrityError(
                            f"{table}: key {tuple(row[c] for c in spec.primary_key[1:])} already "
                            "exists with different content"
                        )
        except DBAPIError as exc:
            raise _translate(exc) from exc
        return inserted

    def select_rows(
        self, version_id: str, table: str, where: Mapping[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        spec = self._spec(table)
        clauses = ["version_id = :version_id"]
        params: dict[str, Any] = {"version_id": version_id}
        for i, (col, value) in enumerate((where or {}).items()):
            if col not in spec.columns:
                raise KnowledgeIntegrityError(f"{table}: unknown column {col}")
            clauses.append(f"{col} = :w{i}")
            params[f"w{i}"] = value
        order = ", ".join(spec.primary_key[1:])
        sql = text(
            f"SELECT {', '.join(spec.columns)} FROM knowledge.{table} "
            f"WHERE {' AND '.join(clauses)} ORDER BY {order}"
        )
        with self._engine.connect() as conn:
            result = conn.execute(sql, params)
            return [dict(zip(result.keys(), r, strict=True)) for r in result]

    # -- embeddings ------------------------------------------------------------------------
    def insert_embeddings(
        self,
        version_id: str,
        embedding_config_id: str,
        items: Sequence[tuple[str, str, Sequence[float]]],
    ) -> int:
        inserted = 0
        sql = text(
            "INSERT INTO knowledge.embeddings (version_id, chunk_id, embedding_config_id, "
            "content_hash, embedding) VALUES (:v, :c, :e, :h, CAST(:vec AS vector)) "
            "ON CONFLICT (version_id, chunk_id, embedding_config_id) DO NOTHING"
        )
        try:
            with self._engine.begin() as conn:
                for chunk_id, content_hash, vector in items:
                    res = conn.execute(
                        sql,
                        {
                            "v": version_id,
                            "c": chunk_id,
                            "e": embedding_config_id,
                            "h": content_hash,
                            "vec": _vector_literal(vector),
                        },
                    )
                    inserted += 1 if res.rowcount else 0
        except IntegrityError as exc:
            raise KnowledgeIntegrityError(str(exc.orig).strip().splitlines()[0]) from exc
        except DBAPIError as exc:
            raise _translate(exc) from exc
        return inserted

    def embedded_chunk_ids(self, version_id: str, embedding_config_id: str) -> set[str]:
        with self._engine.connect() as conn:
            rows: Any = conn.execute(
                text(
                    "SELECT chunk_id FROM knowledge.embeddings "
                    "WHERE version_id = :v AND embedding_config_id = :e"
                ),
                {"v": version_id, "e": embedding_config_id},
            )
            return {r[0] for r in rows}

    def ensure_ann_index(
        self, config: EmbeddingConfig, method: Literal["hnsw", "ivfflat", "none"] = "hnsw"
    ) -> str | None:
        """Create the partial expression ANN index for one embedding configuration."""
        if method == "none":
            return None
        cid = config.embedding_config_id
        if not _SAFE_NAME.match(cid):
            raise KnowledgeIntegrityError("unsafe embedding configuration identifier")
        name = "ix_kb_emb_" + method + "_" + cid.replace("-", "_").lower()
        opts = "WITH (m = 16, ef_construction = 64)" if method == "hnsw" else "WITH (lists = 100)"
        dim = int(config.dimension)
        with self._engine.begin() as conn:
            if method == "ivfflat":
                rows: Any = conn.execute(
                    text(
                        "SELECT count(*) FROM knowledge.embeddings WHERE embedding_config_id = :e"
                    ),
                    {"e": cid},
                ).scalar_one()
                # lists should be about rows / 1000 (at least 1): far more lists than rows leaves
                # most lists empty and an ANN search then misses almost every row.
                opts = f"WITH (lists = {max(1, int(rows) // 1000)})"
            conn.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {name} ON knowledge.embeddings "
                    f"USING {method} ((embedding::vector({dim})) vector_cosine_ops) {opts} "
                    f"WHERE embedding_config_id = '{cid}'"
                )
            )
        return name

    def nearest(
        self,
        version_id: str,
        embedding_config_id: str,
        vector: Sequence[float],
        top_k: int,
        filters: RetrievalFilters,
    ) -> list[tuple[dict[str, Any], float]]:
        with self._engine.connect() as conn:
            dim: Any = conn.execute(
                text(
                    "SELECT dimension FROM knowledge.embedding_configs "
                    "WHERE embedding_config_id = :e"
                ),
                {"e": embedding_config_id},
            ).scalar_one()
        dim = int(dim)
        clauses = ["e.version_id = :v", "e.embedding_config_id = :e"]
        params: dict[str, Any] = {
            "v": version_id,
            "e": embedding_config_id,
            "q": _vector_literal(vector),
            "k": int(top_k),
        }
        mapping: list[tuple[str, str, Sequence[str]]] = [
            ("c.source_id", "f_source", filters.source_ids),
            ("c.edition_id", "f_edition", filters.edition_ids),
            ("c.methodology_profile", "f_profile", filters.methodology_profiles),
            ("c.language", "f_lang", filters.languages),
            ("c.knowledge_domain", "f_domain", [d.value for d in filters.knowledge_domains]),
            ("c.text_origin", "f_origin", [o.value for o in filters.text_origins]),
            ("c.parent_concept_id", "f_parent", filters.parent_concept_ids),
        ]
        for column, name, values in mapping:
            if values:
                clauses.append(f"{column} = ANY(:{name})")
                params[name] = list(values)
        chunk_cols = ", ".join(f"c.{col}" for col in VERSIONED_TABLES["chunks"].columns)
        inner = (
            f"SELECT {chunk_cols}, "
            f"(e.embedding::vector({dim}) <=> CAST(:q AS vector({dim}))) AS distance "
            "FROM knowledge.embeddings e "
            "JOIN knowledge.chunks c ON c.version_id = e.version_id AND c.chunk_id = e.chunk_id "
            f"WHERE {' AND '.join(clauses)}"
        )
        if self._approximate:
            # the raw ORDER BY keeps the ANN index usable
            sql = text(f"{inner} ORDER BY distance, c.chunk_id LIMIT :k")
        else:
            # ties are decided on the distance rounded to 6 decimals (what a hit reports), then
            # by chunk identifier in byte order, matching the in-memory store exactly
            sql = text(
                f"SELECT * FROM ({inner}) AS t "
                'ORDER BY round(t.distance::numeric, 6), t.chunk_id COLLATE "C" LIMIT :k'
            )
        with self._engine.begin() as conn:
            if self._approximate:
                conn.execute(text(f"SET LOCAL hnsw.ef_search = {max(self._ef_search, int(top_k))}"))
            else:
                conn.execute(text("SET LOCAL enable_indexscan = off"))
            result = conn.execute(sql, params)
            keys = list(result.keys())
            out: list[tuple[dict[str, Any], float]] = []
            for r in result:
                row = dict(zip(keys, r, strict=True))
                distance = float(row.pop("distance"))
                out.append(({k.removeprefix("c."): v for k, v in row.items()}, distance))
            return out

    # -- ingestion runs ----------------------------------------------------------------------
    def record_ingestion_run(
        self,
        version_id: str,
        status: str,
        input_manifest_hash: str,
        counts: Mapping[str, int],
        notes: str,
    ) -> None:
        with self._engine.begin() as conn:
            ingestion_version: Any = conn.execute(
                text(
                    "SELECT ingestion_version FROM knowledge.knowledge_versions "
                    "WHERE version_id = :v"
                ),
                {"v": version_id},
            ).scalar_one()
            conn.execute(
                text(
                    "INSERT INTO knowledge.ingestion_runs (version_id, status, ingestion_version, "
                    "input_manifest_hash, counts, notes) VALUES (:v, :s, :i, :h, "
                    "CAST(:c AS jsonb), :n)"
                ),
                {
                    "v": version_id,
                    "s": status,
                    "i": ingestion_version,
                    "h": input_manifest_hash,
                    "c": json.dumps(dict(counts), sort_keys=True),
                    "n": notes,
                },
            )

    def ingestion_runs(self, version_id: str) -> list[dict[str, Any]]:
        with self._engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT run_id, version_id, status, ingestion_version, input_manifest_hash, "
                    "counts, notes FROM knowledge.ingestion_runs WHERE version_id = :v "
                    "ORDER BY run_id"
                ),
                {"v": version_id},
            )
            return [dict(zip(result.keys(), r, strict=True)) for r in result]
