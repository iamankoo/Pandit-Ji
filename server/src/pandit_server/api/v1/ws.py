"""WebSocket chat streaming (`/api/v1/ws/chat`, docs/ARCHITECTURE.md "API Architecture").

Protocol (JSON text frames):

1. client -> ``{"type": "auth", "token": "<access token>"}`` within 5 seconds (the token is never
   accepted in the URL, where it would end up in logs);
2. client -> ``{"type": "chat", "id": "<client id>", ...ChatRequest}`` any number of times;
3. server -> ``{"type": "status", "id", "state": "started"}`` then
   ``{"type": "result", "id", "payload": {...}}`` or ``{"type": "error", "id", "code", "message"}``.

Each connection belongs to one authenticated user; every profile lookup is scoped to that user, so
no message can reach another user. A failed auth closes with code 4401, a schema violation is a
typed error (the connection stays open), a rate-limited message is a typed error, and oversize
frames close the connection with 1009. Browsers must send an allowed ``Origin``.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Literal

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select

from pandit_server.api.v1.chat import answer, outcome_payload
from pandit_server.auth.oidc import AuthError, Principal
from pandit_server.container import Container
from pandit_server.db.models import BirthProfile
from pandit_server.deps import provision_user
from pandit_server.errors import ApiError
from pandit_server.schemas import ChatRequest

router = APIRouter(tags=["chat"])

AUTH_TIMEOUT_SECONDS = 5.0


class _Auth(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["auth"]
    token: str = Field(min_length=10, max_length=8192)


class _Chat(ChatRequest):
    type: Literal["chat"]
    id: str = Field(min_length=1, max_length=64)


def _origin_allowed(container: Container, websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    if origin is None:
        return True  # a non-browser client
    allowed = [o.strip() for o in container.settings.cors_origins.split(",") if o.strip()]
    return origin in allowed


def _run(container: Container, principal: Principal, message: _Chat) -> dict[str, Any]:
    """Blocking work: resolve the caller's own profile and run the verified pipeline."""
    with container.db.session() as session:
        user = provision_user(session, principal)
        if message.profile_id is None:
            raise ApiError(422, "profile_required", "Choose a birth profile for this question.")
        profile = session.scalar(
            select(BirthProfile).where(
                BirthProfile.id == message.profile_id, BirthProfile.user_id == user.id
            )
        )
        if profile is None:
            raise ApiError(404, "not_found", "The requested birth profile was not found.")
        outcome = answer(container, profile, message, uuid.uuid4().hex)
        return outcome_payload(outcome, None)


async def _send_error(websocket: WebSocket, ident: str | None, code: str, message: str) -> None:
    await websocket.send_json({"type": "error", "id": ident, "code": code, "message": message})


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    container: Container = websocket.app.state.container
    if not _origin_allowed(container, websocket):
        await websocket.close(code=4403)
        return
    await websocket.accept()
    max_bytes = container.settings.max_request_bytes
    try:
        first = await asyncio.wait_for(websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS)
        if len(first) > max_bytes:
            await websocket.close(code=1009)
            return
        auth = _Auth.model_validate(json.loads(first))
        principal = await run_in_threadpool(container.verifier.verify, auth.token)
    except (TimeoutError, asyncio.TimeoutError, ValueError, ValidationError, AuthError):
        container.metrics.inc("ws_auth_failures_total")
        await websocket.close(code=4401)
        return
    await websocket.send_json({"type": "ready"})
    try:
        while True:
            text = await websocket.receive_text()
            if len(text) > max_bytes:
                await websocket.close(code=1009)
                return
            ident: str | None = None
            try:
                payload = json.loads(text)
                ident = str(payload.get("id")) if isinstance(payload, dict) else None
                message = _Chat.model_validate(payload)
            except (ValueError, ValidationError):
                await _send_error(websocket, ident, "validation_error", "Invalid message.")
                continue
            decision = container.limiter.check(
                "ws", principal.subject, container.settings.rate_limit_expensive
            )
            if not decision.allowed:
                await _send_error(websocket, message.id, "rate_limited", "Too many requests.")
                continue
            await websocket.send_json({"type": "status", "id": message.id, "state": "started"})
            try:
                result = await run_in_threadpool(_run, container, principal, message)
            except ApiError as exc:
                await _send_error(websocket, message.id, exc.code, exc.message)
                continue
            except Exception:  # noqa: BLE001 - never leak internals over the socket
                await _send_error(websocket, message.id, "internal_error", "An error occurred.")
                continue
            await websocket.send_json({"type": "result", "id": message.id, "payload": result})
    except WebSocketDisconnect:
        return
