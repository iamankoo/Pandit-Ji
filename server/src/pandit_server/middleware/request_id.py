"""Request-ID middleware.

The API Gateway (Traefik) is expected to inject `X-Request-ID` at the edge
(`docs/ARCHITECTURE.md` §4). This middleware reads it if present, else
generates one (e.g. for direct local-dev access without the gateway in
front), binds it for structured logging (`pandit_shared.logging`), and
echoes it back on the response so a client/trace can correlate.
"""

from __future__ import annotations

import uuid

from pandit_shared.logging import bind_request_id
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        bind_request_id(request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        finally:
            bind_request_id(None)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
