"""API foundations owned by Phase 18: Memory, Notifications, Voice and job status.

These are backend foundations only. The full personal-memory and personalization experience, daily
personalized insights and notification delivery, and the speech-to-text / text-to-speech voice
experience belong to Phase 20 and are reported as typed ``unavailable`` here, never faked.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import delete, func, select

from pandit_server.api.v1.chat import answer, outcome_payload
from pandit_server.api.v1.profiles import owned_profile
from pandit_server.db.models import (
    JobRun,
    MemoryItem,
    Notification,
    NotificationSubscription,
    VoiceSession,
)
from pandit_server.deps import ContainerDep, SessionDep, UserDep, limited
from pandit_server.errors import ApiError, not_found
from pandit_server.schemas import (
    ChatRequest,
    MemoryPut,
    NotificationIn,
    SubscriptionIn,
    VoiceSessionIn,
)

router = APIRouter(tags=["platform"], dependencies=[Depends(limited())])

MAX_PENDING_NOTIFICATIONS = 50
MAX_MEMORY_ITEMS = 100


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _aware(value: dt.datetime) -> dt.datetime:
    return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)


# ---- jobs ---------------------------------------------------------------------------------------


@router.get("/jobs/{job_id}")
def get_job(job_id: uuid.UUID, user: UserDep, session: SessionDep) -> dict[str, Any]:
    job = session.scalar(select(JobRun).where(JobRun.id == job_id, JobRun.user_id == user.id))
    if job is None:
        raise not_found("job")
    return {
        "id": str(job.id),
        "kind": job.kind,
        "status": job.status,
        "attempts": job.attempts,
        "result_ref": job.result_ref,
        "error_code": job.error_code,
    }


# ---- memory (consent-gated; retention-limited) --------------------------------------------------


def _require_memory(user: Any) -> None:
    if not user.memory_consent:
        raise ApiError(403, "consent_required", "Memory is off: enable memory_consent first.")


def _purge_expired(session: Any, user: Any) -> None:
    session.execute(
        delete(MemoryItem).where(MemoryItem.user_id == user.id, MemoryItem.expires_at <= _now())
    )


@router.get("/memory")
def list_memory(user: UserDep, session: SessionDep) -> dict[str, Any]:
    _require_memory(user)
    _purge_expired(session, user)
    rows = session.scalars(select(MemoryItem).where(MemoryItem.user_id == user.id)).all()
    return {"items": [{"kind": m.kind, "key": m.key, "value": m.value} for m in rows]}


@router.put("/memory/{key}")
def put_memory(
    key: str, body: MemoryPut, user: UserDep, session: SessionDep, container: ContainerDep
) -> dict[str, Any]:
    _require_memory(user)
    if (
        not 1 <= len(key) <= 80
        or not key.replace("_", "").replace("-", "").replace(".", "").isalnum()
    ):
        raise ApiError(422, "invalid_key", "Memory keys are 1-80 letters, digits, '_', '-' or '.'.")
    _purge_expired(session, user)
    expires = _now() + dt.timedelta(days=container.settings.memory_retention_days)
    item = session.scalar(
        select(MemoryItem).where(
            MemoryItem.user_id == user.id, MemoryItem.kind == body.kind, MemoryItem.key == key
        )
    )
    if item is None:
        count = session.scalar(
            select(func.count()).select_from(MemoryItem).where(MemoryItem.user_id == user.id)
        )
        if (count or 0) >= MAX_MEMORY_ITEMS:
            raise ApiError(409, "memory_limit_reached", "The memory limit was reached.")
        item = MemoryItem(
            user_id=user.id, kind=body.kind, key=key, value=body.value, expires_at=expires
        )
        session.add(item)
    else:
        item.value = body.value
        item.expires_at = expires
    session.flush()
    return {"kind": item.kind, "key": item.key, "value": item.value}


@router.delete("/memory/{key}", status_code=204)
def delete_memory(key: str, user: UserDep, session: SessionDep) -> None:
    _require_memory(user)
    session.execute(delete(MemoryItem).where(MemoryItem.user_id == user.id, MemoryItem.key == key))


@router.delete("/memory", status_code=204)
def clear_memory(user: UserDep, session: SessionDep) -> None:
    session.execute(delete(MemoryItem).where(MemoryItem.user_id == user.id))


# ---- notifications (foundation: subscriptions and scheduled messages; no delivery) ---------------


@router.put("/notifications/subscriptions")
def put_subscription(body: SubscriptionIn, user: UserDep, session: SessionDep) -> dict[str, Any]:
    if body.channel != "inapp" and not user.notification_consent:
        raise ApiError(403, "consent_required", "Enable notification_consent first.")
    sub = session.scalar(
        select(NotificationSubscription).where(
            NotificationSubscription.user_id == user.id,
            NotificationSubscription.channel == body.channel,
            NotificationSubscription.topic == body.topic,
        )
    )
    if sub is None:
        sub = NotificationSubscription(
            user_id=user.id, channel=body.channel, topic=body.topic, enabled=body.enabled
        )
        session.add(sub)
    else:
        sub.enabled = body.enabled
    session.flush()
    return {"channel": sub.channel, "topic": sub.topic, "enabled": sub.enabled}


@router.get("/notifications/subscriptions")
def list_subscriptions(user: UserDep, session: SessionDep) -> dict[str, Any]:
    rows = session.scalars(
        select(NotificationSubscription).where(NotificationSubscription.user_id == user.id)
    ).all()
    return {"items": [{"channel": s.channel, "topic": s.topic, "enabled": s.enabled} for s in rows]}


@router.post("/notifications", status_code=201)
def schedule_notification(
    body: NotificationIn, user: UserDep, session: SessionDep
) -> dict[str, Any]:
    if not user.notification_consent:
        raise ApiError(403, "consent_required", "Enable notification_consent first.")
    when = _aware(body.scheduled_for)
    if when <= _now() or when > _now() + dt.timedelta(days=366):
        raise ApiError(422, "invalid_schedule", "scheduled_for must be within the next year.")
    pending = session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.status == "scheduled")
    )
    if (pending or 0) >= MAX_PENDING_NOTIFICATIONS:
        raise ApiError(409, "notification_limit_reached", "Too many scheduled notifications.")
    note = Notification(user_id=user.id, topic=body.topic, message=body.message, scheduled_for=when)
    session.add(note)
    session.flush()
    return {"id": str(note.id), "status": note.status, "delivery": "not_available_until_phase_20"}


@router.get("/notifications")
def list_notifications(user: UserDep, session: SessionDep) -> dict[str, Any]:
    rows = session.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.scheduled_for)
    ).all()
    return {
        "items": [
            {
                "id": str(n.id),
                "topic": n.topic,
                "message": n.message,
                "scheduled_for": n.scheduled_for.isoformat(),
                "status": n.status,
            }
            for n in rows
        ]
    }


@router.delete("/notifications/{notification_id}", status_code=204)
def cancel_notification(notification_id: uuid.UUID, user: UserDep, session: SessionDep) -> None:
    note = session.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
    )
    if note is None:
        raise not_found("notification")
    session.delete(note)


# ---- voice (foundation: sessions and text turns; audio is a Phase 20 capability) ----------------


@router.get("/voice/capabilities")
def voice_capabilities() -> dict[str, Any]:
    unavailable = {"available": False, "reason": "PHASE_20_NOT_IMPLEMENTED"}
    return {
        "speech_to_text": unavailable,
        "text_to_speech": unavailable,
        "text_turns": {"available": True},
        "languages": ["EN", "HI", "HG"],
    }


@router.post("/voice/sessions", status_code=201)
def create_voice_session(
    body: VoiceSessionIn, user: UserDep, session: SessionDep
) -> dict[str, Any]:
    voice = VoiceSession(user_id=user.id, language=body.language)
    session.add(voice)
    session.flush()
    return {"id": str(voice.id), "language": voice.language, "status": voice.status}


def _voice(session: Any, user: Any, session_id: uuid.UUID) -> VoiceSession:
    voice: VoiceSession | None = session.scalar(
        select(VoiceSession).where(VoiceSession.id == session_id, VoiceSession.user_id == user.id)
    )
    if voice is None:
        raise not_found("voice session")
    return voice


@router.post("/voice/sessions/{session_id}/turns", dependencies=[Depends(limited("expensive"))])
def voice_text_turn(
    session_id: uuid.UUID,
    body: ChatRequest,
    request: Request,
    user: UserDep,
    session: SessionDep,
    container: ContainerDep,
) -> dict[str, Any]:
    """A text turn through the same verified pipeline as chat. Audio input/output is Phase 20."""
    voice = _voice(session, user, session_id)
    if voice.status != "open":
        raise ApiError(409, "session_closed", "The voice session is closed.")
    if body.profile_id is None:
        raise ApiError(422, "profile_required", "Choose a birth profile for this question.")
    profile = owned_profile(session, user, body.profile_id)
    outcome = answer(
        container,
        profile,
        body.model_copy(update={"language": voice.language}),
        getattr(request.state, "request_id", None) or uuid.uuid4().hex,
    )
    return {
        "audio": {"available": False, "reason": "PHASE_20_NOT_IMPLEMENTED"},
        **outcome_payload(outcome, None),
    }


@router.post("/voice/audio", status_code=501)
def voice_audio_unavailable() -> dict[str, Any]:
    raise ApiError(
        501, "voice_audio_unavailable", "Speech input/output is not implemented yet (Phase 20)."
    )


@router.delete("/voice/sessions/{session_id}", status_code=204)
def close_voice_session(session_id: uuid.UUID, user: UserDep, session: SessionDep) -> None:
    session.delete(_voice(session, user, session_id))
