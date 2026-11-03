"""Phase 18 backend platform tables: identity, profiles, charts, conversation, reports, platform, audit.

Additive and forward-compatible: it creates the new ``platform`` schema and the tables the backend
needs (users keyed by the OIDC subject, birth profiles, stored Kundlis, conversations, consented
memory, reports, job runs, notifications, voice sessions, idempotency keys and the audit trail).
No existing table, knowledge version or constraint is touched. ``downgrade`` drops exactly what
this migration created.

Revision ID: 0005_platform_backend
Revises: 0004_domain_knowledge_vocabulary
Create Date: 2026-11-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_platform_backend"
down_revision: str | None = "0004_domain_knowledge_vocabulary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NOW = sa.text("now()")


def _id() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _user_fk() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(
        "user_id",
        sa.Uuid(),
        sa.ForeignKey("identity.users.id", ondelete="CASCADE"),
        nullable=False,
    )


def _created() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW
    )


def _updated() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(
        "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW
    )


TABLES = (
    ("platform", "voice_sessions"),
    ("platform", "notifications"),
    ("platform", "notification_subscriptions"),
    ("platform", "job_runs"),
    ("reports", "reports"),
    ("conversation", "memory_items"),
    ("conversation", "messages"),
    ("conversation", "conversations"),
    ("charts", "kundlis"),
    ("profiles", "birth_profiles"),
    ("identity", "idempotency_keys"),
    ("identity", "users"),
    ("audit", "events"),
)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS platform")

    op.create_table(
        "users",
        _id(),
        sa.Column("subject", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(120)),
        sa.Column("locale", sa.String(8), nullable=False, server_default="en"),
        sa.Column("memory_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notification_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("analytics_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        _created(),
        _updated(),
        schema="identity",
    )
    op.create_table(
        "idempotency_keys",
        _user_fk(),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("method", sa.String(8), nullable=False),
        sa.Column("path", sa.String(200), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response", postgresql.JSONB(), nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("user_id", "key"),
        schema="identity",
    )
    op.create_table(
        "birth_profiles",
        _id(),
        _user_fk(),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("birth_time", sa.Time()),
        sa.Column("time_precision", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("time_uncertainty_seconds", sa.Float()),
        sa.Column("disambiguation", sa.String(8), nullable=False, server_default="strict"),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("altitude_m", sa.Float(), nullable=False, server_default="0"),
        sa.Column("place_label", sa.String(160)),
        sa.Column("birth_utc", sa.DateTime(timezone=True)),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        _created(),
        _updated(),
        sa.UniqueConstraint("user_id", "label", name="uq_birth_profiles_user_label"),
        sa.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_birth_profiles_lat"),
        sa.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_birth_profiles_lon"),
        sa.CheckConstraint(
            "time_precision IN ('exact','minute','approximate','unknown')",
            name="ck_birth_profiles_precision",
        ),
        schema="profiles",
    )
    op.create_index(
        "ix_birth_profiles_user_id", "birth_profiles", ["user_id"], schema="profiles"
    )
    op.create_table(
        "kundlis",
        _id(),
        sa.Column(
            "profile_id",
            sa.Uuid(),
            sa.ForeignKey("profiles.birth_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("profile_row_version", sa.Integer(), nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("engine_version", sa.String(32), nullable=False),
        sa.Column("standards_version", sa.String(16), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        _created(),
        sa.UniqueConstraint("profile_id", "profile_row_version", "config_hash", name="uq_kundli"),
        schema="charts",
    )
    op.create_table(
        "conversations",
        _id(),
        _user_fk(),
        sa.Column("language", sa.String(8), nullable=False, server_default="EN"),
        _created(),
        schema="conversation",
    )
    op.create_index(
        "ix_conversations_user_id", "conversations", ["user_id"], schema="conversation"
    )
    op.create_table(
        "messages",
        _id(),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("conversation.conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        _created(),
        schema="conversation",
    )
    op.create_table(
        "memory_items",
        _id(),
        _user_fk(),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        _created(),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "kind", "key", name="uq_memory_user_kind_key"),
        schema="conversation",
    )
    op.create_index("ix_memory_items_user_id", "memory_items", ["user_id"], schema="conversation")
    op.create_table(
        "reports",
        _id(),
        _user_fk(),
        sa.Column(
            "profile_id",
            sa.Uuid(),
            sa.ForeignKey("profiles.birth_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("domains", postgresql.JSONB(), nullable=False),
        sa.Column("content", postgresql.JSONB()),
        _created(),
        _updated(),
        schema="reports",
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"], schema="reports")
    op.create_table(
        "job_runs",
        _id(),
        _user_fk(),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_ref", sa.String(64)),
        sa.Column("error_code", sa.String(48)),
        _created(),
        _updated(),
        schema="platform",
    )
    op.create_index("ix_job_runs_user_id", "job_runs", ["user_id"], schema="platform")
    op.create_table(
        "notification_subscriptions",
        _id(),
        _user_fk(),
        sa.Column("channel", sa.String(8), nullable=False),
        sa.Column("topic", sa.String(48), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        _created(),
        sa.UniqueConstraint("user_id", "channel", "topic", name="uq_notification_subscription"),
        sa.CheckConstraint("channel IN ('inapp','push','email')", name="ck_notification_channel"),
        schema="platform",
    )
    op.create_index(
        "ix_notification_subscriptions_user_id",
        "notification_subscriptions",
        ["user_id"],
        schema="platform",
    )
    op.create_table(
        "notifications",
        _id(),
        _user_fk(),
        sa.Column("topic", sa.String(48), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="scheduled"),
        _created(),
        schema="platform",
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], schema="platform")
    op.create_table(
        "voice_sessions",
        _id(),
        _user_fk(),
        sa.Column("language", sa.String(8), nullable=False, server_default="EN"),
        sa.Column("status", sa.String(12), nullable=False, server_default="open"),
        _created(),
        schema="platform",
    )
    op.create_index("ix_voice_sessions_user_id", "voice_sessions", ["user_id"], schema="platform")
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=_NOW
        ),
        sa.Column("actor_hash", sa.String(64)),
        sa.Column("action", sa.String(48), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("request_id", sa.String(64)),
        sa.Column("outcome", sa.String(16), nullable=False),
        schema="audit",
    )


def downgrade() -> None:
    for schema, table in TABLES:
        op.drop_table(table, schema=schema)
    op.execute("DROP SCHEMA IF EXISTS platform CASCADE")
