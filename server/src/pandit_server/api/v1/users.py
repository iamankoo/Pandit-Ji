"""The signed-in user: profile, privacy controls, data export and account deletion."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import delete, select

from pandit_server.compose.profiles import profile_to_out
from pandit_server.db.erase import erase_user
from pandit_server.db.models import BirthProfile, MemoryItem, User
from pandit_server.deps import ContainerDep, PrincipalDep, SessionDep, UserDep, limited
from pandit_server.platform_services import record_audit
from pandit_server.schemas import PrivacyUpdate, UserOut, UserUpdate

router = APIRouter(prefix="/users/me", tags=["users"], dependencies=[Depends(limited())])


def _out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        display_name=user.display_name,
        locale=user.locale,
        memory_consent=user.memory_consent,
        notification_consent=user.notification_consent,
        analytics_consent=user.analytics_consent,
        created_at=user.created_at,
    )


@router.get("", response_model=UserOut)
def get_me(user: UserDep) -> UserOut:
    return _out(user)


@router.patch("", response_model=UserOut)
def update_me(body: UserUpdate, user: UserDep, session: SessionDep) -> UserOut:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    session.flush()
    return _out(user)


@router.put("/privacy", response_model=UserOut)
def update_privacy(
    body: PrivacyUpdate, request: Request, user: UserDep, session: SessionDep
) -> UserOut:
    """Consent controls. Withdrawing memory consent erases the stored memory immediately."""
    changes = body.model_dump(exclude_unset=True)
    if changes.get("memory_consent") is False:
        session.execute(delete(MemoryItem).where(MemoryItem.user_id == user.id))
    for field, value in changes.items():
        setattr(user, field, value)
    record_audit(
        session,
        subject=user.subject,
        action="privacy.update",
        resource_type="user",
        resource_id=str(user.id),
        request_id=getattr(request.state, "request_id", None),
    )
    session.flush()
    return _out(user)


@router.get("/export")
def export_my_data(user: UserDep, session: SessionDep) -> dict[str, Any]:
    """Everything the backend holds about the user (data portability)."""
    profiles = session.scalars(select(BirthProfile).where(BirthProfile.user_id == user.id)).all()
    memory = session.scalars(select(MemoryItem).where(MemoryItem.user_id == user.id)).all()
    return {
        "user": _out(user).model_dump(mode="json"),
        "birth_profiles": [profile_to_out(p).model_dump(mode="json") for p in profiles],
        "memory": [{"kind": m.kind, "key": m.key, "value": m.value} for m in memory],
    }


@router.delete("", status_code=204)
def delete_me(
    request: Request,
    container: ContainerDep,
    principal: PrincipalDep,
    user: UserDep,
    session: SessionDep,
) -> None:
    """Delete the account and every row it owns (cascade), then revoke all of its tokens. The audit
    trail keeps only a one-way actor hash. The Keycloak identity itself is removed by the operator
    (or the Keycloak account console); the backend holds no credentials."""
    subject, user_id = user.subject, str(user.id)
    erase_user(session, user.id)
    record_audit(
        session,
        subject=subject,
        action="account.delete",
        resource_type="user",
        resource_id=user_id,
        request_id=getattr(request.state, "request_id", None),
    )
    session.flush()
    container.verifier.revoke_subject(principal.subject)
