"""Model manifest: the identity, licence and provenance record of one model artifact set.

Four things are kept apart (``docs/ARCHITECTURE.md`` section 36):

* model **code**: this package;
* model **configuration**: ``settings.py`` (sampling, limits, endpoints);
* model **manifest**: a JSON file under ``services/agent/llm/manifests/`` (this module reads it);
* model **weights**: never in git; acquired explicitly and verified against the manifest hashes.

A manifest for a real model must carry a pinned 40-hex revision, a SHA-256 for every artifact and a
licence record that was read. A manifest for a test fixture says so and can never be production
eligible. Nothing here downloads anything.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pandit_contracts.llm import LLMErrorCode, LLMLanguage
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from pandit_agent.llm.errors import LLMFailure

SUPPORTED_RUNTIMES = frozenset({"vllm", "mock"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_CHUNK = 1024 * 1024


class _M(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", protected_namespaces=())


class SourceInfo(_M):
    url: str
    revision_url: str
    gated: bool
    last_modified_at_source: str


class LicenseInfo(_M):
    spdx: str
    name: str
    license_file: str
    license_file_sha256: str
    verification: Literal["LICENSE_FILE_READ", "NOT_APPLICABLE", "UNVERIFIED"]
    commercial_use: str
    redistribution_and_derivatives: str
    legal_status: Literal["LEGAL_REVIEW_REQUIRED", "COUNSEL_CLEARED", "NOT_APPLICABLE"]


class Artifact(_M):
    filename: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256: str


class TokenizerInfo(_M):
    tokenizer_class: str
    tokenizer_config_sha256: str
    bos_token: str | None
    add_bos_token: bool
    eos_token: str
    pad_token: str | None
    generation_eos_token_ids: tuple[int, ...]
    special_tokens: tuple[str, ...]
    reserved_added_tokens: tuple[str, ...] = ()


class ChatTemplateInfo(_M):
    format: Literal["chatml"]
    file: str
    sha256: str
    extracted_from: str
    supports_enable_thinking: bool
    generation_prompt: str = Field(min_length=1)


class ContextInfo(_M):
    native_tokens_model_card: int = Field(gt=0)
    max_position_embeddings_config_json: int = Field(gt=0)
    extended_tokens_with_yarn: int = Field(gt=0)
    extended_enabled: bool
    operational_limit_tokens: int = Field(gt=0)


class LanguagesInfo(_M):
    supported_interface_modes: tuple[LLMLanguage, ...] = Field(min_length=1)
    evidence: str
    quality_status: Literal["UNEVALUATED", "NOT_APPLICABLE"]


class RuntimeInfo(_M):
    name: str
    minimum_version_from_model_card: str
    latest_version_observed: str
    latest_version_observed_on: str
    latest_version_observed_note: str
    serving_mode: str
    runtime_tested_against_real_model: bool


class HardwareInfo(_M):
    expected_class: str
    weights_size_bytes: int = Field(ge=0)
    basis: str


class GenerationDefaultsFromModel(_M):
    temperature: float
    top_p: float
    top_k: int
    do_sample: bool


class ProvenanceInfo(_M):
    verified_on: str
    verified_by: str
    weights_committed_to_git: bool
    acquisition: str
    notes: str


class ModelManifest(_M):
    manifest_version: Literal[1]
    manifest_id: str = Field(min_length=1)
    configuration_version: str = Field(min_length=1)
    test_fixture: bool
    production_eligible: bool
    production_blockers: tuple[str, ...]
    model_id: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    source: SourceInfo
    license: LicenseInfo
    artifacts: tuple[Artifact, ...]
    tokenizer: TokenizerInfo
    chat_template: ChatTemplateInfo
    context: ContextInfo
    languages: LanguagesInfo
    runtime: RuntimeInfo
    quantization: str
    hardware: HardwareInfo
    generation_config_from_model: GenerationDefaultsFromModel
    provenance: ProvenanceInfo

    @model_validator(mode="after")
    def _rules(self) -> ModelManifest:
        problems: list[str] = []
        if self.runtime.name not in SUPPORTED_RUNTIMES:
            problems.append(f"unsupported runtime {self.runtime.name!r}")
        if self.provenance.weights_committed_to_git:
            problems.append("weights must never be committed to git")
        if not _SHA256.match(self.chat_template.sha256):
            problems.append("chat_template.sha256 is not a SHA-256")
        if not _SHA256.match(self.tokenizer.tokenizer_config_sha256):
            problems.append("tokenizer_config_sha256 is not a SHA-256")
        if self.tokenizer.eos_token not in self.tokenizer.special_tokens:
            problems.append("eos_token must be one of the special tokens")
        if self.context.operational_limit_tokens > self.context.extended_tokens_with_yarn:
            problems.append("operational limit exceeds the model's extended context")
        if (
            self.context.operational_limit_tokens > self.context.native_tokens_model_card
            and not self.context.extended_enabled
        ):
            problems.append("operational limit exceeds the native context while YaRN is off")
        if self.production_eligible and self.production_blockers:
            problems.append("a manifest with production blockers is not production eligible")
        if self.test_fixture:
            if self.production_eligible:
                problems.append("a test fixture can never be production eligible")
        else:
            problems.extend(self._real_model_problems())
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def _real_model_problems(self) -> list[str]:
        problems: list[str] = []
        if not _REVISION.match(self.model_revision):
            problems.append("model_revision must be a pinned 40-hex revision")
        if not self.artifacts:
            problems.append("a real model needs artifacts with hashes")
        for artifact in self.artifacts:
            if not _SHA256.match(artifact.sha256):
                problems.append(f"artifact {artifact.filename} has no valid SHA-256")
        if self.license.verification != "LICENSE_FILE_READ":
            problems.append("the licence has not been read and recorded")
        if not _SHA256.match(self.license.license_file_sha256):
            problems.append("license_file_sha256 is not a SHA-256")
        if not self.license.spdx or self.license.spdx == "NONE":
            problems.append("a real model needs a licence identifier")
        return problems

    @property
    def artifact_hashes(self) -> tuple[str, ...]:
        return tuple(a.sha256 for a in self.artifacts)


def load_manifest(path: Path) -> ModelManifest:
    """Read and validate a manifest. Any defect is an ``INVALID_MANIFEST`` failure."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LLMFailure(LLMErrorCode.INVALID_MANIFEST, f"cannot read manifest: {exc}") from exc
    try:
        return ModelManifest.model_validate(raw)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"]) or "manifest"
        raise LLMFailure(LLMErrorCode.INVALID_MANIFEST, f"{where}: {first['msg']}") from exc


