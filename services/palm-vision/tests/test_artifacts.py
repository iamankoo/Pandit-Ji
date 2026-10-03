from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pandit_palm_vision.artifacts import (
    REQUIRED_PREPROCESSING,
    ArtifactPolicyError,
    ModelArtifact,
    file_sha256,
    verify_file,
)


def _artifact(**overrides: Any) -> ModelArtifact:
    fields: dict[str, Any] = {
        "artifact_id": "LINE_MODEL_X",
        "version": "1",
        "role": "palm_line_segmentation",
        "sha256": "a" * 64,
        "source": "internal training run TR-1 (fixture description)",
        "licence_id": "INTERNAL-OWNED",
        "licence_verified": True,
        "provenance_note": "trained on the governed dataset manifest M-1",
        "preprocessing_compat": (REQUIRED_PREPROCESSING,),
        "runtime_compat": ("python>=3.10",),
    }
    fields.update(overrides)
    return ModelArtifact(**fields)


def test_a_complete_artifact_is_usable_but_not_validated() -> None:
    artifact = _artifact()
    assert artifact.usable and not artifact.validated
    artifact.require_production_usable()


@pytest.mark.parametrize(
    ("field", "value", "problem"),
    [
        ("sha256", None, "SHA256_MISSING_OR_INVALID"),
        ("sha256", "xyz", "SHA256_MISSING_OR_INVALID"),
        ("source", None, "SOURCE_MISSING"),
        ("licence_id", None, "LICENCE_MISSING"),
        ("licence_verified", False, "LICENCE_NOT_VERIFIED"),
        ("provenance_note", None, "PROVENANCE_MISSING"),
        ("preprocessing_compat", (), "PREPROCESSING_INCOMPATIBLE"),
        ("runtime_compat", (), "RUNTIME_COMPATIBILITY_UNDECLARED"),
    ],
)
def test_an_artifact_missing_anything_is_rejected(field: str, value: object, problem: str) -> None:
    artifact = _artifact(**{field: value})
    assert problem in artifact.problems()
    with pytest.raises(ArtifactPolicyError):
        artifact.require_production_usable()


def test_validated_needs_a_report_hash() -> None:
    assert not _artifact(validation_report_sha256="nothex").validated
    assert _artifact(validation_report_sha256="b" * 64).validated


def test_the_reference_hides_an_unverified_licence() -> None:
    assert _artifact(licence_verified=False).ref().licence_id is None
    assert _artifact().ref().licence_id == "INTERNAL-OWNED"


def test_the_file_must_match_the_recorded_hash(tmp_path: Path) -> None:
    weights = tmp_path / "tiny.bin"
    weights.write_bytes(b"deterministic fixture bytes, not a model")
    good = _artifact(sha256=file_sha256(weights))
    verify_file(good, weights)
    with pytest.raises(ArtifactPolicyError):
        verify_file(_artifact(sha256="c" * 64), weights)
    with pytest.raises(ArtifactPolicyError):
        verify_file(good, tmp_path / "missing.bin")
