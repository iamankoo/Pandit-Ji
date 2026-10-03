"""The single versioned configuration source for the LLM layer.

Three kinds of setting, kept apart:

* **model configuration** (the manifest): what the model is and what it can do;
* **service settings** (this module, ``LLMSettings``): where it runs and the operational limits;
* **request generation configuration** (``GENERATION_PROFILES``): sampling per request.

Nothing else in the package hardcodes a sampling value, a timeout or a host. A hosted third-party
API is not a valid endpoint: only hosts the operator lists in ``allowed_hosts`` are reachable.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from pandit_contracts.llm import GenerationConfig, LLMErrorCode
from pandit_shared import BaseServiceSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict

from pandit_agent.llm.errors import LLMFailure

LLM_SETTINGS_VERSION = "llm-settings-1"
GENERATION_CONFIG_VERSION = "gen-1"

# ``model_default`` repeats the values published in the model's own generation_config.json at the
# pinned revision (temperature 0.6, top_p 0.95, top_k 20). ``deterministic`` is greedy decoding
# with a fixed seed: the most reproducible setting the runtime offers (not a bit-for-bit promise).
GENERATION_PROFILES: dict[str, GenerationConfig] = {
    "deterministic": GenerationConfig(
        config_version=GENERATION_CONFIG_VERSION,
        temperature=0.0,
        top_p=1.0,
        top_k=1,
        max_new_tokens=1024,
        seed=0,
        timeout_s=120.0,
    ),
    "model_default": GenerationConfig(
        config_version=GENERATION_CONFIG_VERSION,
        temperature=0.6,
        top_p=0.95,
        top_k=20,
        max_new_tokens=1024,
        timeout_s=120.0,
    ),
}


def generation_profile(name: str) -> GenerationConfig:
    try:
        return GENERATION_PROFILES[name]
    except KeyError as exc:
        raise LLMFailure(
            LLMErrorCode.INVALID_CONFIGURATION, f"unknown generation profile {name!r}"
        ) from exc


def default_assets_dir() -> Path:
    """``services/agent/llm`` in a source checkout (set ``assets_dir`` for other layouts)."""
    return Path(__file__).resolve().parents[3] / "llm"


class LLMSettings(BaseServiceSettings):
    model_config = SettingsConfigDict(env_prefix="AGENT_LLM_", extra="ignore")

    settings_version: str = LLM_SETTINGS_VERSION
    manifest_name: str = "qwen3-8b.json"
    assets_dir: Path | None = None
    endpoint_url: str = "http://127.0.0.1:8000"
    served_model_name: str | None = None
    allowed_hosts: str = "localhost,127.0.0.1,::1"
    model_dir: Path | None = None
    verify_artifacts: bool = True
    max_context_chars: int = Field(default=60000, gt=0)
    structured_retries: int = Field(default=1, ge=0, le=3)
    # A scripted test runtime is refused unless a test (or a developer) opts in explicitly.
    allow_test_fixture: bool = False

    @property
    def resolved_assets_dir(self) -> Path:
        return self.assets_dir if self.assets_dir is not None else default_assets_dir()

    @property
    def allowed_host_set(self) -> frozenset[str]:
        return frozenset(h.strip().lower() for h in self.allowed_hosts.split(",") if h.strip())


def check_endpoint(url: str, allowed_hosts: frozenset[str]) -> str:
    """Return ``url`` if it points at an operator-approved host, else refuse it.

    This is what keeps user content from being sent to a hosted provider by configuration
    accident: the default allows loopback only, and every other host must be listed on purpose.
    """
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise LLMFailure(LLMErrorCode.ENDPOINT_NOT_PERMITTED, "endpoint must be an http(s) URL")
    if parts.username or parts.password:
        raise LLMFailure(LLMErrorCode.ENDPOINT_NOT_PERMITTED, "endpoint must not embed credentials")
    if parts.hostname.lower() not in allowed_hosts:
        raise LLMFailure(
            LLMErrorCode.ENDPOINT_NOT_PERMITTED,
            "endpoint host is not in the operator allow-list (self-hosted inference only)",
        )
    return url.rstrip("/")
