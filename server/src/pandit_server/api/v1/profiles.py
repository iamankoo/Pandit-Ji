"""Birth-profile CRUD. Every query is scoped to the owner; another user's profile is a plain 404."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from pandit_server.compose.profiles import profile_to_out, resolve_birth_utc
from pandit_server.db.erase import erase_profile_data
from pandit_server.db.models import BirthProfile, User
from pandit_server.deps import SessionDep, UserDep, limited
from pandit_server.errors import ApiError, not_found
from pandit_server.platform_services import record_audit, run_idempotent
from pandit_server.schemas import BirthProfileIn, BirthProfileOut, BirthProfileUpdate

router = APIRouter(
    prefix="/birth-profiles", tags=["birth-profiles"], dependencies=[Depends(limited())]
)

MAX_PROFILES_PER_USER = 20
_FIELDS = (
    "label",
    "birth_date",
    "birth_time",
    "time_precision",
    "time_uncertainty_seconds",
    "timezone",
    "disambiguation",
    "latitude",
    "longitude",
    "altitude_m",
    "place_label",
)


def owned_profile(
    session: SessionDep, user: User, profile_id: uuid.UUID, *, lock: bool = False
) -> BirthProfile:
    """The caller's own profile (a plain 404 otherwise). ``lock`` takes a row lock (``FOR UPDATE``)
    so concurrent updates are serialised and the version check cannot be raced."""
    query = select(BirthProfile).where(
        BirthProfile.id == profile_id, BirthProfile.user_id == user.id
    )
    if lock:
        query = query.with_for_update()
    profile = session.scalar(query)
    if profile is None:
        raise not_found("birth profile")
    return profile


@router.post("", status_code=201, response_model=BirthProfileOut)
def create_profile(
    body: BirthProfileIn,
    request: Request,
    response: Response,
    user: UserDep,
    session: SessionDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Any:
    def create() -> tuple[int, dict[str, Any]]:
        count = session.scalar(
            select(func.count()).select_from(BirthProfile).where(BirthProfile.user_id == user.id)
        )
        if (count or 0) >= MAX_PROFILES_PER_USER:
            raise ApiError(409, "profile_limit_reached", "The birth-profile limit was reached.")
        data = body.model_dump()
        profile = BirthProfile(user_id=user.id, birth_utc=resolve_birth_utc(body), **data)
        try:
            with session.begin_nested():
                session.add(profile)
        except IntegrityError as exc:
            raise ApiError(
                409, "label_exists", "A profile with this label already exists."
            ) from exc
        session.refresh(profile)
        record_audit(
            session,
            subject=user.subject,
            action="birth_profile.create",
            resource_type="birth_profile",
            resource_id=str(profile.id),
            request_id=getattr(request.state, "request_id", None),
        )
        return 201, profile_to_out(profile).model_dump(mode="json")

    status, payload, replayed = run_idempotent(
        session,
        user_id=user.id,
        key=idempotency_key,
        method="POST",
        path="/birth-profiles",
        body=body.model_dump(mode="json"),
        handler=create,
    )
    if replayed:
        response.headers["Idempotent-Replayed"] = "true"
    response.status_code = status
    return payload


@router.get("")
def list_profiles(
    user: UserDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    base = select(BirthProfile).where(BirthProfile.user_id == user.id)
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.scalars(
        base.order_by(BirthProfile.created_at, BirthProfile.id).limit(limit).offset(offset)
    ).all()
    return {
        "items": [profile_to_out(p).model_dump(mode="json") for p in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{profile_id}", response_model=BirthProfileOut)
def get_profile(profile_id: uuid.UUID, user: UserDep, session: SessionDep) -> BirthProfileOut:
    return profile_to_out(owned_profile(session, user, profile_id))


@router.put("/{profile_id}", response_model=BirthProfileOut)
def update_profile(
    profile_id: uuid.UUID,
    body: BirthProfileUpdate,
    request: Request,
    user: UserDep,
    session: SessionDep,
) -> BirthProfileOut:
    """Full replacement with optimistic concurrency: ``expected_version`` must match."""
    profile = owned_profile(session, user, profile_id, lock=True)
    if profile.row_version != body.expected_version:
        raise ApiError(409, "version_conflict", "The profile was changed; reload and retry.")
    data = body.model_dump(exclude={"expected_version"})
    birth_utc = resolve_birth_utc(BirthProfileIn(**data))
    for field in _FIELDS:
        setattr(profile, field, data[field])
    profile.birth_utc = birth_utc
    profile.row_version += 1
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        raise ApiError(409, "label_exists", "A profile with this label already exists.") from exc
    session.refresh(profile)
    record_audit(
        session,
        subject=user.subject,
        action="birth_profile.update",
        resource_type="birth_profile",
        resource_id=str(profile.id),
        request_id=getattr(request.state, "request_id", None),
    )
    return profile_to_out(profile)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(
    profile_id: uuid.UUID, request: Request, user: UserDep, session: SessionDep
) -> None:
    profile = owned_profile(session, user, profile_id)
    erase_profile_data(session, [profile.id])
    session.delete(profile)
    record_audit(
        session,
        subject=user.subject,
        action="birth_profile.delete",
        resource_type="birth_profile",
        resource_id=str(profile_id),
        request_id=getattr(request.state, "request_id", None),
    )
