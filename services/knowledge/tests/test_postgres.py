"""PostgreSQL + pgvector integration (KB-14 to KB-17, KB-35).

Needs a database: set ``KNOWLEDGE_TEST_DATABASE_URL`` (for example
``postgresql+psycopg://pandit:pandit@localhost:55432/pandit``). The tests run the Alembic chain
down to base and back up, then truncate the knowledge tables before each test, so point them at a
scratch database only. They are skipped when the variable is not set.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from pandit_knowledge.content import KnowledgeContent
from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import KnowledgeBuilder, build_rows
from pandit_knowledge.models import (
    ConceptType,
    Confidence,
    IngestionPermission,
    KnowledgeDomain,
    ReadingLevel,
    RetrievalFilters,
    RetrievalQuery,
    RuleKind,
    StatementKind,
    SupportStatus,
    TextFidelity,
    TextOrigin,
)
from pandit_knowledge.retrieval import Retriever
from pandit_knowledge.schema import VERSIONED_TABLES
from pandit_knowledge.store import (
    InMemoryKnowledgeStore,
    KnowledgeIntegrityError,
    SealedVersionError,
)
from pandit_knowledge.validation import verify_version

URL = os.environ.get("KNOWLEDGE_TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(not URL, reason="KNOWLEDGE_TEST_DATABASE_URL is not set"),
]

ALEMBIC_INI = Path(__file__).resolve().parents[3] / "infrastructure" / "migrations" / "alembic.ini"
ALL_TABLES = (
    "ingestion_runs, embeddings, chunks, exceptions, domain_mappings, rule_references, terms, "
    "statements, concepts, source_editions, sources, knowledge_versions, embedding_configs"
)


def _alembic(action: str, revision: str) -> None:
    from alembic import command
    from alembic.config import Config

    os.environ["DATABASE_URL"] = str(URL)
    cfg = Config(str(ALEMBIC_INI))
    getattr(command, action)(cfg, revision)


@pytest.fixture(scope="module")
def engine() -> Iterator[Any]:
    from sqlalchemy import create_engine

    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    eng = create_engine(str(URL))
    yield eng
    eng.dispose()


@pytest.fixture
def pg(engine: Any) -> Any:
    from sqlalchemy import text

    from pandit_knowledge.pg_store import PostgresKnowledgeStore

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE knowledge.{ALL_TABLES.replace(', ', ', knowledge.')} CASCADE"))
    return PostgresKnowledgeStore(engine)


def _rows(engine: Any, sql: str, **params: Any) -> list[tuple[Any, ...]]:
    from sqlalchemy import text

    with engine.connect() as conn:
        return [tuple(r) for r in conn.execute(text(sql), params)]


def _exec(engine: Any, sql: str, **params: Any) -> None:
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text(sql), params)


# ---- migration ------------------------------------------------------------------------------
def test_migration_chain_is_reversible(engine: Any) -> None:
    _alembic("downgrade", "0001_initial_schemas")
    assert _rows(engine, "SELECT to_regclass('knowledge.chunks')")[0][0] is None
    assert _rows(engine, "SELECT 1 FROM pg_namespace WHERE nspname = 'knowledge'")
    assert not _rows(
        engine,
        "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'knowledge'",
    )  # the guard functions are dropped with the tables
    _alembic("upgrade", "head")
    assert _rows(engine, "SELECT to_regclass('knowledge.chunks')")[0][0] is not None


def test_pgvector_extension_is_present(engine: Any) -> None:
    assert _rows(engine, "SELECT extname FROM pg_extension WHERE extname = 'vector'")


def test_python_schema_spec_matches_the_database(engine: Any) -> None:
    for name, spec in VERSIONED_TABLES.items():
        cols = [
            r[0]
            for r in _rows(
                engine,
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'knowledge' AND table_name = :t",
                t=name,
            )
        ]
        assert set(cols) == set(spec.columns), name
        pk = [
            r[0]
            for r in _rows(
                engine,
                "SELECT a.attname FROM pg_index i "
                "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
                "WHERE i.indrelid = CAST(:t AS regclass) AND i.indisprimary",
                t=f"knowledge.{name}",
            )
        ]
        assert set(pk) == set(spec.primary_key), name


def _check_literals(engine: Any, table: str, column: str) -> set[str]:
    rows = _rows(
        engine,
        "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
        "WHERE c.conrelid = CAST(:t AS regclass) AND c.contype = 'c'",
        t=f"knowledge.{table}",
    )
    for (definition,) in rows:
        # PostgreSQL stores "col IN (...)" as: CHECK ((col = ANY (ARRAY['A'::text, ...])))
        if f"(({column} = ANY (ARRAY[" in definition:
            return set(re.findall(r"'([^']+)'::text", definition))
    raise AssertionError(f"no CHECK on {table}.{column}")


def test_check_constraints_match_the_python_vocabularies(engine: Any) -> None:
    expected = {
        ("sources", "ingestion_permission"): IngestionPermission,
        ("source_editions", "reading_level"): ReadingLevel,
        ("statements", "reading_level"): ReadingLevel,
        ("chunks", "reading_level"): ReadingLevel,
        ("concepts", "concept_type"): ConceptType,
        ("statements", "statement_kind"): StatementKind,
        ("statements", "support_status"): SupportStatus,
        ("domain_mappings", "support_status"): SupportStatus,
        ("statements", "confidence"): Confidence,
        ("exceptions", "confidence"): Confidence,
        ("chunks", "confidence"): Confidence,
        ("rule_references", "rule_kind"): RuleKind,
        ("chunks", "knowledge_domain"): KnowledgeDomain,
        ("chunks", "text_origin"): TextOrigin,
        ("chunks", "text_fidelity"): TextFidelity,
    }
    for (table, column), enum in expected.items():
        assert _check_literals(engine, table, column) == {e.value for e in enum}, (table, column)
    assert _check_literals(engine, "statements", "location_kind") == {
        "verse",
        "note",
        "derived",
        "verse_and_note",
    }
    assert _check_literals(engine, "terms", "term_kind") == {"NAME", "ALIAS", "RENDERING"}


# ---- build, parity, idempotence ---------------------------------------------------------------
def test_full_build_in_postgres_is_intact(
    pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    result = KnowledgeBuilder(pg, provider).build(content)
    assert result.outcome == "CREATED"
    assert verify_version(pg, result.version_id) == []
    version = pg.get_version(result.version_id)
    assert version.status == "SEALED"
    for table, n in version.manifest.record_counts.items():
        assert len(pg.select_rows(result.version_id, table)) == n


def test_postgres_and_memory_stores_agree(
    pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    mem = InMemoryKnowledgeStore()
    a = KnowledgeBuilder(mem, provider).build(content)
    b = KnowledgeBuilder(pg, provider).build(content)
    assert a.version_id == b.version_id and a.snapshot_hash == b.snapshot_hash

    def norm(rows: list[dict[str, Any]], pk: tuple[str, ...]) -> dict[Any, str]:
        return {
            tuple(r[c] for c in pk): json.dumps(
                {k: v for k, v in r.items() if k != "version_id"}, sort_keys=True, default=str
            )
            for r in rows
        }

    for table, spec in VERSIONED_TABLES.items():
        assert norm(mem.select_rows(a.version_id, table), spec.primary_key) == norm(
            pg.select_rows(b.version_id, table), spec.primary_key
        ), table


def test_reingest_is_a_noop_and_runs_are_audited(
    pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    builder = KnowledgeBuilder(pg, provider)
    first = builder.build(content)
    second = builder.build(content)
    assert second.outcome == "NOOP" and second.version_id == first.version_id
    assert len(pg.list_versions()) == 1
    assert [r["status"] for r in pg.ingestion_runs(first.version_id)] == [
        "CREATED",
        "NOOP_IDENTICAL",
    ]
    n_chunks = len(pg.select_rows(first.version_id, "chunks"))
    assert _rows(pg._engine, "SELECT count(*) FROM knowledge.embeddings")[0][0] == n_chunks  # noqa: SLF001


def test_interrupted_build_resumes_in_postgres(
    pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    builder = KnowledgeBuilder(pg, provider)
    manifest, parts = builder.manifest_for(content)
    pg.register_embedding_config(provider.config)
    version, outcome = pg.begin_version(manifest)
    assert outcome == "CREATED"
    for table in ("sources", "source_editions", "concepts", "statements"):
        pg.insert_rows(version.version_id, table, parts["rows"][table])
    assert pg.get_version(version.version_id).status == "DRAFT"
    result = builder.build(content)
    assert result.outcome == "RESUMED"
    assert verify_version(pg, result.version_id) == []


def test_two_embedding_dimensions_coexist(
    pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    small = KnowledgeBuilder(pg, provider).build(content)
    big_provider = HashingEmbeddingProvider(512)
    big = KnowledgeBuilder(pg, big_provider).build(content)
    assert small.version_id != big.version_id
    dims = {
        r[0]
        for r in _rows(
            pg._engine, "SELECT DISTINCT vector_dims(embedding) FROM knowledge.embeddings"
        )
    }  # noqa: SLF001
    assert dims == {256, 512}
    for p, v in ((provider, small), (big_provider, big)):
        hit = Retriever(pg, p).retrieve(RetrievalQuery(text="profession", version_id=v.version_id))
        assert hit.hits and hit.hits[0].parent_concept_id == "HOUSE.10"


# ---- immutability and integrity enforced by the database ------------------------------------------
def _built(pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider) -> str:
    return KnowledgeBuilder(pg, provider).build(content).version_id


def test_sealed_version_rejects_writes_through_the_store(
    pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    vid = _built(pg, content, provider)
    rows, chunks = build_rows(content)
    with pytest.raises(SealedVersionError):
        pg.insert_rows(
            vid,
            "concepts",
            rows["concepts"][:1]
            + [
                dict(
                    rows["concepts"][0],
                    concept_id="X.NEW",
                    canonical_key="x",
                    content_hash="a" * 64,
                )
            ],
        )
    vec = provider.embed_documents(["x"])[0]
    with pytest.raises(SealedVersionError):
        pg.insert_embeddings(
            vid,
            provider.config.embedding_config_id,
            [(chunks[0].chunk_id, chunks[0].content_hash(), vec)],
        )


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE knowledge.statements SET source_location = 'tampered'",
        "DELETE FROM knowledge.statements",
        "DELETE FROM knowledge.chunks",
        "UPDATE knowledge.knowledge_versions SET standards_version = '0'",
        "DELETE FROM knowledge.knowledge_versions",
        "UPDATE knowledge.ingestion_runs SET notes = 'x'",
        "DELETE FROM knowledge.ingestion_runs",
        "UPDATE knowledge.embedding_configs SET model = 'x'",
        "UPDATE knowledge.embeddings SET content_hash = repeat('a', 64)",
        "DELETE FROM knowledge.embeddings",
    ],
)
def test_database_triggers_make_sealed_history_immutable(
    pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider, sql: str
) -> None:
    from sqlalchemy.exc import DBAPIError

    _built(pg, content, provider)
    with pytest.raises(DBAPIError, match="sealed|append-only"):
        _exec(pg._engine, sql)  # noqa: SLF001


def test_draft_rows_are_append_only_too(
    pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    from sqlalchemy.exc import DBAPIError

    manifest, parts = KnowledgeBuilder(pg, provider).manifest_for(content)
    pg.register_embedding_config(provider.config)
    version, _ = pg.begin_version(manifest)
    pg.insert_rows(version.version_id, "sources", parts["rows"]["sources"])
    with pytest.raises(DBAPIError, match="append-only"):
        _exec(pg._engine, "UPDATE knowledge.sources SET title = 'x'")  # noqa: SLF001
    with pytest.raises(KnowledgeIntegrityError, match="different content"):
        bad = dict(parts["rows"]["sources"][0], title="other", content_hash="b" * 64)
        pg.insert_rows(version.version_id, "sources", [bad])


def test_a_version_can_only_move_from_draft_to_sealed(
    pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    from sqlalchemy.exc import DBAPIError

    manifest, _ = KnowledgeBuilder(pg, provider).manifest_for(content)
    pg.register_embedding_config(provider.config)
    version, _ = pg.begin_version(manifest)
    with pytest.raises(DBAPIError, match="DRAFT to SEALED"):
        _exec(
            pg._engine,
            "UPDATE knowledge.knowledge_versions SET status = 'DRAFT', standards_version = 'x'",
        )  # noqa: SLF001
    pg.seal_version(version.version_id)
    assert pg.get_version(version.version_id).status == "SEALED"


def test_embedding_triggers_check_dimension_hash_and_configuration(
    pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    builder = KnowledgeBuilder(pg, provider)
    manifest, parts = builder.manifest_for(content)
    pg.register_embedding_config(provider.config)
    version, _ = pg.begin_version(manifest)
    vid = version.version_id
    for table in ("sources", "source_editions", "concepts", "statements", "terms",
                  "rule_references", "domain_mappings", "exceptions", "chunks"):  # fmt: skip
        pg.insert_rows(vid, table, parts["rows"][table])
    chunk = parts["rows"]["chunks"][0]
    cfg = provider.config.embedding_config_id
    good = provider.embed_documents(["x"])[0]
    with pytest.raises(KnowledgeIntegrityError, match="dimension"):
        pg.insert_embeddings(vid, cfg, [(chunk["chunk_id"], chunk["content_hash"], good[:-1])])
    with pytest.raises(KnowledgeIntegrityError, match="content hash"):
        pg.insert_embeddings(vid, cfg, [(chunk["chunk_id"], "f" * 64, good)])
    other = HashingEmbeddingProvider(512)
    pg.register_embedding_config(other.config)
    with pytest.raises(KnowledgeIntegrityError, match="configuration"):
        pg.insert_embeddings(
            vid, other.config.embedding_config_id,
            [(chunk["chunk_id"], chunk["content_hash"], other.embed_documents(["x"])[0])],
        )  # fmt: skip


def test_constraints_reject_bad_rows(pg: Any) -> None:
    from sqlalchemy.exc import DBAPIError, IntegrityError

    _exec(
        pg._engine,  # noqa: SLF001
        "INSERT INTO knowledge.embedding_configs (embedding_config_id, provider, model, "
        "model_version, dimension, metric, config_version, is_semantic, languages_declared, "
        "config_hash) VALUES ('EC-t', 'p', 'm', '1', 4, 'cosine', '1', false, '[]'::jsonb, repeat('a', 64))",
    )
    with pytest.raises(IntegrityError):  # unknown metric
        _exec(
            pg._engine,  # noqa: SLF001
            "INSERT INTO knowledge.embedding_configs (embedding_config_id, provider, model, "
            "model_version, dimension, metric, config_version, is_semantic, languages_declared, "
            "config_hash) VALUES ('EC-u', 'p', 'm', '1', 4, 'dot', '1', false, '[]'::jsonb, repeat('a', 64))",
        )
    with pytest.raises(DBAPIError):  # version row with a malformed hash
        _exec(
            pg._engine,  # noqa: SLF001
            "INSERT INTO knowledge.knowledge_versions (version_id, status, snapshot_hash, "
            "standards_version, schema_version, ingestion_version, chunking_version, "
            "embedding_config_id, manifest) VALUES ('KV-x', 'DRAFT', 'nothex', '1', '1', '1', '1', "
            "'EC-t', '{}'::jsonb)",
        )
    _exec(
        pg._engine,  # noqa: SLF001
        "INSERT INTO knowledge.knowledge_versions (version_id, status, snapshot_hash, "
        "standards_version, schema_version, ingestion_version, chunking_version, "
        "embedding_config_id, manifest) VALUES ('KV-ok', 'DRAFT', repeat('a', 64), '1', '1', '1', "
        "'1', 'EC-t', '{}'::jsonb)",
    )
    with pytest.raises(IntegrityError):  # concept with an unknown type
        _exec(
            pg._engine,  # noqa: SLF001
            "INSERT INTO knowledge.concepts (version_id, concept_id, concept_type, canonical_key, "
            "content_hash) VALUES ('KV-ok', 'X.1', 'NOT_A_TYPE', 'x', repeat('a', 64))",
        )
    with pytest.raises(IntegrityError):  # edition pointing at a missing source
        _exec(
            pg._engine,  # noqa: SLF001
            "INSERT INTO knowledge.source_editions (version_id, edition_id, source_id, "
            "edition_label, translator, publisher, publication_year, language, location_url, "
            "reading_level, registry_verification_level, content_hash) VALUES ('KV-ok', 'E', "
            "'SRC.MISSING', '', '', '', '', 'en', '', 'OCR_LEVEL', 'x', repeat('a', 64))",
        )


# ---- retrieval -------------------------------------------------------------------------------
QUERIES = [
    ("profession livelihood", RetrievalFilters()),
    ("Wheel of Fortune", RetrievalFilters()),
    ("house significator", RetrievalFilters(methodology_profiles=("KB_PHALA_SASTRI_HOUSE_KARAKA_XV_17",))),
    ("love marriage", RetrievalFilters(knowledge_domains=(KnowledgeDomain.TAROT,))),
    ("Sun", RetrievalFilters(source_ids=("SRC.BRIHAT_JATAKA",), languages=("en",))),
    ("significations", RetrievalFilters(parent_concept_ids=("HOUSE.07",), text_origins=(TextOrigin.PROJECT_RENDERING,))),
]  # fmt: skip


@pytest.mark.parametrize(("text", "filters"), QUERIES)
def test_postgres_retrieval_matches_the_reference_store(
    pg: Any,
    content: KnowledgeContent,
    provider: HashingEmbeddingProvider,
    text: str,
    filters: RetrievalFilters,
) -> None:
    mem = InMemoryKnowledgeStore()
    KnowledgeBuilder(mem, provider).build(content)
    vid = _built(pg, content, provider)
    q = RetrievalQuery(text=text, top_k=10, max_distance=1.0, filters=filters)
    a = Retriever(mem, provider).retrieve(q)
    b = Retriever(pg, provider).retrieve(q)
    assert [h.chunk_id for h in a.hits] == [h.chunk_id for h in b.hits]
    for x, y in zip(a.hits, b.hits, strict=True):
        assert abs(x.distance - y.distance) < 1e-4
        assert x.knowledge_version_id == y.knowledge_version_id == vid
        assert x.content_hash == y.content_hash


def test_postgres_filters_exclude_everything_else(
    pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    _built(pg, content, provider)
    r = Retriever(pg, provider)
    hits = r.retrieve(
        RetrievalQuery(
            text="house", top_k=50, max_distance=1.0, filters=RetrievalFilters(languages=("hi",))
        )
    )
    assert hits.hits == ()
    only_waite = r.retrieve(
        RetrievalQuery(
            text="king queen",
            top_k=50,
            max_distance=1.0,
            filters=RetrievalFilters(source_ids=("SRC.WAITE_PICTORIAL_KEY",)),
        )
    )
    assert only_waite.hits and {h.source_id for h in only_waite.hits} == {"SRC.WAITE_PICTORIAL_KEY"}


def test_ann_index_is_created_per_configuration_and_is_usable(
    pg: Any, content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    from sqlalchemy import text

    vid = _built(pg, content, provider)
    name = pg.ensure_ann_index(provider.config, "hnsw")
    assert pg.ensure_ann_index(provider.config, "hnsw") == name  # idempotent
    assert _rows(pg._engine, "SELECT indexdef FROM pg_indexes WHERE indexname = :n", n=name)  # noqa: SLF001
    indexdef = _rows(pg._engine, "SELECT indexdef FROM pg_indexes WHERE indexname = :n", n=name)[0][
        0
    ]  # noqa: SLF001
    assert "hnsw" in indexdef and "vector_cosine_ops" in indexdef and "WHERE" in indexdef
    assert pg.ensure_ann_index(provider.config, "none") is None
    ivf = pg.ensure_ann_index(provider.config, "ivfflat")
    assert ivf and ivf != name
    vec = "[" + ",".join(str(x) for x in provider.embed_query("profession")) + "]"
    cid = provider.config.embedding_config_id
    with pg._engine.begin() as conn:  # noqa: SLF001
        conn.execute(text("SET LOCAL enable_seqscan = off"))
        conn.execute(text("SET LOCAL enable_bitmapscan = off"))
        plan = "\n".join(
            r[0]
            for r in conn.execute(
                text(
                    "EXPLAIN SELECT chunk_id FROM knowledge.embeddings "
                    f"WHERE embedding_config_id = '{cid}' "
                    f"ORDER BY embedding::vector(256) <=> '{vec}'::vector(256) LIMIT 5"
                )
            )
        )
    assert "ix_kb_emb_" in plan, plan
    # exact mode (the default): an index can never lower recall
    exact = Retriever(pg, provider).retrieve(RetrievalQuery(text="profession", version_id=vid))
    assert exact.hits[0].parent_concept_id == "HOUSE.10"
    assert "APPROXIMATE_INDEX_SEARCH" not in exact.notes
    from pandit_knowledge.pg_store import PostgresKnowledgeStore

    approx_store = PostgresKnowledgeStore(pg._engine, approximate=True)  # noqa: SLF001
    approx = Retriever(approx_store, provider).retrieve(
        RetrievalQuery(text="profession", version_id=vid)
    )
    assert "APPROXIMATE_INDEX_SEARCH" in approx.notes
    assert approx.hits and approx.hits[0].parent_concept_id == "HOUSE.10"


def test_unsafe_index_identifier_is_refused(pg: Any, provider: HashingEmbeddingProvider) -> None:
    from pandit_knowledge.models import EmbeddingConfig

    class Evil(EmbeddingConfig):
        @property
        def embedding_config_id(self) -> str:
            return "EC-x'; DROP TABLE knowledge.chunks; --"

    evil = Evil(
        provider="p",
        model="m",
        model_version="1",
        dimension=4,
        config_version="1",
        is_semantic=False,
    )
    with pytest.raises(KnowledgeIntegrityError, match="unsafe"):
        pg.ensure_ann_index(evil, "hnsw")
