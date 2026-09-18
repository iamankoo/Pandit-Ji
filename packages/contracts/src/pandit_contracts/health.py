"""Shared health-status contract.

Every service and `server/` reports health the same shape, so a caller (a
readiness probe, an integration test, or a future admin dashboard) never
needs component-specific parsing.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class HealthState(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class HealthStatus(BaseModel):
    """Health/version report for a single component."""

    component: str = Field(..., description="Canonical component name, e.g. 'astro-engine'.")
    state: HealthState = Field(default=HealthState.OK)
    version: str = Field(..., description="Component package version.")
    detail: str | None = Field(default=None, description="Optional human-readable detail.")
