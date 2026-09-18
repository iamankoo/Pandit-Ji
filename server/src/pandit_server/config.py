"""Typed configuration for `server/`.

Every value is read from the environment (never hard-coded), per
`docs/ARCHITECTURE.md` §"Security Architecture" and the Phase 3
"Configuration Architecture" requirement. See `.env.example` at the repo
root for the full variable list and safe placeholder values.
"""

from __future__ import annotations

from pandit_shared import BaseServiceSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict


class Settings(BaseServiceSettings):
    """`app_env`/`log_level` are inherited from `BaseServiceSettings` (reads
    `APP_ENV`/`LOG_LEVEL` case-insensitively) -- only server-specific
    settings are declared here."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    # --- Core ---
    api_version: str = Field(default="v1", alias="API_VERSION")

    # --- Database (PostgreSQL) ---
    database_url: str = Field(
        default="postgresql+psycopg://pandit:pandit@postgres:5432/pandit",
        alias="DATABASE_URL",
    )

    # --- Cache / queue broker (Valkey; Redis-protocol-compatible, see ADR-005) ---
    valkey_url: str = Field(default="redis://valkey:6379/0", alias="VALKEY_URL")

    # --- Auth (Keycloak / OIDC) ---
    auth_issuer_url: str = Field(
        default="http://keycloak:8080/realms/pandit-ji", alias="AUTH_ISSUER_URL"
    )
    auth_client_id: str = Field(default="pandit-server", alias="AUTH_CLIENT_ID")
    auth_client_secret: str = Field(default="changeme-in-env", alias="AUTH_CLIENT_SECRET")

    # --- Object storage (S3-compatible; MinIO by default, see TECH_STACK.md) ---
    object_storage_endpoint: str = Field(
        default="http://minio:9000", alias="OBJECT_STORAGE_ENDPOINT"
    )
    object_storage_bucket: str = Field(default="pandit-dev", alias="OBJECT_STORAGE_BUCKET")
    object_storage_access_key: str = Field(
        default="changeme-in-env", alias="OBJECT_STORAGE_ACCESS_KEY"
    )
    object_storage_secret_key: str = Field(
        default="changeme-in-env", alias="OBJECT_STORAGE_SECRET_KEY"
    )

    # --- AI / LLM inference (LLMProvider interface target -- ADR-002) ---
    ai_inference_base_url: str = Field(
        default="http://localhost:11434", alias="AI_INFERENCE_BASE_URL"
    )
