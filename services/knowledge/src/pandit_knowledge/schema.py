"""Table specifications shared by every store (KB-14 to KB-17).

The PostgreSQL migration (`infrastructure/migrations/versions/0002_knowledge_schema.py`) is the
DDL source of truth. This module mirrors its column lists so the in-memory store enforces the
same keys and the PostgreSQL store can build statements; a test compares the two against
`information_schema` so they cannot drift.
"""

from __future__ import annotations

from dataclasses import dataclass

SCHEMA = "knowledge"


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[str, ...]
    primary_key: tuple[str, ...]
    json_columns: tuple[str, ...] = ()
    # (columns, referenced table) -- every foreign key is composite on (version_id, ...).
    foreign_keys: tuple[tuple[tuple[str, ...], str], ...] = ()
    versioned: bool = True


SOURCES = TableSpec(
    "sources",
    (
        "version_id",
        "source_id",
        "title",
        "author",
        "tradition",
        "original_language",
        "source_classification",
        "copyright_status",
        "ingestion_permission",
        "copyright_note",
        "registry_ref",
        "content_hash",
    ),
    ("version_id", "source_id"),
)
EDITIONS = TableSpec(
    "source_editions",
    (
        "version_id",
        "edition_id",
        "source_id",
        "edition_label",
        "translator",
        "publisher",
        "publication_year",
        "language",
        "location_url",
        "reading_level",
        "registry_verification_level",
        "content_hash",
    ),
    ("version_id", "edition_id"),
    foreign_keys=((("version_id", "source_id"), "sources"),),
)
CONCEPTS = TableSpec(
    "concepts",
    ("version_id", "concept_id", "concept_type", "canonical_key", "content_hash"),
    ("version_id", "concept_id"),
)
STATEMENTS = TableSpec(
    "statements",
    (
        "version_id",
        "statement_id",
        "concept_id",
        "statement_kind",
        "profile_id",
        "edition_id",
        "source_location",
        "location_kind",
        "reading_level",
        "registry_verification_level",
        "confidence",
        "support_status",
        "language",
        "attributes",
        "content_hash",
    ),
    ("version_id", "statement_id"),
    json_columns=("attributes",),
    foreign_keys=(
        (("version_id", "concept_id"), "concepts"),
        (("version_id", "edition_id"), "source_editions"),
    ),
)
TERMS = TableSpec(
    "terms",
    (
        "version_id",
        "term_id",
        "concept_id",
        "term_kind",
        "script",
        "language",
        "text",
        "profile_id",
        "edition_id",
        "source_location",
        "verification_status",
        "content_hash",
    ),
    ("version_id", "term_id"),
    foreign_keys=(
        (("version_id", "concept_id"), "concepts"),
        (("version_id", "edition_id"), "source_editions"),
    ),
)
RULE_REFERENCES = TableSpec(
    "rule_references",
    (
        "version_id",
        "reference_id",
        "concept_id",
        "rule_id",
        "rule_kind",
        "relation",
        "profile_id",
        "source_location",
        "content_hash",
    ),
    ("version_id", "reference_id"),
    foreign_keys=((("version_id", "concept_id"), "concepts"),),
)
DOMAIN_MAPPINGS = TableSpec(
    "domain_mappings",
    (
        "version_id",
        "mapping_id",
        "domain_id",
        "concept_id",
        "support_status",
        "supporting_statement_ids",
        "profile_id",
        "bridge_note",
        "content_hash",
    ),
    ("version_id", "mapping_id"),
    json_columns=("supporting_statement_ids",),
    foreign_keys=(
        (("version_id", "domain_id"), "concepts"),
        (("version_id", "concept_id"), "concepts"),
    ),
)
EXCEPTIONS = TableSpec(
    "exceptions",
    (
        "version_id",
        "exception_id",
        "affected_rule_id",
        "affected_concept_id",
        "profile_id",
        "edition_id",
        "source_location",
        "condition_summary",
        "effect",
        "confidence",
        "conflict_note",
        "content_hash",
    ),
    ("version_id", "exception_id"),
    foreign_keys=(
        (("version_id", "affected_concept_id"), "concepts"),
        (("version_id", "edition_id"), "source_editions"),
    ),
)
CHUNKS = TableSpec(
    "chunks",
    (
        "version_id",
        "chunk_id",
        "knowledge_domain",
        "text",
        "language",
        "text_origin",
        "text_fidelity",
        "source_id",
        "edition_id",
        "source_location",
        "section_path",
        "sequence",
        "parent_concept_id",
        "methodology_profile",
        "reading_level",
        "confidence",
        "external_ref",
        "chunking_version",
        "char_count",
        "content_hash",
    ),
    ("version_id", "chunk_id"),
    foreign_keys=(
        (("version_id", "edition_id"), "source_editions"),
        (("version_id", "parent_concept_id"), "concepts"),
    ),
)

VERSIONED_TABLES: dict[str, TableSpec] = {
    t.name: t
    for t in (
        SOURCES,
        EDITIONS,
        CONCEPTS,
        STATEMENTS,
        TERMS,
        RULE_REFERENCES,
        DOMAIN_MAPPINGS,
        EXCEPTIONS,
        CHUNKS,
    )
}

# Insert order that satisfies every foreign key.
INSERT_ORDER: tuple[str, ...] = (
    "sources",
    "source_editions",
    "concepts",
    "statements",
    "terms",
    "rule_references",
    "domain_mappings",
    "exceptions",
    "chunks",
)

VERSION_COLUMNS = (
    "version_id",
    "status",
    "snapshot_hash",
    "standards_version",
    "schema_version",
    "ingestion_version",
    "chunking_version",
    "embedding_config_id",
    "manifest",
)
EMBEDDING_CONFIG_COLUMNS = (
    "embedding_config_id",
    "provider",
    "model",
    "model_version",
    "dimension",
    "metric",
    "config_version",
    "is_semantic",
    "languages_declared",
    "config_hash",
)
EMBEDDING_COLUMNS = (
    "version_id",
    "chunk_id",
    "embedding_config_id",
    "content_hash",
    "embedding",
)
INGESTION_RUN_COLUMNS = (
    "run_id",
    "version_id",
    "status",
    "ingestion_version",
    "input_manifest_hash",
    "counts",
    "notes",
)
