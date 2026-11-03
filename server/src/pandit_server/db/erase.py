"""Explicit erasure of user-owned rows.

PostgreSQL also enforces ``ON DELETE CASCADE`` on every owned table (the migration); erasing
explicitly keeps deletion correct and testable on any database, and it is the one place that must
list every table a user can own (a test fails if a new owned table is forgotten).
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from pandit_server.db.models import (
    BirthProfile,
    Conversation,
    IdempotencyKey,
    JobRun,
    MemoryItem,
    Message,
    Notification,
    NotificationSubscription,
    Report,
    StoredKundli,
    User,
    VoiceSession,
)

#: Every model with a ``user_id`` column (checked by a test against the metadata).
USER_OWNED = (
    Conversation,
    MemoryItem,
    Report,
    BirthProfile,
    JobRun,
    Notification,
    NotificationSubscription,
    VoiceSession,
    IdempotencyKey,
)


def erase_profile_data(session: Session, profile_ids: list[uuid.UUID]) -> None:
    if not profile_ids:
        return
    session.execute(delete(StoredKundli).where(StoredKundli.profile_id.in_(profile_ids)))
    session.execute(delete(Report).where(Report.profile_id.in_(profile_ids)))


def erase_user(session: Session, user_id: uuid.UUID) -> None:
    conversation_ids = select(Conversation.id).where(Conversation.user_id == user_id)
    session.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
    profile_ids = list(
        session.scalars(select(BirthProfile.id).where(BirthProfile.user_id == user_id)).all()
    )
    erase_profile_data(session, profile_ids)
    for model in USER_OWNED:
        session.execute(delete(model).where(model.user_id == user_id))
    session.execute(delete(User).where(User.id == user_id))
