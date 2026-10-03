"""Palmistry knowledge vocabulary (Phase 13): additive, forward-only, no data touched.

Extends five CHECK vocabularies of the ``knowledge`` schema so the palmistry knowledge version
(built by the same ingestion into the same tables) can be stored:

* ``concepts.concept_type``: + ``PALM_LINE``, ``PALM_REGION``, ``PALM_FEATURE``;
* ``statements.statement_kind``: + ``LOCATION_DEFINITION``, ``READING_CONVENTION``, ``COVERAGE``;
* ``statements.location_kind``: + ``paragraph``, ``chapter``, ``page`` (the palmistry sources are
  books cited by paragraph, chapter and page, not by verse);
* ``rule_references.rule_kind``: + ``PALM_RULE``;
* ``chunks.knowledge_domain``: + ``PALMISTRY``.

Nothing else changes: no table, column, trigger, row or index is added, altered or removed, so
the Phase 12 knowledge version ``KV-06361d7aba28c1ce`` (a snapshot of rows and versions, not of
these constraints) is untouched, and sealed versions stay immutable. The palm knowledge content
is a *separate* knowledge version created by the ingestion; this migration only allows its
vocabulary.

``downgrade`` restores the Phase 12 vocabularies as ``NOT VALID`` constraints: they apply to new
rows only, so a database that already holds a palm version is not rewritten (rows in a sealed
version cannot be edited), and the next ``upgrade`` replaces them again.

Revision ID: 0003_palm_knowledge_vocabulary
Revises: 0002_knowledge_schema
Create Date: 2026-10-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_palm_knowledge_vocabulary"
down_revision: str | None = "0002_knowledge_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, column, Phase 12 values, values added by this migration)
VOCABULARIES: tuple[tuple[str, str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "concepts",
        "concept_type",
        ("PLANET", "HOUSE", "DOMAIN", "TERM", "TAROT_CARD", "CONCEPT"),
        ("PALM_LINE", "PALM_REGION", "PALM_FEATURE"),
    ),
    (
        "statements",
        "statement_kind",
        (
            "SIGNIFICATION",
            "ROLE",
            "HOUSE_KARAKA",
            "DERIVED_INVERSION",
            "STRENGTH_NOTE",
            "SOURCE_VARIANCE",
        ),
        ("LOCATION_DEFINITION", "READING_CONVENTION", "COVERAGE"),
    ),
    (
        "statements",
        "location_kind",
        ("verse", "note", "derived", "verse_and_note"),
        ("paragraph", "chapter", "page"),
    ),
    ("rule_references", "rule_kind", ("RULE", "TABLE", "PROFILE"), ("PALM_RULE",)),
    ("chunks", "knowledge_domain", ("VEDIC", "TAROT"), ("PALMISTRY",)),
)


def _in_list(values: Sequence[str]) -> str:
    return ", ".join("'" + v + "'" for v in values)


def _drop_vocabulary_checks(table: str, column: str) -> None:
    """Drop the CHECK constraint(s) of one column, found by definition (names may differ)."""
    op.execute(
        f"""
        DO $$
        DECLARE c record;
        BEGIN
            FOR c IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'knowledge.{table}'::regclass AND contype = 'c'
                  AND pg_get_constraintdef(oid) LIKE '%({column} = ANY%'
            LOOP
                EXECUTE format('ALTER TABLE knowledge.{table} DROP CONSTRAINT %I', c.conname);
            END LOOP;
        END
        $$
        """
    )


def upgrade() -> None:
    for table, column, old, added in VOCABULARIES:
        _drop_vocabulary_checks(table, column)
        op.execute(
            f"ALTER TABLE knowledge.{table} ADD CONSTRAINT {table}_{column}_check "
            f"CHECK ({column} IN ({_in_list(old + added)}))"
        )


def downgrade() -> None:
    for table, column, old, _added in VOCABULARIES:
        _drop_vocabulary_checks(table, column)
        op.execute(
            f"ALTER TABLE knowledge.{table} ADD CONSTRAINT {table}_{column}_check "
            f"CHECK ({column} IN ({_in_list(old)})) NOT VALID"
        )
