"""Knowledge schema (Phase 12): sources, concepts, statements, terms, rule references,
domain mappings, exceptions, chunks, embeddings and versions.

Forward-only migration on top of ``0001_initial_schemas`` (which already created the
``knowledge`` schema and the ``vector`` extension). Design (``docs/ARCHITECTURE.md`` section
"Knowledge Architecture", ``docs/ASTROLOGY_STANDARDS.md`` v1.26.0 KB-14 to KB-17):

* every record row belongs to one *knowledge version* and is keyed ``(version_id, natural key)``;
* a ``SEALED`` version is immutable: triggers reject every insert, update and delete in it, and
  record rows are never updated at all (append-only), so history cannot be rewritten silently;
* all foreign keys are composite on ``(version_id, ...)`` so a version never points into another;
* embeddings live in their own table with an untyped ``vector`` column (the dimension belongs to
  the embedding configuration, so the model can change without a table change) and a trigger that
  checks the dimension, the chunk's content hash and the version's configuration;
* no ANN index is created here: the index strategy is configurable per embedding configuration
  (``PostgresKnowledgeStore.ensure_ann_index``), because Phase 14 may replace the model.

Revision ID: 0002_knowledge_schema
Revises: 0001_initial_schemas
Create Date: 2026-10-01
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_knowledge_schema"
down_revision: str | None = "0001_initial_schemas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

HASH = "CHECK (content_hash ~ '^[0-9a-f]{64}$')"

TABLES_DDL = [
    # ---------------------------------------------------------------- embedding configurations
    """
    CREATE TABLE knowledge.embedding_configs (
        embedding_config_id text PRIMARY KEY,
        provider text NOT NULL,
        model text NOT NULL,
        model_version text NOT NULL,
        dimension integer NOT NULL CHECK (dimension > 0),
        metric text NOT NULL CHECK (metric IN ('cosine')),
        config_version text NOT NULL,
        is_semantic boolean NOT NULL,
        languages_declared jsonb NOT NULL,
        config_hash text NOT NULL CHECK (config_hash ~ '^[0-9a-f]{64}$'),
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    # ---------------------------------------------------------------- versions
    """
    CREATE TABLE knowledge.knowledge_versions (
        version_id text PRIMARY KEY,
        status text NOT NULL CHECK (status IN ('DRAFT', 'SEALED')),
        snapshot_hash text NOT NULL UNIQUE CHECK (snapshot_hash ~ '^[0-9a-f]{64}$'),
        standards_version text NOT NULL,
        schema_version text NOT NULL,
        ingestion_version text NOT NULL,
        chunking_version text NOT NULL,
        embedding_config_id text NOT NULL
            REFERENCES knowledge.embedding_configs (embedding_config_id),
        manifest jsonb NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        sealed_at timestamptz,
        CHECK ((status = 'SEALED') = (sealed_at IS NOT NULL))
    )
    """,
    # ---------------------------------------------------------------- sources and editions
    f"""
    CREATE TABLE knowledge.sources (
        version_id text NOT NULL REFERENCES knowledge.knowledge_versions (version_id),
        source_id text NOT NULL,
        title text NOT NULL,
        author text NOT NULL,
        tradition text NOT NULL,
        original_language text NOT NULL,
        source_classification text NOT NULL,
        copyright_status text NOT NULL,
        ingestion_permission text NOT NULL CHECK (ingestion_permission IN (
            'FACTS_AND_CITATIONS_ONLY', 'FULL_TEXT_PUBLIC_DOMAIN', 'LOCATION_ONLY',
            'DEFERRED_UNRESOLVED')),
        copyright_note text NOT NULL,
        registry_ref text NOT NULL,
        content_hash text NOT NULL {HASH},
        PRIMARY KEY (version_id, source_id)
    )
    """,
    f"""
    CREATE TABLE knowledge.source_editions (
        version_id text NOT NULL REFERENCES knowledge.knowledge_versions (version_id),
        edition_id text NOT NULL,
        source_id text NOT NULL,
        edition_label text NOT NULL,
        translator text NOT NULL,
        publisher text NOT NULL,
        publication_year text NOT NULL,
        language text NOT NULL,
        location_url text NOT NULL,
        reading_level text NOT NULL CHECK (reading_level IN (
            'SANSKRIT_LEVEL', 'TRANSLATION_LEVEL', 'PAGE_IMAGE_LEVEL', 'OCR_LEVEL',
            'TRANSCRIPTION_LEVEL', 'SECONDARY_REFERENCE', 'NOT_APPLICABLE')),
        registry_verification_level text NOT NULL,
        content_hash text NOT NULL {HASH},
        PRIMARY KEY (version_id, edition_id),
        FOREIGN KEY (version_id, source_id) REFERENCES knowledge.sources (version_id, source_id)
    )
    """,
    # ---------------------------------------------------------------- concepts
    f"""
    CREATE TABLE knowledge.concepts (
        version_id text NOT NULL REFERENCES knowledge.knowledge_versions (version_id),
        concept_id text NOT NULL,
        concept_type text NOT NULL CHECK (concept_type IN (
            'PLANET', 'HOUSE', 'DOMAIN', 'TERM', 'TAROT_CARD', 'CONCEPT')),
        canonical_key text NOT NULL,
        content_hash text NOT NULL {HASH},
        PRIMARY KEY (version_id, concept_id)
    )
    """,
    # ---------------------------------------------------------------- statements
    f"""
    CREATE TABLE knowledge.statements (
        version_id text NOT NULL REFERENCES knowledge.knowledge_versions (version_id),
        statement_id text NOT NULL,
        concept_id text NOT NULL,
        statement_kind text NOT NULL CHECK (statement_kind IN (
            'SIGNIFICATION', 'ROLE', 'HOUSE_KARAKA', 'DERIVED_INVERSION', 'STRENGTH_NOTE',
            'SOURCE_VARIANCE')),
        profile_id text NOT NULL,
        edition_id text NOT NULL,
        source_location text NOT NULL,
        location_kind text NOT NULL CHECK (location_kind IN (
            'verse', 'note', 'derived', 'verse_and_note')),
        reading_level text NOT NULL CHECK (reading_level IN (
            'SANSKRIT_LEVEL', 'TRANSLATION_LEVEL', 'PAGE_IMAGE_LEVEL', 'OCR_LEVEL',
            'TRANSCRIPTION_LEVEL', 'SECONDARY_REFERENCE', 'NOT_APPLICABLE')),
        registry_verification_level text NOT NULL,
        confidence text NOT NULL CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW')),
        support_status text NOT NULL CHECK (support_status IN (
            'SOURCE_SUPPORTED', 'PROJECT_DERIVED', 'UNRESOLVED_CONFLICT', 'NOT_EVALUABLE')),
        language text NOT NULL,
        attributes jsonb NOT NULL,
        content_hash text NOT NULL {HASH},
        PRIMARY KEY (version_id, statement_id),
        FOREIGN KEY (version_id, concept_id) REFERENCES knowledge.concepts (version_id, concept_id),
        FOREIGN KEY (version_id, edition_id)
            REFERENCES knowledge.source_editions (version_id, edition_id)
    )
    """,
    # ---------------------------------------------------------------- terms
    f"""
    CREATE TABLE knowledge.terms (
        version_id text NOT NULL REFERENCES knowledge.knowledge_versions (version_id),
        term_id text NOT NULL,
        concept_id text NOT NULL,
        term_kind text NOT NULL CHECK (term_kind IN ('NAME', 'ALIAS', 'RENDERING')),
        script text NOT NULL,
        language text NOT NULL,
        text text NOT NULL,
        profile_id text NOT NULL,
        edition_id text NOT NULL,
        source_location text NOT NULL,
        verification_status text NOT NULL,
        content_hash text NOT NULL {HASH},
        PRIMARY KEY (version_id, term_id),
        FOREIGN KEY (version_id, concept_id) REFERENCES knowledge.concepts (version_id, concept_id),
        FOREIGN KEY (version_id, edition_id)
            REFERENCES knowledge.source_editions (version_id, edition_id)
    )
    """,
    # ---------------------------------------------------------------- rule references
    f"""
    CREATE TABLE knowledge.rule_references (
        version_id text NOT NULL REFERENCES knowledge.knowledge_versions (version_id),
        reference_id text NOT NULL,
        concept_id text NOT NULL,
        rule_id text NOT NULL,
        rule_kind text NOT NULL CHECK (rule_kind IN ('RULE', 'TABLE', 'PROFILE')),
        relation text NOT NULL,
        profile_id text NOT NULL,
        source_location text NOT NULL,
        content_hash text NOT NULL {HASH},
        PRIMARY KEY (version_id, reference_id),
        FOREIGN KEY (version_id, concept_id) REFERENCES knowledge.concepts (version_id, concept_id)
    )
    """,
    # ---------------------------------------------------------------- domain mappings
    f"""
    CREATE TABLE knowledge.domain_mappings (
        version_id text NOT NULL REFERENCES knowledge.knowledge_versions (version_id),
        mapping_id text NOT NULL,
        domain_id text NOT NULL,
        concept_id text NOT NULL,
        support_status text NOT NULL CHECK (support_status IN (
            'SOURCE_SUPPORTED', 'PROJECT_DERIVED', 'UNRESOLVED_CONFLICT', 'NOT_EVALUABLE')),
        supporting_statement_ids jsonb NOT NULL,
        profile_id text NOT NULL,
        bridge_note text NOT NULL,
        content_hash text NOT NULL {HASH},
        PRIMARY KEY (version_id, mapping_id),
        FOREIGN KEY (version_id, domain_id) REFERENCES knowledge.concepts (version_id, concept_id),
        FOREIGN KEY (version_id, concept_id) REFERENCES knowledge.concepts (version_id, concept_id)
    )
    """,
    # ---------------------------------------------------------------- exceptions
    f"""
    CREATE TABLE knowledge.exceptions (
        version_id text NOT NULL REFERENCES knowledge.knowledge_versions (version_id),
        exception_id text NOT NULL,
        affected_rule_id text NOT NULL,
        affected_concept_id text NOT NULL,
        profile_id text NOT NULL,
        edition_id text NOT NULL,
        source_location text NOT NULL,
        condition_summary text NOT NULL,
        effect text NOT NULL,
        confidence text NOT NULL CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW')),
        conflict_note text NOT NULL,
        content_hash text NOT NULL {HASH},
        PRIMARY KEY (version_id, exception_id),
        FOREIGN KEY (version_id, affected_concept_id)
            REFERENCES knowledge.concepts (version_id, concept_id),
        FOREIGN KEY (version_id, edition_id)
            REFERENCES knowledge.source_editions (version_id, edition_id)
    )
    """,
    # ---------------------------------------------------------------- chunks
    f"""
    CREATE TABLE knowledge.chunks (
        version_id text NOT NULL REFERENCES knowledge.knowledge_versions (version_id),
        chunk_id text NOT NULL,
        knowledge_domain text NOT NULL CHECK (knowledge_domain IN ('VEDIC', 'TAROT')),
        text text NOT NULL CHECK (length(text) > 0),
        language text NOT NULL,
        text_origin text NOT NULL CHECK (text_origin IN (
            'SOURCE_TEXT', 'SOURCE_TERMS', 'PROJECT_RENDERING')),
        text_fidelity text NOT NULL CHECK (text_fidelity IN (
            'PROOFREAD_TRANSCRIPTION', 'OCR_UNCORRECTED', 'TEMPLATE_RENDERING')),
        source_id text NOT NULL,
        edition_id text NOT NULL,
        source_location text NOT NULL,
        section_path text NOT NULL,
        sequence integer NOT NULL CHECK (sequence >= 0),
        parent_concept_id text NOT NULL,
        methodology_profile text NOT NULL,
        reading_level text NOT NULL CHECK (reading_level IN (
            'SANSKRIT_LEVEL', 'TRANSLATION_LEVEL', 'PAGE_IMAGE_LEVEL', 'OCR_LEVEL',
            'TRANSCRIPTION_LEVEL', 'SECONDARY_REFERENCE', 'NOT_APPLICABLE')),
        confidence text NOT NULL CHECK (confidence IN ('HIGH', 'MEDIUM', 'LOW')),
        external_ref text NOT NULL,
        chunking_version text NOT NULL,
        char_count integer NOT NULL CHECK (char_count = length(text)),
        content_hash text NOT NULL {HASH},
        PRIMARY KEY (version_id, chunk_id),
        FOREIGN KEY (version_id, edition_id)
            REFERENCES knowledge.source_editions (version_id, edition_id),
        FOREIGN KEY (version_id, parent_concept_id)
            REFERENCES knowledge.concepts (version_id, concept_id)
    )
    """,
    # ---------------------------------------------------------------- embeddings
    """
    CREATE TABLE knowledge.embeddings (
        version_id text NOT NULL,
        chunk_id text NOT NULL,
        embedding_config_id text NOT NULL
            REFERENCES knowledge.embedding_configs (embedding_config_id),
        content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
        embedding vector NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (version_id, chunk_id, embedding_config_id),
        FOREIGN KEY (version_id, chunk_id) REFERENCES knowledge.chunks (version_id, chunk_id)
    )
    """,
    # ---------------------------------------------------------------- ingestion runs
    """
    CREATE TABLE knowledge.ingestion_runs (
        run_id bigserial PRIMARY KEY,
        version_id text NOT NULL REFERENCES knowledge.knowledge_versions (version_id),
        status text NOT NULL CHECK (status IN (
            'CREATED', 'RESUMED', 'NOOP_IDENTICAL')),
        ingestion_version text NOT NULL,
        input_manifest_hash text NOT NULL CHECK (input_manifest_hash ~ '^[0-9a-f]{64}$'),
        counts jsonb NOT NULL,
        notes text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
]

INDEXES = [
    ("ix_knowledge_statements_concept", "statements", "version_id, concept_id"),
    ("ix_knowledge_terms_concept", "terms", "version_id, concept_id"),
    ("ix_knowledge_rule_refs_rule", "rule_references", "version_id, rule_id"),
    ("ix_knowledge_rule_refs_concept", "rule_references", "version_id, concept_id"),
    ("ix_knowledge_mappings_domain", "domain_mappings", "version_id, domain_id"),
    ("ix_knowledge_exceptions_rule", "exceptions", "version_id, affected_rule_id"),
    ("ix_knowledge_chunks_domain_lang", "chunks", "version_id, knowledge_domain, language"),
    ("ix_knowledge_chunks_source", "chunks", "version_id, source_id"),
    ("ix_knowledge_chunks_profile", "chunks", "version_id, methodology_profile"),
    ("ix_knowledge_chunks_parent", "chunks", "version_id, parent_concept_id"),
    ("ix_knowledge_embeddings_config", "embeddings", "embedding_config_id"),
]

VERSIONED = [
    "sources",
    "source_editions",
    "concepts",
    "statements",
    "terms",
    "rule_references",
    "domain_mappings",
    "exceptions",
    "chunks",
]

FUNCTIONS = [
    # Record rows: append-only; nothing in a SEALED version changes at all.
    """
    CREATE FUNCTION knowledge.guard_record_row() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
        vid text;
        st text;
    BEGIN
        IF TG_OP = 'UPDATE' THEN
            RAISE EXCEPTION 'knowledge rows are append-only (table %)', TG_TABLE_NAME;
        END IF;
        IF TG_OP = 'DELETE' THEN
            vid := OLD.version_id;
        ELSE
            vid := NEW.version_id;
        END IF;
        SELECT status INTO st FROM knowledge.knowledge_versions WHERE version_id = vid;
        IF st = 'SEALED' THEN
            RAISE EXCEPTION 'knowledge version % is sealed', vid;
        END IF;
        IF TG_OP = 'DELETE' THEN
            RETURN OLD;
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    # Embeddings: same sealing rule, plus dimension, content hash and configuration checks.
    """
    CREATE FUNCTION knowledge.guard_embedding_row() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE
        st text;
        cfg text;
        dim integer;
        chunk_hash text;
    BEGIN
        IF TG_OP = 'UPDATE' THEN
            RAISE EXCEPTION 'knowledge rows are append-only (table %)', TG_TABLE_NAME;
        END IF;
        IF TG_OP = 'DELETE' THEN
            SELECT status INTO st FROM knowledge.knowledge_versions
                WHERE version_id = OLD.version_id;
            IF st = 'SEALED' THEN
                RAISE EXCEPTION 'knowledge version % is sealed', OLD.version_id;
            END IF;
            RETURN OLD;
        END IF;
        SELECT status, embedding_config_id INTO st, cfg
            FROM knowledge.knowledge_versions WHERE version_id = NEW.version_id;
        IF st = 'SEALED' THEN
            RAISE EXCEPTION 'knowledge version % is sealed', NEW.version_id;
        END IF;
        IF cfg IS DISTINCT FROM NEW.embedding_config_id THEN
            RAISE EXCEPTION 'embedding configuration is not the one of version %', NEW.version_id;
        END IF;
        SELECT dimension INTO dim FROM knowledge.embedding_configs
            WHERE embedding_config_id = NEW.embedding_config_id;
        IF vector_dims(NEW.embedding) <> dim THEN
            RAISE EXCEPTION 'embedding dimension % does not match configured %',
                vector_dims(NEW.embedding), dim;
        END IF;
        SELECT content_hash INTO chunk_hash FROM knowledge.chunks
            WHERE version_id = NEW.version_id AND chunk_id = NEW.chunk_id;
        IF chunk_hash IS DISTINCT FROM NEW.content_hash THEN
            RAISE EXCEPTION 'embedding content hash does not match chunk %', NEW.chunk_id;
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    # Versions: DRAFT -> SEALED only; a SEALED version never changes and is never deleted.
    """
    CREATE FUNCTION knowledge.guard_version_row() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF TG_OP = 'DELETE' THEN
            IF OLD.status = 'SEALED' THEN
                RAISE EXCEPTION 'knowledge version % is sealed', OLD.version_id;
            END IF;
            RETURN OLD;
        END IF;
        IF OLD.status = 'SEALED' THEN
            RAISE EXCEPTION 'knowledge version % is sealed', OLD.version_id;
        END IF;
        IF NEW.status <> 'SEALED'
           OR NEW.version_id <> OLD.version_id
           OR NEW.snapshot_hash <> OLD.snapshot_hash
           OR NEW.embedding_config_id <> OLD.embedding_config_id
           OR NEW.manifest <> OLD.manifest THEN
            RAISE EXCEPTION 'a knowledge version may only move from DRAFT to SEALED';
        END IF;
        RETURN NEW;
    END;
    $$
    """,
    # Ingestion runs and embedding configurations: audit trail, never edited.
    """
    CREATE FUNCTION knowledge.guard_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'table % is append-only', TG_TABLE_NAME;
    END;
    $$
    """,
]


def upgrade() -> None:
    for ddl in TABLES_DDL:
        op.execute(ddl)
    for name, table, columns in INDEXES:
        op.execute(f"CREATE INDEX {name} ON knowledge.{table} ({columns})")
    for fn in FUNCTIONS:
        op.execute(fn)
    for table in VERSIONED:
        op.execute(
            f"CREATE TRIGGER trg_{table}_guard BEFORE INSERT OR UPDATE OR DELETE "
            f"ON knowledge.{table} FOR EACH ROW EXECUTE FUNCTION knowledge.guard_record_row()"
        )
    op.execute(
        "CREATE TRIGGER trg_embeddings_guard BEFORE INSERT OR UPDATE OR DELETE "
        "ON knowledge.embeddings FOR EACH ROW EXECUTE FUNCTION knowledge.guard_embedding_row()"
    )
    op.execute(
        "CREATE TRIGGER trg_versions_guard BEFORE UPDATE OR DELETE "
        "ON knowledge.knowledge_versions FOR EACH ROW "
        "EXECUTE FUNCTION knowledge.guard_version_row()"
    )
    op.execute(
        "CREATE TRIGGER trg_runs_guard BEFORE UPDATE OR DELETE "
        "ON knowledge.ingestion_runs FOR EACH ROW EXECUTE FUNCTION knowledge.guard_append_only()"
    )
    op.execute(
        "CREATE TRIGGER trg_configs_guard BEFORE UPDATE OR DELETE "
        "ON knowledge.embedding_configs FOR EACH ROW EXECUTE FUNCTION knowledge.guard_append_only()"
    )


def downgrade() -> None:
    # Dropping the tables drops their triggers; functions are dropped explicitly.
    for table in (
        "ingestion_runs",
        "embeddings",
        "chunks",
        "exceptions",
        "domain_mappings",
        "rule_references",
        "terms",
        "statements",
        "concepts",
        "source_editions",
        "sources",
        "knowledge_versions",
        "embedding_configs",
    ):
        op.execute(f"DROP TABLE IF EXISTS knowledge.{table} CASCADE")
    for fn in (
        "guard_record_row",
        "guard_embedding_row",
        "guard_version_row",
        "guard_append_only",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS knowledge.{fn}()")
