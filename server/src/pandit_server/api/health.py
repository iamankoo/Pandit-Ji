"""Liveness and readiness endpoints.

Liveness (`/healthz`): the process is alive. Never depends on an external
dependency -- a slow/unavailable database must not make the process look
dead and get killed/restarted unnecessarily.

Readiness (`/readyz`): the process can actually serve requests -- checks
that its real dependencies (PostgreSQL, the Valkey/Redis-protocol cache)
respond, and reports each of the five domain services' own health. A
best-effort, short-timeout check per dependency; any failure degrades
readiness rather than raising.
"""

from __future__ import annotations

import redis
from fastapi import APIRouter, Depends
from pandit_agent import get_health as agent_health
from pandit_astro_engine import get_health as astro_engine_health
from pandit_contracts.health import HealthState, HealthStatus
from pandit_knowledge import get_health as knowledge_health
from pandit_rule_engine import get_health as rule_engine_health
from pandit_verification import get_health as verification_health

from pandit_server import __version__
from pandit_server.config import Settings

router = APIRouter(tags=["health"])


def get_settings() -> Settings:
    return Settings()


@router.get("/healthz")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


def _check_database(database_url: str) -> HealthStatus:
    try:
        import psycopg

        with psycopg.connect(database_url, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return HealthStatus(component="postgresql", version="n/a", state=HealthState.OK)
    except Exception as exc:  # noqa: BLE001 - readiness must never raise
        return HealthStatus(
            component="postgresql", version="n/a", state=HealthState.UNAVAILABLE, detail=str(exc)
        )


def _check_cache(valkey_url: str) -> HealthStatus:
    try:
        client = redis.from_url(valkey_url, socket_connect_timeout=2)  # type: ignore[no-untyped-call]
        client.ping()
        return HealthStatus(component="valkey", version="n/a", state=HealthState.OK)
    except Exception as exc:  # noqa: BLE001 - readiness must never raise
        return HealthStatus(
            component="valkey", version="n/a", state=HealthState.UNAVAILABLE, detail=str(exc)
        )


@router.get("/readyz")
async def readiness(settings: Settings = Depends(get_settings)) -> dict[str, object]:  # noqa: B008
    dependencies = [
        _check_database(settings.database_url),
        _check_cache(settings.valkey_url),
    ]
    services = [
        astro_engine_health(),
        rule_engine_health(),
        agent_health(),
        knowledge_health(),
        verification_health(),
    ]
    all_ok = all(s.state == HealthState.OK for s in dependencies + services)
    return {
        "status": "ready" if all_ok else "not_ready",
        "server_version": __version__,
        "dependencies": [d.model_dump() for d in dependencies],
        "services": [s.model_dump() for s in services],
    }
