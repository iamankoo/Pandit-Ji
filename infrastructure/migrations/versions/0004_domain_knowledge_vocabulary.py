"""Life-domain knowledge vocabulary (Phase 17): additive, forward-only, no data touched.

Extends five CHECK vocabularies of the ``knowledge`` schema so the Phase 17 domain methodology
knowledge version (built by the same ingestion into the same tables) can be stored:

* ``concepts.concept_type``: + ``VARGA`` (a divisional chart);
* ``statements.statement_kind``: + ``DOMAIN_DEFINITION``, ``VARGA_USE``, ``POLICY_NOTE``;
* ``statements.support_status`` and ``domain_mappings.support_status``: + ``PARTIALLY_SUPPORTED``
  (a mapping a source supports only in part; never treated as ``SOURCE_SUPPORTED``);
* ``rule_references.rule_kind``: + ``DOMAIN_RULE`` (a rule of the separate domain ruleset).

Nothing else changes: no table, column, trigger, row or index is added, altered or removed, so the
Phase 12 knowledge version ``KV-06361d7aba28c1ce`` and the Phase 13 palm knowledge version
``KV-a21c2c040abe9663`` (snapshots of rows and versions, not of these constraints) are untouched,
and sealed versions stay immutable. The Phase 17 knowledge content is a *separate* knowledge
version created by the ingestion; this migration only allows its vocabulary.

``downgrade`` restores the post-0003 vocabularies as ``NOT VALID`` constraints: they apply to new
rows only, so a database that already holds a Phase 17 version is not rewritten (rows in a sealed
version cannot be edited), and the next ``upgrade`` replaces them again.

Revision ID: 0004_domain_knowledge_vocabulary
Revises: 0003_palm_knowledge_vocabulary
Create Date: 2026-10-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_domain_knowledge_vocabulary"
down_revision: str | None = "0003_palm_knowledge_vocabulary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SUPPORT = ("SOURCE_SUPPORTED", "PROJECT_DERIVED", "UNRESOLVED_CONFLICT", "NOT_EVALUABLE")

# (table, column, values after migration 0003, values added by this migration)
VOCABULARIES: tuple[tuple[str, str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "concepts",
        "concept_type",
        (
            "PLANET",
            "HOUSE",
            "DOMAIN",
            "TERM",
            "TAROT_CARD",
            "CONCEPT",
            "PALM_LINE",
            "PALM_REGION",
            "PALM_FEATURE",
        ),
        ("VARGA",),
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
            "LOCATION_DEFINITION",
            "READING_CONVENTION",
            "COVERAGE",
        ),
        ("DOMAIN_DEFINITION", "VARGA_USE", "POLICY_NOTE"),
    ),
    ("statements", "support_status", _SUPPORT, ("PARTIALLY_SUPPORTED",)),
    ("domain_mappings", "support_status", _SUPPORT, ("PARTIALLY_SUPPORTED",)),
    (
        "rule_references",
        "rule_kind",
        ("RULE", "TABLE", "PROFILE", "PALM_RULE"),
        ("DOMAIN_RULE",),
    ),
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
