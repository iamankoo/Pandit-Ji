"""`/api/v1` versioning: the public API surface of the backend (docs/ARCHITECTURE.md "API
Architecture"). A breaking change to this version introduces `/api/v2`; `/api/v1` keeps working.
"""

from fastapi import APIRouter


def build_v1_router() -> APIRouter:
    from pandit_server.api.v1 import (
        auth,
        calculations,
        charts,
        chat,
        platform_api,
        profiles,
        reports,
        users,
        ws,
    )

    router = APIRouter(prefix="/api/v1")
    for module in (
        auth,
        users,
        profiles,
        charts,
        calculations,
        chat,
        reports,
        platform_api,
        ws,
    ):
        router.include_router(module.router)
    return router


__all__ = ["build_v1_router"]
