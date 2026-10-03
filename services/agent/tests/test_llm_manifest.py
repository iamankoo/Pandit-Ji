from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from llm_helpers import (
    MOCK_MANIFEST,
    QWEN_MANIFEST,
    manifest_dict,
    mock_manifest,
    qwen_manifest,
    write_manifest,
)
from pandit_contracts.llm import LLMErrorCode

from pandit_agent.llm.errors import LLMFailure
from pandit_agent.llm.manifest import (
    ModelManifest,
    load_manifest,
    normalized_sha256,
    verify_model_directory,
)


def _rejected(tmp_path: Path, data: dict[str, Any]) -> LLMFailure:
    with pytest.raises(LLMFailure) as caught:
        load_manifest(write_manifest(tmp_path, data))
    assert caught.value.code is LLMErrorCode.INVALID_MANIFEST
    return caught.value


def test_the_selected_model_manifest_is_valid_and_pinned() -> None:
    m = qwen_manifest()
    assert m.model_id == "Qwen/Qwen3-8B"
    assert len(m.model_revision) == 40
    assert m.license.spdx == "Apache-2.0"
    assert m.license.verification == "LICENSE_FILE_READ"
    assert m.runtime.name == "vllm"
    assert m.provenance.weights_committed_to_git is False
    assert m.test_fixture is False


def test_every_artifact_has_a_sha256_and_the_sizes_sum_to_the_weights() -> None:
    m = qwen_manifest()
    assert len(m.artifacts) == 12
    assert all(len(a.sha256) == 64 for a in m.artifacts)
    weights = sum(a.size_bytes for a in m.artifacts if a.filename.endswith(".safetensors"))
    assert weights == m.hardware.weights_size_bytes == 16_381_516_776


def test_the_selected_model_is_honestly_not_production_eligible() -> None:
    m = qwen_manifest()
    assert m.production_eligible is False
    blockers = " ".join(m.production_blockers)
    for gate in ("MODEL_DOWNLOAD_REQUIRED", "HARDWARE_REQUIRED", "CALIBRATION_REQUIRED"):
        assert gate in blockers
    assert m.license.legal_status == "LEGAL_REVIEW_REQUIRED"
    assert m.languages.quality_status == "UNEVALUATED"
    assert m.runtime.runtime_tested_against_real_model is False


def test_both_context_figures_are_recorded_without_picking_one_silently() -> None:
    ctx = qwen_manifest().context
    assert ctx.native_tokens_model_card == 32768
    assert ctx.max_position_embeddings_config_json == 40960
    assert ctx.extended_enabled is False
    assert ctx.operational_limit_tokens == 32768


def test_the_test_fixture_manifest_is_marked_and_never_production() -> None:
    m = mock_manifest()
    assert m.test_fixture is True
    assert m.production_eligible is False
    assert m.artifacts == ()
    assert "not a language model" in " ".join(m.production_blockers)


def test_the_manifest_files_are_loadable_by_name() -> None:
    assert load_manifest(Path(__file__).resolve().parents[1] / "llm" / "manifests" / MOCK_MANIFEST)
    assert load_manifest(Path(__file__).resolve().parents[1] / "llm" / "manifests" / QWEN_MANIFEST)


def test_a_missing_artifact_hash_is_rejected(tmp_path: Path) -> None:
    data = manifest_dict()
    data["artifacts"][0]["sha256"] = ""
    assert "SHA-256" in _rejected(tmp_path, data).message


def test_a_malformed_artifact_hash_is_rejected(tmp_path: Path) -> None:
    data = manifest_dict()
    data["artifacts"][0]["sha256"] = "G" * 64
    _rejected(tmp_path, data)


def test_an_unsupported_runtime_is_rejected(tmp_path: Path) -> None:
    data = manifest_dict()
    data["runtime"]["name"] = "some-other-engine"
    assert "unsupported runtime" in _rejected(tmp_path, data).message


def test_an_unpinned_revision_is_rejected(tmp_path: Path) -> None:
    data = manifest_dict()
    data["model_revision"] = "main"
    assert "40-hex" in _rejected(tmp_path, data).message


def test_a_real_model_without_artifacts_is_rejected(tmp_path: Path) -> None:
    data = manifest_dict()
    data["artifacts"] = []
    _rejected(tmp_path, data)


