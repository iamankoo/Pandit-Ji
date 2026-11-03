"""Composition over the existing deterministic engines. No astronomy or chart logic lives here:
each function builds the engine's own request from a stored profile, calls the engine's public
service and returns the engine's own result model as JSON, with the versions it was made under.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from pandit_astro_engine import KundliCalculationService
from pandit_astro_engine._version import __version__ as ASTRO_ENGINE_VERSION
from pandit_astro_engine.dashas.models import DashaConfiguration
from pandit_astro_engine.dashas.service import DashaCalculationService
from pandit_astro_engine.transits.models import NatalReference, TransitConfiguration
from pandit_astro_engine.transits.service import TransitCalculationService

from pandit_server.compose.profiles import (
    profile_versions,
    require_birth_time,
    to_astro_request,
    to_birth_time_input,
)
from pandit_server.container import Container
from pandit_server.db.models import BirthProfile
from pandit_server.platform_services import sha256_hex

_kundli_service = KundliCalculationService()
_dasha_service = DashaCalculationService()
_transit_service = TransitCalculationService()

TRANSIT_INTERPRETATION_NOTICE = {
    "provided": False,
    "reason": (
        "Raw deterministic transit facts only. No life-domain transit evaluation exists: the "
        "domain-to-house transit methodology is RESEARCH_PENDING (owner decision)."
    ),
}


def engine_versions() -> dict[str, str]:
    return {"astro_engine": ASTRO_ENGINE_VERSION}


def _config_hash(profile: BirthProfile) -> str:
    return sha256_hex({"calc": "kundli-default", "engine": engine_versions()})


def compute_kundli(profile: BirthProfile) -> dict[str, Any]:
    kundli = _kundli_service.calculate(to_astro_request(profile))
    payload: dict[str, Any] = kundli.model_dump(mode="json")
    return payload


def kundli_for(container: Container, profile: BirthProfile) -> tuple[dict[str, Any], bool]:
    """The Kundli for a profile version (cached; never recomputed for an unchanged profile)."""
    require_birth_time(profile)
    return container.cache.get_or_compute(
        "kundli",
        str(profile.user_id),
        profile_versions(profile),
        engine_versions(),
        lambda: compute_kundli(profile),
    )


def natal_reference(kundli_json: dict[str, Any]) -> NatalReference:
    from pandit_astro_engine import Kundli

    return NatalReference.from_kundli(Kundli.model_validate(kundli_json))


def compute_dasha(profile: BirthProfile, depth: int) -> dict[str, Any]:
    facts = _dasha_service.calculate(
        to_astro_request(profile),
        DashaConfiguration(depth=depth),
        to_birth_time_input(profile),
    )
    payload: dict[str, Any] = facts.model_dump(mode="json")
    return payload


def dasha_for(
    container: Container, profile: BirthProfile, depth: int
) -> tuple[dict[str, Any], bool]:
    require_birth_time(profile)
    return container.cache.get_or_compute(
        "dasha",
        str(profile.user_id),
        {**profile_versions(profile), "depth": depth},
        engine_versions(),
        lambda: compute_dasha(profile, depth),
    )


def current_periods(facts: dict[str, Any], at: dt.datetime) -> dict[str, Any]:
    """The period of each level containing ``at`` (UTC, start inclusive, end exclusive)."""
    found: dict[str, Any] = {}
    for period in facts.get("periods", []):
        start = dt.datetime.fromisoformat(period["start_utc"])
        end = dt.datetime.fromisoformat(period["end_utc"])
        if start <= at < end:
            found[str(period["level"])] = period
    return found


def transitions_between(
    facts: dict[str, Any], start: dt.datetime, end: dt.datetime
) -> list[dict[str, Any]]:
    """Periods beginning in ``[start, end)``, in chronological order."""
    rows = [
        p
        for p in facts.get("periods", [])
        if start <= dt.datetime.fromisoformat(p["start_utc"]) < end
    ]
    return sorted(rows, key=lambda p: (p["start_utc"], p["level"]))


def compute_transit(
    natal: NatalReference,
    at: dt.datetime | None,
    window: tuple[dt.datetime, dt.datetime] | None,
    include_sade_sati: bool,
) -> dict[str, Any]:
    from pandit_astro_engine.transits.models import TransitRequest

    config = TransitConfiguration(include_sade_sati=include_sade_sati)
    request = TransitRequest(
        natal=natal,
        config=config,
        at_utc=at,
        window_start_utc=window[0] if window else None,
        window_end_utc=window[1] if window else None,
    )
    payload: dict[str, Any] = _transit_service.calculate(request).model_dump(mode="json")
    return payload
