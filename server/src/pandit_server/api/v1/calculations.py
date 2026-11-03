"""Panchang, Numerology and Compatibility endpoints over the existing engines.

Only what each engine supports is exposed; each response carries the engine's own methodology
profile identifiers and typed statuses. Nothing is invented here: an unsupported profile or an
unmet precondition is a typed error, never a guessed value.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import APIRouter, Depends
from pandit_astro_engine.compatibility.constants import CompatibilityProfileId
from pandit_astro_engine.compatibility.models import (
    CompatibilityRequest,
    MatchParticipantInput,
)
from pandit_astro_engine.compatibility.service import CompatibilityService
from pandit_astro_engine.models import Location
from pandit_astro_engine.numerology import calculate_numerology
from pandit_astro_engine.numerology.constants import MasterNumberPolicy, NumerologyProfileId
from pandit_astro_engine.numerology.models import NameInput, NumerologyRequest
from pandit_astro_engine.panchang.models import PanchangRequest
from pandit_astro_engine.panchang.service import PanchangService

from pandit_server.api.v1.profiles import owned_profile
from pandit_server.compose import engines
from pandit_server.compose.profiles import (
    _local_input,
    profile_versions,
    require_birth_time,
    to_birth_time_input,
    validate_timezone,
)
from pandit_server.deps import ContainerDep, SessionDep, UserDep, limited, public_limited
from pandit_server.errors import ApiError
from pandit_server.schemas import CompatibilityQuery, NumerologyQuery, PanchangQuery

router = APIRouter(tags=["calculations"])

_panchang_service = PanchangService()


@router.post("/panchang", dependencies=[Depends(public_limited)])
def post_panchang(body: PanchangQuery, container: ContainerDep) -> dict[str, Any]:
    """A daily Panchang for a date and place. It depends on no user data, so it is public and its
    cached result is shared by every caller (the key still includes every input and version)."""
    validate_timezone(body.timezone)
    request = PanchangRequest(
        date=body.date,
        location=Location(latitude=body.latitude, longitude=body.longitude),
        timezone=body.timezone,
    )
    result, cached = container.cache.get_or_compute(
        "panchang",
        "public",
        request.model_dump(mode="json"),
        engines.engine_versions(),
        lambda: _panchang_service.daily(request).model_dump(mode="json"),
    )
    return {"versions": engines.engine_versions(), "cached": cached, "panchang": result}


@router.post("/numerology", dependencies=[Depends(limited())])
def post_numerology(
    body: NumerologyQuery, user: UserDep, container: ContainerDep
) -> dict[str, Any]:
    try:
        profile = NumerologyProfileId(body.profile) if body.profile else None
        policy = (
            MasterNumberPolicy(body.master_number_policy) if body.master_number_policy else None
        )
    except ValueError as exc:
        raise ApiError(
            422, "unsupported_profile", "Unsupported numerology profile or policy."
        ) from exc
    if body.date_of_birth is None and body.latin_name is None:
        raise ApiError(422, "nothing_to_calculate", "Provide date_of_birth and/or latin_name.")
    kwargs: dict[str, Any] = {
        "date_of_birth": body.date_of_birth,
        "name": NameInput(latin_spelling=body.latin_name) if body.latin_name else None,
        "master_number_policy": policy,
    }
    if profile is not None:
        kwargs["profile"] = profile
    try:
        request = NumerologyRequest(**kwargs)
    except ValueError as exc:
        raise ApiError(
            422, "invalid_numerology_request", "The combination is not supported."
        ) from exc
    result, cached = container.cache.get_or_compute(
        "numerology",
        str(user.id),  # the input is personal (a name and a birth date): scoped to its owner
        request.model_dump(mode="json"),
        engines.engine_versions(),
        lambda: calculate_numerology(request).model_dump(mode="json"),
    )
    return {"versions": engines.engine_versions(), "cached": cached, "numerology": result}


def _participant(profile: Any) -> MatchParticipantInput:
    require_birth_time(profile)
    return MatchParticipantInput(
        local_datetime=_local_input(
            profile.birth_date, profile.birth_time, profile.timezone, profile.disambiguation
        ),
        location=Location(latitude=profile.latitude, longitude=profile.longitude),
        birth_time=to_birth_time_input(profile),
    )


@router.post("/compatibility", dependencies=[Depends(limited("expensive"))])
def post_compatibility(
    body: CompatibilityQuery, user: UserDep, session: SessionDep, container: ContainerDep
) -> dict[str, Any]:
    """Match two of the caller's own profiles with a supported compatibility profile. Source
    conflicts and uncertainty are the engine's own and are returned unmerged."""
    try:
        profile_id = CompatibilityProfileId(body.profile)
    except ValueError as exc:
        raise ApiError(
            422,
            "unsupported_profile",
            "Unsupported compatibility profile.",
            details={"supported": [p.value for p in CompatibilityProfileId]},
        ) from exc
    a = owned_profile(session, user, body.profile_a_id)
    b = owned_profile(session, user, body.profile_b_id)
    request = CompatibilityRequest(
        profile=profile_id,
        person_a=_participant(a),
        person_b=_participant(b),
        as_of_date=dt.datetime.now(dt.timezone.utc).date(),
        participant_consent_attested=True,
    )
    result, cached = container.cache.get_or_compute(
        "compatibility",
        str(user.id),
        {
            "a": profile_versions(a),
            "b": profile_versions(b),
            "profile": profile_id.value,
            "as_of": request.as_of_date.isoformat(),
        },
        engines.engine_versions(),
        lambda: CompatibilityService().match(request).model_dump(mode="json"),
    )
    return {"versions": engines.engine_versions(), "cached": cached, "compatibility": result}
