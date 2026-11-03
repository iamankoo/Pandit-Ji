"""Request metrics, safe request logging, security headers and the request-size limit."""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from pandit_server.platform_services import Metrics

_log = logging.getLogger("pandit_server.http")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


class PlatformMiddleware(BaseHTTPMiddleware):
    """Logs method, route template, status and latency only: never a query string, header, body,
    token or any personal data."""

    def __init__(self, app, metrics: Metrics, max_request_bytes: int) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._metrics = metrics
        self._max = max_request_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started = time.perf_counter()
        length = request.headers.get("content-length")
        if length is not None and length.isdigit() and int(length) > self._max:
            response: Response = JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "payload_too_large",
                        "message": "The request body is too large.",
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
            )
        else:
            response = await call_next(request)
        elapsed = time.perf_counter() - started
        route = request.scope.get("route")
        template = getattr(route, "path", None) or "unmatched"
        self._metrics.observe_request(request.method, template, response.status_code, elapsed)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        decision = getattr(request.state, "rate_limit", None)
        if decision is not None:
            response.headers["X-RateLimit-Limit"] = str(decision.limit)
            response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        _log.info(
            "http_request",
            extra={
                "method": request.method,
                "route": template,
                "status": response.status_code,
                "duration_ms": round(elapsed * 1000, 2),
            },
        )
        return response
