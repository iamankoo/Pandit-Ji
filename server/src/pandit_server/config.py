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

    # --- Auth details (OIDC resource server; Keycloak is the identity provider) ---
    auth_jwks_url: str | None = Field(default=None, alias="AUTH_JWKS_URL")
    auth_audience: str = Field(default="pandit-server", alias="AUTH_AUDIENCE")
    auth_algorithms: str = Field(default="RS256", alias="AUTH_ALGORITHMS")
    auth_clock_skew_seconds: int = Field(default=30, alias="AUTH_CLOCK_SKEW_SECONDS")
    auth_jwks_cache_seconds: int = Field(default=300, alias="AUTH_JWKS_CACHE_SECONDS")
    auth_admin_role: str = Field(default="pandit-admin", alias="AUTH_ADMIN_ROLE")

    # --- Rate limiting (requests per window, per user or per IP; Valkey-backed) ---
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_default: int = Field(default=120, alias="RATE_LIMIT_DEFAULT")
    rate_limit_anonymous: int = Field(default=30, alias="RATE_LIMIT_ANONYMOUS")
    rate_limit_expensive: int = Field(default=20, alias="RATE_LIMIT_EXPENSIVE")
    rate_limit_auth: int = Field(default=10, alias="RATE_LIMIT_AUTH")

    # --- Caching (deterministic results only) ---
    cache_ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")

    # --- Limits and safety ---
    max_request_bytes: int = Field(default=262144, alias="MAX_REQUEST_BYTES")
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")
    metrics_token: str | None = Field(default=None, alias="METRICS_TOKEN")
    memory_retention_days: int = Field(default=365, alias="MEMORY_RETENTION_DAYS")

    # --- Self-hosted LLM boundary (Phase 14; no hosted fallback exists) ---
    llm_manifest_name: str = Field(default="qwen3-8b.json", alias="LLM_MANIFEST_NAME")
    chat_max_regenerations: int = Field(default=2, alias="CHAT_MAX_REGENERATIONS")
    chat_max_evidence_items: int = Field(default=120, alias="CHAT_MAX_EVIDENCE_ITEMS")

    # --- Background jobs (Celery over Valkey; eager mode runs tasks inline, for tests) ---
    celery_eager: bool = Field(default=False, alias="CELERY_EAGER")
