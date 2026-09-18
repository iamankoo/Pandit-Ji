"""FastAPI application factory for `server/`.

`create_app()` wires together: structured logging, request-ID middleware,
structured error handlers, the liveness/readiness routes, and the
`/api/v1` versioning foundation. Run locally with:

    uvicorn pandit_server.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from pandit_shared.logging import configure_logging

from pandit_server import __version__
from pandit_server.api import health as health_routes
from pandit_server.api.v1 import router as v1_router
from pandit_server.config import Settings
from pandit_server.errors import register_exception_handlers
from pandit_server.middleware.request_id import RequestIDMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(service="server", environment=settings.app_env, level=settings.log_level)

    app = FastAPI(
        title="Pandit Ji Server",
        version=__version__,
        description=(
            "FastAPI HTTP composition layer (ADR-007). "
            "See docs/ARCHITECTURE.md for the full architecture."
        ),
    )

    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)

    app.include_router(health_routes.router)
    app.include_router(v1_router)

    return app


app = create_app()
