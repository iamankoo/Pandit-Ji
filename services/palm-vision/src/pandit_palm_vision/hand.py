"""Hand detection and landmark acquisition: an interface, not a model (Phase 13).

A :class:`HandDetector` finds hands and returns 21 landmarks per hand in normalized image
coordinates (x to the right, y downward, both in [0, 1] of the image width and height) with
the detector's own handedness label and scores. It is replaceable and versioned; its identity
is part of every fact's provenance.

**Landmarks are not palmistry.** The 21-point layout locates the wrist, the thumb and the four
finger joints; it detects no palm lines, mounts or palmistry features (`TECH_STACK.md`: a
dedicated model is required for those).

Adapters:

* :class:`StaticHandDetector`: returns candidates supplied by the caller. Used for synthetic
  fixtures and tests; it makes no claim of real detection.
* :class:`MediaPipeHandDetector`: wraps the MediaPipe Hand Landmarker when the optional
  ``mediapipe`` package and a **verified** local model asset are available. No model is bundled
  and none is downloaded.

Mirroring: a detector's handedness label depends on whether it assumes a mirrored (selfie)
image. ``assumes_mirrored_input`` states that assumption explicitly; when it is unknown the
side is not determined (:mod:`pandit_palm_vision.side`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

import cv2
from pandit_contracts.palm import ModelArtifactRef
from pandit_contracts.palm_canonical import BASIS_POINTS, to_basis_points

from pandit_palm_vision.artifacts import ArtifactPolicyError, ModelArtifact, verify_file
from pandit_palm_vision.image_input import ImageInput

LANDMARK_COUNT = 21
# Indices of the 21-point hand layout used by the pipeline (documented, to be re-verified
# against the detector's documentation when an adapter is enabled).
WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
INDEX_MCP = 5
MIDDLE_MCP = 9
RING_MCP = 13
PINKY_MCP = 17


class DetectorUnavailableError(RuntimeError):
    """The detector's optional dependency or verified model asset is not available."""


@dataclass(frozen=True)
class HandCandidate:
    """One detected hand: 21 normalized landmarks and the detector's own scores."""

    landmarks: tuple[tuple[float, float], ...]
    handedness_label: Literal["Left", "Right"]
    handedness_score_bp: int
    presence_bp: int

    def __post_init__(self) -> None:
        if len(self.landmarks) != LANDMARK_COUNT:
            raise ValueError(f"a hand has {LANDMARK_COUNT} landmarks")
        for score in (self.handedness_score_bp, self.presence_bp):
            if not 0 <= score <= BASIS_POINTS:
                raise ValueError("scores are integer basis points")


@dataclass(frozen=True)
class DetectionResult:
    candidates: tuple[HandCandidate, ...]
    detector_id: str
    detector_version: str
    # What the detector assumes about the image's mirroring when it names a hand: True when it
    # assumes a mirrored (selfie) image, False when it assumes an unmirrored one, None unknown.
    assumes_mirrored_input: bool | None
    models: tuple[ModelArtifactRef, ...] = ()
    notes: tuple[str, ...] = field(default=())


class HandDetector(Protocol):
    def detect(self, image: ImageInput) -> DetectionResult: ...


@dataclass(frozen=True)
class StaticHandDetector:
    """Returns the candidates it was given (fixtures and tests only)."""

    candidates: tuple[HandCandidate, ...]
    assumes_mirrored_input: bool | None = False
    detector_id: str = "STATIC_FIXTURE_DETECTOR"
    detector_version: str = "1"

    def detect(self, image: ImageInput) -> DetectionResult:
        return DetectionResult(
            candidates=self.candidates,
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            assumes_mirrored_input=self.assumes_mirrored_input,
        )


@dataclass(frozen=True)
class MappingHandDetector:
    """Returns the candidates registered for an image id (fixtures and tests only)."""

    candidates_by_image: dict[str, tuple[HandCandidate, ...]]
    assumes_mirrored_input: bool | None = False
    detector_id: str = "MAPPING_FIXTURE_DETECTOR"
    detector_version: str = "1"

    def detect(self, image: ImageInput) -> DetectionResult:
        return DetectionResult(
            candidates=self.candidates_by_image.get(image.image_id, ()),
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            assumes_mirrored_input=self.assumes_mirrored_input,
        )


class MediaPipeHandDetector:
    """MediaPipe Hand Landmarker adapter (optional; needs a verified local model asset).

    The asset must be described by a :class:`ModelArtifact` whose SHA-256, source and licence
    are recorded and whose file matches the hash; otherwise construction fails. The adapter is
    not exercised by normal CI (no model asset and no ``mediapipe`` package there): tests use a
    fake module to cover its logic.
    """

    detector_id = "MEDIAPIPE_HAND_LANDMARKER"

    def __init__(
        self,
        artifact: ModelArtifact,
        asset_path: Path,
        *,
        assumes_mirrored_input: bool | None,
        max_hands: int = 2,
    ) -> None:
        artifact.require_production_usable()
        verify_file(artifact, asset_path)
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise DetectorUnavailableError(
                "the optional 'mediapipe' package is not installed"
            ) from exc
        self._mp: Any = mp
        self._artifact = artifact
        self._assumes_mirrored = assumes_mirrored_input
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(asset_path)),
            num_hands=max_hands,
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
        )
        self._landmarker: Any = mp.tasks.vision.HandLandmarker.create_from_options(options)

    def detect(self, image: ImageInput) -> DetectionResult:
        rgb = cv2.cvtColor(image.pixels, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(mp_image)
        candidates: list[HandCandidate] = []
        for points, categories in zip(result.hand_landmarks, result.handedness, strict=True):
            top = categories[0]
            label: Literal["Left", "Right"] = (
                "Left" if str(top.category_name).lower() == "left" else "Right"
            )
            candidates.append(
                HandCandidate(
                    landmarks=tuple((float(p.x), float(p.y)) for p in points),
                    handedness_label=label,
                    handedness_score_bp=to_basis_points(float(top.score)),
                    presence_bp=to_basis_points(float(top.score)),
                )
            )
        return DetectionResult(
            candidates=tuple(candidates),
            detector_id=self.detector_id,
            detector_version=self._artifact.version,
            assumes_mirrored_input=self._assumes_mirrored,
            models=(self._artifact.ref(),),
        )


def best_candidate(candidates: Sequence[HandCandidate]) -> HandCandidate | None:
    """The highest-presence candidate (ties: the first), or ``None`` when no hand was found."""
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.presence_bp)


__all__ = [
    "ArtifactPolicyError",
    "DetectionResult",
    "DetectorUnavailableError",
    "HandCandidate",
    "HandDetector",
    "MappingHandDetector",
    "MediaPipeHandDetector",
    "StaticHandDetector",
    "best_candidate",
]
