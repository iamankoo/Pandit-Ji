"""Create the schema namespaces for the single shared PostgreSQL database.

Per docs/ARCHITECTURE.md "Database Architecture": schema-per-domain, one
database, no domain tables yet -- this is the minimal infrastructure
migration for Phase 3. Each schema's tables are added by the Phases.md
phase that owns it (e.g. `charts`/`dashas` in Phase 5/7, `rules` in
Phase 6, `knowledge` in Phase 12, ...).

Revision ID: 0001_initial_schemas
Revises:
Create Date: 2026-09-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_initial_schemas"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMAS = [
    "identity",
    "profiles",
    "calc_config",
    "charts",
    "dashas",
    "transits",
    "panchang",
    "rules",
    "knowledge",
    "compatibility",
    "numerology",
    "conversation",
    "reports",
    "feedback",
    "audit",
]


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    for schema in reversed(SCHEMAS):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
