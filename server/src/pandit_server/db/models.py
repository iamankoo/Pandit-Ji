"""Phase 18 persistence models (SQLAlchemy 2.x), one schema per domain (docs/ARCHITECTURE.md).

Ownership rule: every user-owned row carries ``user_id`` (or reaches it through a parent that
does) and every query in the repositories filters on it. Deleting a user cascades to all of their
rows; only the audit trail survives, and it holds a one-way actor hash, never the user id or any
personal data.

The matching Alembic migration is ``0005_platform_backend`` (additive; it creates the ``platform``
schema and these tables). ``Base.metadata`` is the source for both the migration test and the
SQLite-backed unit tests (the schemas are translated away there).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

JsonType = JSON().with_variant(JSONB(), "postgresql")
AutoBigInt = BigInteger().with_variant(Integer(), "sqlite")

SCHEMAS = ("identity", "profiles", "charts", "conversation", "reports", "audit", "platform")


class Base(DeclarativeBase):
    pass


def _now() -> Any:
    return func.now()


class User(Base):
    """An application user, keyed by the OIDC ``sub`` claim (Keycloak owns the credentials)."""

    __tablename__ = "users"
    __table_args__ = {"schema": "identity"}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subject: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120))
    locale: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    memory_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notification_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    analytics_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now(), onupdate=_now()
    )


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = {"schema": "identity"}

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("identity.users.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    path: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response: Mapped[Any] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )


class BirthProfile(Base):
    """A birth profile. Original local input and the canonical UTC instant are both kept; missing
    details are never inferred (a missing time stays ``None`` with ``time_precision='unknown'``)."""

    __tablename__ = "birth_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "label", name="uq_birth_profiles_user_label"),
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_birth_profiles_lat"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_birth_profiles_lon"),
        CheckConstraint(
            "time_precision IN ('exact','minute','approximate','unknown')",
            name="ck_birth_profiles_precision",
        ),
        {"schema": "profiles"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    birth_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    birth_time: Mapped[dt.time | None] = mapped_column(Time)
    time_precision: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    time_uncertainty_seconds: Mapped[float | None] = mapped_column(Float)
    disambiguation: Mapped[str] = mapped_column(String(8), nullable=False, default="strict")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    place_label: Mapped[str | None] = mapped_column(String(160))
    birth_utc: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now(), onupdate=_now()
    )


class StoredKundli(Base):
    __tablename__ = "kundlis"
    __table_args__ = (
        UniqueConstraint("profile_id", "profile_row_version", "config_hash", name="uq_kundli"),
        {"schema": "charts"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.birth_profiles.id", ondelete="CASCADE"), nullable=False
    )
    profile_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    standards_version: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[Any] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = {"schema": "conversation"}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="EN")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )


class Message(Base):
    """Stored only for users who gave ``memory_consent``; holds the verified response, never raw
    prompts or birth details."""

    __tablename__ = "messages"
    __table_args__ = {"schema": "conversation"}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conversation.conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[Any] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )


class MemoryItem(Base):
    __tablename__ = "memory_items"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", "key", name="uq_memory_user_kind_key"),
        {"schema": "conversation"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[Any] = mapped_column(JsonType, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = {"schema": "reports"}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.birth_profiles.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    domains: Mapped[Any] = mapped_column(JsonType, nullable=False)
    content: Mapped[Any | None] = mapped_column(JsonType)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now(), onupdate=_now()
    )


class JobRun(Base):
    __tablename__ = "job_runs"
    __table_args__ = {"schema": "platform"}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_ref: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(48))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now(), onupdate=_now()
    )


class NotificationSubscription(Base):
    __tablename__ = "notification_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "channel", "topic", name="uq_notification_subscription"),
        CheckConstraint("channel IN ('inapp','push','email')", name="ck_notification_channel"),
        {"schema": "platform"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(8), nullable=False)
    topic: Mapped[str] = mapped_column(String(48), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "platform"}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(48), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    scheduled_for: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="scheduled")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )


class VoiceSession(Base):
    __tablename__ = "voice_sessions"
    __table_args__ = {"schema": "platform"}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("identity.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="EN")
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="open")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )


class AuditEvent(Base):
    """Safe audit trail: an actor hash, an action and a resource id. No personal data, no payloads,
    and no foreign key to ``users`` (the trail outlives account deletion)."""

    __tablename__ = "events"
    __table_args__ = {"schema": "audit"}

    id: Mapped[int] = mapped_column(AutoBigInt, primary_key=True, autoincrement=True)
    occurred_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=_now()
    )
    actor_hash: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
