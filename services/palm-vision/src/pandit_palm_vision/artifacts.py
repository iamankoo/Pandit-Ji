"""Model artifact policy (Phase 13; standards PM-15, `research/PALM_READING.md` section 10).

No model weights are bundled, downloaded or required by CI. A model artifact may be used as a
production dependency only when it has an identifier, a version, a SHA-256 that matches the file,
a recorded source, a **verified** licence, a provenance note, and declared preprocessing and
runtime compatibility. An artifact that fails any of these is rejected, never used silently.

``validated`` is separate from *usable*: an artifact can be a legitimate dependency (provenance
and licence in order) and still unvalidated for palm lines until a validation report (evaluation
on the governed dataset) is recorded for it. The pipeline reports that honestly
(`LineAnalysisStatus.MODEL_UNVALIDATED`).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pandit_contracts.palm import ModelArtifactRef
from pandit_contracts.palm_canonical import is_sha256_hex

from pandit_palm_vision.identity import PREPROCESSING_ID, PREPROCESSING_VERSION

REQUIRED_PREPROCESSING = f"{PREPROCESSING_ID}:{PREPROCESSING_VERSION}"


class ArtifactPolicyError(ValueError):
    """A model artifact does not satisfy the artifact policy."""


@dataclass(frozen=True)
class ModelArtifact:
    artifact_id: str
    version: str
    role: str
    sha256: str | None
    source: str | None
    licence_id: str | None
    licence_verified: bool
    provenance_note: str | None
    preprocessing_compat: tuple[str, ...] = ()
    runtime_compat: tuple[str, ...] = ()
    validation_report_sha256: str | None = None

    def problems(self) -> tuple[str, ...]:
        found: list[str] = []
        if not self.artifact_id or not self.version:
            found.append("ARTIFACT_ID_OR_VERSION_MISSING")
        if self.sha256 is None or not is_sha256_hex(self.sha256):
            found.append("SHA256_MISSING_OR_INVALID")
        if not self.source:
            found.append("SOURCE_MISSING")
        if not self.licence_id:
            found.append("LICENCE_MISSING")
        if not self.licence_verified:
            found.append("LICENCE_NOT_VERIFIED")
        if not self.provenance_note:
            found.append("PROVENANCE_MISSING")
        if REQUIRED_PREPROCESSING not in self.preprocessing_compat:
            found.append("PREPROCESSING_INCOMPATIBLE")
        if not self.runtime_compat:
            found.append("RUNTIME_COMPATIBILITY_UNDECLARED")
        return tuple(found)

    @property
    def usable(self) -> bool:
        return not self.problems()

    @property
    def validated(self) -> bool:
        """A validation report on the governed dataset is recorded (never assumed)."""
        return self.validation_report_sha256 is not None and is_sha256_hex(
            self.validation_report_sha256
        )

    def require_production_usable(self) -> None:
        problems = self.problems()
        if problems:
            raise ArtifactPolicyError(
                f"model artifact {self.artifact_id!r} is not usable: " + ", ".join(problems)
            )

    def ref(self) -> ModelArtifactRef:
        return ModelArtifactRef(
            artifact_id=self.artifact_id,
            version=self.version,
            sha256=self.sha256,
            role=self.role,
            licence_id=self.licence_id if self.licence_verified else None,
        )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(artifact: ModelArtifact, path: Path) -> None:
    """The file must exist and match the recorded SHA-256."""
    if not path.is_file():
        raise ArtifactPolicyError(f"artifact file not found for {artifact.artifact_id!r}")
    if file_sha256(path) != artifact.sha256:
        raise ArtifactPolicyError(f"artifact file hash differs for {artifact.artifact_id!r}")
