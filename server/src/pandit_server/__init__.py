"""server: FastAPI HTTP composition layer.

Per ADR-007: composes the five canonical services (`astro-engine`,
`rule-engine`, `agent`, `knowledge`, `verification`) into callable
endpoints. Owns no business logic itself -- routers, dependency wiring,
and the auth-token-validation handoff from the API Gateway only.

Phase 3 scope: application factory, health/readiness endpoints, request-ID
middleware, structured error handling, and the `/api/v1` versioning
foundation. Domain business endpoints (`/charts`, `/dashas`, `/chat`, ...)
are added starting the phase that implements each corresponding engine.
"""

__version__ = "0.1.0"
