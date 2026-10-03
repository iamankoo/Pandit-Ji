"""The optional MediaPipe adapter is covered with a FAKE module: no mediapipe, no model asset."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import pytest
from pandit_contracts.palm import HandSide

from pandit_palm_vision.artifacts import (
    REQUIRED_PREPROCESSING,
    ArtifactPolicyError,
    ModelArtifact,
    file_sha256,
)
from pandit_palm_vision.hand import DetectorUnavailableError, MediaPipeHandDetector
from pandit_palm_vision.synthetic import SyntheticPalm, make_synthetic_palm


def _artifact(path: Path, **overrides: Any) -> ModelArtifact:
    fields: dict[str, Any] = {
        "artifact_id": "HAND_LANDMARKER_FIXTURE",
        "version": "fixture-1",
        "role": "hand_landmarker",
        "sha256": file_sha256(path),
        "source": "unit test fixture (a stand-in file, not a real model)",
        "licence_id": "FIXTURE",
        "licence_verified": True,
        "provenance_note": "fixture",
        "preprocessing_compat": (REQUIRED_PREPROCESSING,),
        "runtime_compat": ("python>=3.10",),
    }
    fields.update(overrides)
    return ModelArtifact(**fields)


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = x, y


def _fake_mediapipe(palm: SyntheticPalm, label: str = "Right") -> types.ModuleType:
    module = types.ModuleType("mediapipe")

    class _Landmarker:
        def detect(self, image: Any) -> Any:
            category = types.SimpleNamespace(category_name=label, score=0.93)
            return types.SimpleNamespace(
                hand_landmarks=[[_Point(x, y) for x, y in palm.landmarks]],
                handedness=[[category]],
            )

    class _HandLandmarker:
        @staticmethod
        def create_from_options(options: Any) -> _Landmarker:
            return _Landmarker()

    vision = types.SimpleNamespace(
        HandLandmarkerOptions=lambda **kw: kw,
        RunningMode=types.SimpleNamespace(IMAGE="IMAGE"),
        HandLandmarker=_HandLandmarker,
    )
    module.tasks = types.SimpleNamespace(  # type: ignore[attr-defined]
        BaseOptions=lambda **kw: kw, vision=vision
    )
    module.Image = lambda **kw: kw  # type: ignore[attr-defined]
    module.ImageFormat = types.SimpleNamespace(SRGB="SRGB")  # type: ignore[attr-defined]
    return module


def test_the_adapter_converts_detector_output_and_records_the_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, right_palm: SyntheticPalm
) -> None:
    asset = tmp_path / "hand.task"
    asset.write_bytes(b"stand-in asset bytes")
    monkeypatch.setitem(sys.modules, "mediapipe", _fake_mediapipe(right_palm))
    detector = MediaPipeHandDetector(_artifact(asset), asset, assumes_mirrored_input=False)
    result = detector.detect(right_palm.image)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.handedness_label == "Right"
    assert candidate.handedness_score_bp == 9300
    assert len(candidate.landmarks) == 21
    assert result.assumes_mirrored_input is False
    assert result.models[0].artifact_id == "HAND_LANDMARKER_FIXTURE"
    assert right_palm.side is HandSide.RIGHT


def test_a_missing_package_is_a_clear_unavailable_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset = tmp_path / "hand.task"
    asset.write_bytes(b"stand-in asset bytes")
    monkeypatch.setitem(sys.modules, "mediapipe", None)  # makes `import mediapipe` fail
    with pytest.raises(DetectorUnavailableError):
        MediaPipeHandDetector(_artifact(asset), asset, assumes_mirrored_input=False)


def test_an_unverified_artifact_or_a_changed_file_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    palm = make_synthetic_palm(HandSide.RIGHT)
    asset = tmp_path / "hand.task"
    asset.write_bytes(b"stand-in asset bytes")
    monkeypatch.setitem(sys.modules, "mediapipe", _fake_mediapipe(palm))
    with pytest.raises(ArtifactPolicyError):
        MediaPipeHandDetector(
            _artifact(asset, licence_verified=False), asset, assumes_mirrored_input=False
        )
    artifact = _artifact(asset)
    asset.write_bytes(b"tampered")
    with pytest.raises(ArtifactPolicyError):
        MediaPipeHandDetector(artifact, asset, assumes_mirrored_input=False)
