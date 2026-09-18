"""Structured error handling foundation.

Every unhandled/HTTP error response is shaped consistently:
`{"error": {"code": ..., "message": ..., "request_id": ...}}`. This is a
foundation for later phases' failure architecture
(`docs/ARCHITECTURE.md` §"Failure Architecture") -- domain-specific error
codes are added as each domain endpoint is built.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

# `starlette.exceptions.HTTPException` (not `fastapi.HTTPException`, which is
# a subclass) is what Starlette's router itself raises for an unmatched route
# (a plain 404). Registering the handler for the base class here catches both
# that internal case and any `fastapi.HTTPException` raised by application
# code, since exception-handler dispatch is isinstance-based on the ancestor.


def _error_body(code: str, message: str, request: Request) -> dict[str, dict[str, str | None]]:
    request_id = getattr(request.state, "request_id", None)
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(
                code=f"http_{exc.status_code}", message=str(exc.detail), request=request
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                code="validation_error", message="Request validation failed.", request=request
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                code="internal_error", message="An unexpected error occurred.", request=request
            ),
        )
