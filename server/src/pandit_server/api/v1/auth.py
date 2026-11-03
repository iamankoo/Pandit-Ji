"""Authentication endpoints. Registration, login, password reset, MFA and brute-force lockout are
Keycloak's (TECH_STACK.md); the backend is the resource server. It exposes the OIDC settings a
client needs and token revocation (logout), and nothing that handles a password.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from pandit_server.deps import (
    ContainerDep,
    PrincipalDep,
    SessionDep,
    limited,
    public_limited,
)
from pandit_server.platform_services import record_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", dependencies=[Depends(public_limited)])
def oidc_config(container: ContainerDep) -> dict[str, object]:
    """Public OIDC settings for clients (authorization-code flow with PKCE). No secrets."""
    s = container.settings
    issuer = s.auth_issuer_url.rstrip("/")
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/protocol/openid-connect/auth",
        "token_endpoint": f"{issuer}/protocol/openid-connect/token",
        "jwks_uri": s.auth_jwks_url or f"{issuer}/protocol/openid-connect/certs",
        "registration_endpoint_hint": f"{issuer}/protocol/openid-connect/registrations",
        "audience": s.auth_audience,
        "flow": "authorization_code_pkce",
        "managed_by": "keycloak",
    }


@router.post("/logout", status_code=204, dependencies=[Depends(limited("auth"))])
def logout(
    request: Request, container: ContainerDep, principal: PrincipalDep, session: SessionDep
) -> None:
    """Revoke the presented access token."""
    container.verifier.revoke_token(principal)
    record_audit(
        session,
        subject=principal.subject,
        action="auth.logout",
        resource_type="session",
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/logout-all", status_code=204, dependencies=[Depends(limited("auth"))])
def logout_all(
    request: Request, container: ContainerDep, principal: PrincipalDep, session: SessionDep
) -> None:
    """Revoke every token of this user issued so far."""
    container.verifier.revoke_subject(principal.subject)
    record_audit(
        session,
        subject=principal.subject,
        action="auth.logout_all",
        resource_type="session",
        request_id=getattr(request.state, "request_id", None),
    )
