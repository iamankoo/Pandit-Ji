"""FastAPI dependencies: the container, the authenticated principal, the current user, limits."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from pandit_server.auth.oidc import AuthError, Principal
from pandit_server.container import Container
from pandit_server.db.models import User
from pandit_server.errors import ApiError
from pandit_server.platform_services import sha256_hex


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def get_session(container: ContainerDep) -> Iterator[Session]:
    """One transaction per request: committed when the handler returns, rolled back on error."""
    with container.db.session() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def get_principal(request: Request, container: ContainerDep) -> Principal:
    """Authenticate the bearer token. Failed attempts are counted per IP (brute-force guard)."""
    settings = container.settings
    ip = client_ip(request)
    token = _bearer(request)
    try:
        if token is None:
            raise AuthError("missing_token", "Authentication required.")
        principal = container.verifier.verify(token)
    except AuthError as exc:
        container.metrics.inc("auth_failures_total", reason=exc.code)
        container.limiter.enforce("authfail", ip, settings.rate_limit_auth * 3)
        status = 503 if exc.code == "identity_provider_unavailable" else 401
        raise ApiError(
            status,
            exc.code if status == 503 else "unauthorized",
            exc.message,
            headers={"WWW-Authenticate": "Bearer"} if status == 401 else None,
        ) from exc
    request.state.principal = principal
    return principal


PrincipalDep = Annotated[Principal, Depends(get_principal)]


def provision_user(session: Session, principal: Principal) -> User:
    """The application user for the token's subject (created on first valid use)."""
    user = session.scalar(select(User).where(User.subject == principal.subject))
    if user is None:
        user = User(subject=principal.subject, display_name=principal.display_name)
        session.add(user)
        session.flush()
    return user


def get_current_user(principal: PrincipalDep, session: SessionDep) -> User:
    return provision_user(session, principal)


UserDep = Annotated[User, Depends(get_current_user)]


def require_admin(principal: PrincipalDep, container: ContainerDep) -> Principal:
    if not principal.has_role(container.settings.auth_admin_role):
        raise ApiError(403, "forbidden", "You do not have access to this resource.")
    return principal


def limited(kind: str = "default") -> Callable[..., None]:
    """Per-user rate limit for a class of endpoints (``default``, ``expensive`` or ``auth``)."""

    def dependency(request: Request, container: ContainerDep, principal: PrincipalDep) -> None:
        settings = container.settings
        limit = {
            "default": settings.rate_limit_default,
            "expensive": settings.rate_limit_expensive,
            "auth": settings.rate_limit_auth,
        }[kind]
        decision = container.limiter.enforce(kind, principal.subject, limit)
        request.state.rate_limit = decision

    return dependency


def public_limited(request: Request, container: ContainerDep) -> None:
    """Per-IP limit for unauthenticated endpoints."""
    container.limiter.enforce(
        "anon", sha256_hex(client_ip(request)), container.settings.rate_limit_anonymous
    )
