"""Liveness, readiness and metrics.

Liveness (`/healthz`): the process is alive; never depends on an external dependency.

Readiness (`/readyz`): the critical dependencies (PostgreSQL, Valkey) respond and each domain
service reports healthy. The language model is reported as a *capability*, not a dependency: chat
needs it, every other endpoint works without it, so its absence degrades only chat.

Metrics (`/metrics`): Prometheus text, counters and latency sums, no labels carrying personal data.
Protected by ``METRICS_TOKEN`` when set; hidden in production when no token is configured.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header
from fastapi.responses import PlainTextResponse
from pandit_agent import get_health as agent_health
from pandit_astro_engine import get_health as astro_engine_health
from pandit_contracts.health import HealthState, HealthStatus
from pandit_knowledge import get_health as knowledge_health
from pandit_rule_engine import get_health as rule_engine_health
from pandit_verification import get_health as verification_health

from pandit_server import __version__
from pandit_server.deps import ContainerDep
from pandit_server.errors import not_found

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


def _dependency(component: str, ok: bool, detail: str | None = None) -> HealthStatus:
    return HealthStatus(
        component=component,
        version="n/a",
        state=HealthState.OK if ok else HealthState.UNAVAILABLE,
        detail=None if ok else detail,
    )


def _llm_capability(container: Any) -> dict[str, str]:
    llm = getattr(container, "_llm", None)
    if llm is None:
        return {"component": "llm", "state": "not_initialized"}
    try:
        health = llm.health()
        return {"component": "llm", "state": str(getattr(health.state, "value", health.state))}
    except Exception:  # noqa: BLE001 - readiness must never raise
        return {"component": "llm", "state": "unavailable"}


@router.get("/readyz")
def readiness(container: ContainerDep) -> dict[str, object]:
    store = container.store
    degraded = bool(getattr(store, "degraded", False))
    dependencies = [
        _dependency("postgresql", container.db.ping(), "database unreachable"),
        _dependency("valkey", store.ping() and not degraded, "valkey unreachable"),
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
        "capabilities": [_llm_capability(container)],
    }


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(container: ContainerDep, x_metrics_token: str | None = Header(default=None)) -> str:
    token = container.settings.metrics_token
    if token is None:
        if container.settings.app_env.value == "production":
            raise not_found("page")
    elif x_metrics_token != token:
        raise not_found("page")
    return container.metrics.render()
