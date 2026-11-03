"""FastAPI application factory for `server/`.

`create_app()` wires structured logging, request-ID and platform middleware (metrics, security
headers, size limit, CORS), the structured error handlers, health/readiness/metrics, and the
versioned `/api/v1` routers. Run locally with:

    uvicorn pandit_server.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pandit_shared.logging import configure_logging

from pandit_server import __version__
from pandit_server.api import health as health_routes
from pandit_server.api.v1 import build_v1_router
from pandit_server.config import Settings
from pandit_server.container import Container, build_container
from pandit_server.errors import register_exception_handlers
from pandit_server.middleware.platform import PlatformMiddleware
from pandit_server.middleware.request_id import RequestIDMiddleware


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(service="server", environment=settings.app_env, level=settings.log_level)
    container = container or build_container(settings)

    app = FastAPI(
        title="Pandit Ji Server",
        version=__version__,
        description=(
            "FastAPI HTTP composition layer (ADR-007). "
            "See docs/ARCHITECTURE.md for the full architecture."
        ),
    )
    app.state.container = container

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        )
    app.add_middleware(
        PlatformMiddleware, metrics=container.metrics, max_request_bytes=settings.max_request_bytes
    )
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)

    app.include_router(health_routes.router)
    app.include_router(build_v1_router())

    return app


def _default_app() -> FastAPI:
    return create_app()


def __getattr__(name: str) -> FastAPI:
    # ``uvicorn pandit_server.main:app``: built lazily so importing the module has no side effects.
    if name == "app":
        return _default_app()
    raise AttributeError(name)