def normalized_sha256(text: str) -> str:
    """SHA-256 of text with CRLF folded to LF (working trees may be CRLF, the index is LF)."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model_directory(manifest: ModelManifest, model_dir: Path) -> int:
    """Check every manifest artifact in ``model_dir`` (presence, size, SHA-256).

    Acquisition is explicit and happens outside this code; this is the check that what is on disk
    is exactly what the manifest pins. Returns the number of verified files.
    """
    if manifest.test_fixture:
        return 0
    if not model_dir.is_dir():
        raise LLMFailure(LLMErrorCode.MODEL_UNAVAILABLE, "the model directory does not exist")
    for artifact in manifest.artifacts:
        path = model_dir / artifact.filename
        if not path.is_file():
            raise LLMFailure(
                LLMErrorCode.MODEL_UNAVAILABLE, f"missing artifact {artifact.filename}"
            )
        if path.stat().st_size != artifact.size_bytes:
            raise LLMFailure(
                LLMErrorCode.MODEL_LOAD_FAILURE, f"size mismatch for {artifact.filename}"
            )
        if sha256_file(path) != artifact.sha256:
            raise LLMFailure(
                LLMErrorCode.MODEL_LOAD_FAILURE, f"SHA-256 mismatch for {artifact.filename}"
            )
    return len(manifest.artifacts)
