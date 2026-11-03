"""Chart, Dasha and raw Transit endpoints over the existing deterministic engines.

These return the engines' own result models with their methodology/profile identifiers, versions
and provenance. The Transit endpoint exposes raw facts only: it does not evaluate any life domain
(the domain-to-house transit methodology is RESEARCH_PENDING and stays non-evaluating).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from pandit_server.api.v1.profiles import owned_profile
from pandit_server.compose import engines
from pandit_server.compose.profiles import profile_versions
from pandit_server.db.models import StoredKundli
from pandit_server.deps import ContainerDep, SessionDep, UserDep, limited
from pandit_server.platform_services import sha256_hex
from pandit_server.schemas import TransitQuery

router = APIRouter(prefix="/birth-profiles/{profile_id}", tags=["charts"])


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)


@router.get("/kundli", dependencies=[Depends(limited("expensive"))])
def get_kundli(
    profile_id: uuid.UUID, user: UserDep, session: SessionDep, container: ContainerDep
) -> dict[str, Any]:
    profile = owned_profile(session, user, profile_id)
    payload, cached = engines.kundli_for(container, profile)
    config_hash = sha256_hex({"calc": "kundli-default", "engine": engines.engine_versions()})
    stored = session.scalar(
        select(StoredKundli).where(
            StoredKundli.profile_id == profile.id,
            StoredKundli.profile_row_version == profile.row_version,
            StoredKundli.config_hash == config_hash,
        )
    )
    if stored is None:
        metadata = payload.get("metadata", {})
        session.add(
            StoredKundli(
                profile_id=profile.id,
                profile_row_version=profile.row_version,
                config_hash=config_hash,
                engine_version=str(metadata.get("engine_version", "")),
                standards_version=str(metadata.get("standards_version", "")),
                payload=payload,
            )
        )
    return {
        "profile_id": str(profile.id),
        "profile_version": profile.row_version,
        "time_precision": profile.time_precision,
        "birth_time_uncertainty_seconds": profile.time_uncertainty_seconds,
        "versions": engines.engine_versions(),
        "cached": cached,
        "kundli": payload,
    }


@router.get("/dasha", dependencies=[Depends(limited("expensive"))])
def get_dasha(
    profile_id: uuid.UUID,
    user: UserDep,
    session: SessionDep,
    container: ContainerDep,
    depth: Annotated[int, Query(ge=1, le=3)] = 3,
    at_utc: Annotated[dt.datetime | None, Query()] = None,
) -> dict[str, Any]:
    """Vimshottari periods (Maha/Antar/Pratyantar) and the period of each level at ``at_utc``."""
    profile = owned_profile(session, user, profile_id)
    if profile.birth_time is None:
        # the engine's own typed outcome for an unknown birth time; nothing is assumed
        return {
            "status": "not_evaluable",
            "reason_code": "birth_time_unknown",
            "versions": engines.engine_versions(),
        }
    facts, cached = engines.dasha_for(container, profile, depth)
    at = at_utc or _utc_now()
    if at.tzinfo is None:
        at = at.replace(tzinfo=dt.timezone.utc)
    return {
        "profile_id": str(profile.id),
        "profile_version": profile.row_version,
        "versions": engines.engine_versions(),
        "cached": cached,
        "at_utc": at.astimezone(dt.timezone.utc).isoformat(),
        "current": engines.current_periods(facts, at.astimezone(dt.timezone.utc)),
        "facts": facts,
    }


@router.get("/dasha/transitions", dependencies=[Depends(limited("expensive"))])
def get_dasha_transitions(
    profile_id: uuid.UUID,
    user: UserDep,
    session: SessionDep,
    container: ContainerDep,
    start_utc: Annotated[dt.datetime, Query()],
    end_utc: Annotated[dt.datetime, Query()],
    depth: Annotated[int, Query(ge=1, le=3)] = 3,
) -> dict[str, Any]:
    """Periods that begin within ``[start_utc, end_utc)``."""
    from pandit_server.errors import ApiError

    if start_utc.tzinfo is None or end_utc.tzinfo is None or end_utc <= start_utc:
        raise ApiError(422, "invalid_range", "start_utc and end_utc must be aware and ordered.")
    profile = owned_profile(session, user, profile_id)
    if profile.birth_time is None:
        return {"status": "not_evaluable", "reason_code": "birth_time_unknown", "transitions": []}
    facts, _ = engines.dasha_for(container, profile, depth)
    return {
        "profile_id": str(profile.id),
        "transitions": engines.transitions_between(facts, start_utc, end_utc),
    }


@router.post("/transits", dependencies=[Depends(limited("expensive"))])
def post_transits(
    profile_id: uuid.UUID,
    body: TransitQuery,
    user: UserDep,
    session: SessionDep,
    container: ContainerDep,
) -> dict[str, Any]:
    """Raw transit facts for an instant or a window (UTC), related to the natal chart."""
    profile = owned_profile(session, user, profile_id)
    kundli_json, _ = engines.kundli_for(container, profile)
    natal = engines.natal_reference(kundli_json)
    window = (
        (body.window_start_utc, body.window_end_utc)
        if body.window_start_utc and body.window_end_utc
        else None
    )
    at = body.at_utc or (None if window else _utc_now())
    facts, cached = container.cache.get_or_compute(
        "transit",
        str(user.id),
        {
            **profile_versions(profile),
            "at": at.isoformat() if at else None,
            "window": [w.isoformat() for w in window] if window else None,
            "sade_sati": body.include_sade_sati,
        },
        engines.engine_versions(),
        lambda: engines.compute_transit(natal, at, window, body.include_sade_sati),
    )
    return {
        "profile_id": str(profile.id),
        "versions": engines.engine_versions(),
        "cached": cached,
        "interpretation": engines.TRANSIT_INTERPRETATION_NOTICE,
        "facts": facts,
    }