def test_an_unverified_licence_is_rejected(tmp_path: Path) -> None:
    data = manifest_dict()
    data["license"]["verification"] = "UNVERIFIED"
    assert "licence" in _rejected(tmp_path, data).message


def test_a_missing_licence_hash_is_rejected(tmp_path: Path) -> None:
    data = manifest_dict()
    data["license"]["license_file_sha256"] = ""
    _rejected(tmp_path, data)


def test_committed_weights_are_rejected(tmp_path: Path) -> None:
    data = manifest_dict()
    data["provenance"]["weights_committed_to_git"] = True
    assert "never be committed" in _rejected(tmp_path, data).message


def test_production_eligible_with_blockers_is_rejected(tmp_path: Path) -> None:
    data = manifest_dict()
    data["production_eligible"] = True
    _rejected(tmp_path, data)


def test_a_test_fixture_cannot_claim_production(tmp_path: Path) -> None:
    data = manifest_dict(MOCK_MANIFEST)
    data["production_eligible"] = True
    data["production_blockers"] = []
    assert "test fixture" in _rejected(tmp_path, data).message


def test_an_operational_limit_beyond_the_native_context_is_rejected(tmp_path: Path) -> None:
    data = manifest_dict()
    data["context"]["operational_limit_tokens"] = 100000
    _rejected(tmp_path, data)


def test_an_unknown_field_is_rejected(tmp_path: Path) -> None:
    data = manifest_dict()
    data["surprise"] = 1
    _rejected(tmp_path, data)


def test_an_unreadable_or_non_json_manifest_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(LLMFailure) as missing:
        load_manifest(tmp_path / "nope.json")
    assert missing.value.code is LLMErrorCode.INVALID_MANIFEST
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(LLMFailure) as broken:
        load_manifest(bad)
    assert broken.value.code is LLMErrorCode.INVALID_MANIFEST


def test_the_normalized_hash_ignores_line_ending_style() -> None:
    assert normalized_sha256("a\r\nb\r\n") == normalized_sha256("a\nb\n")
    assert normalized_sha256("a\nb\n") == hashlib.sha256(b"a\nb\n").hexdigest()


def _manifest_for_files(tmp_path: Path) -> tuple[ModelManifest, Path]:
    model_dir = tmp_path / "weights"
    model_dir.mkdir()
    artifacts = []
    for name, payload in (("w1.safetensors", b"alpha"), ("config.json", b"{}")):
        (model_dir / name).write_bytes(payload)
        artifacts.append(
            {
                "filename": name,
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    data = manifest_dict()
    data["artifacts"] = artifacts
    return load_manifest(write_manifest(tmp_path, data)), model_dir


def test_a_model_directory_matching_the_manifest_verifies(tmp_path: Path) -> None:
    manifest, model_dir = _manifest_for_files(tmp_path)
    assert verify_model_directory(manifest, model_dir) == 2


def test_a_tampered_artifact_fails_verification(tmp_path: Path) -> None:
    manifest, model_dir = _manifest_for_files(tmp_path)
    (model_dir / "w1.safetensors").write_bytes(b"omega")
    with pytest.raises(LLMFailure) as caught:
        verify_model_directory(manifest, model_dir)
    assert caught.value.code is LLMErrorCode.MODEL_LOAD_FAILURE
    assert "SHA-256" in caught.value.message


def test_a_wrong_size_artifact_fails_verification(tmp_path: Path) -> None:
    manifest, model_dir = _manifest_for_files(tmp_path)
    (model_dir / "w1.safetensors").write_bytes(b"alphabet")
    with pytest.raises(LLMFailure) as caught:
        verify_model_directory(manifest, model_dir)
    assert "size" in caught.value.message


def test_a_missing_artifact_or_directory_is_model_unavailable(tmp_path: Path) -> None:
    manifest, model_dir = _manifest_for_files(tmp_path)
    (model_dir / "config.json").unlink()
    with pytest.raises(LLMFailure) as caught:
        verify_model_directory(manifest, model_dir)
    assert caught.value.code is LLMErrorCode.MODEL_UNAVAILABLE
    with pytest.raises(LLMFailure) as no_dir:
        verify_model_directory(manifest, tmp_path / "absent")
    assert no_dir.value.code is LLMErrorCode.MODEL_UNAVAILABLE
