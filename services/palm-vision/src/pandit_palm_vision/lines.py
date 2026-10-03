"""Palm-line / feature analysis: the interface and honest implementations (Phase 13).

**MediaPipe provides no palm lines.** A dedicated model is required (`TECH_STACK.md`), and **no
trained, validated palm-line model exists yet**. This module therefore provides:

* the :class:`LineAnalyzer` interface the pipeline calls;
* :class:`ModelUnavailableLineAnalyzer`: the production default today. It returns the explicit
  status ``MODEL_UNAVAILABLE`` and no track, so every line fact becomes ``NOT_EVALUABLE``;
* :class:`BaselineRidgeLineAnalyzer`: a classical OpenCV/NumPy ridge-enhancement baseline,
  **BASELINE / EXPERIMENTAL**. It is a research tool: it makes no claim to find palmistry lines,
  its threshold is ``CALIBRATION_REQUIRED`` (it returns no track until one is supplied), and it
  never becomes a production interpretation model on its own;
* :class:`FixtureLineAnalyzer`: returns supplied tracks (synthetic fixtures and tests);
* :class:`ArtifactBackedLineAnalyzer`: the slot for a learned model, usable only with an
  artifact that satisfies the artifact policy and a backend callable. Its status is
  ``MODEL_UNVALIDATED`` until a validation report is recorded for the artifact and
  ``TRAINED_MODEL`` after. No backend and no weights exist in this repository (MODEL_REQUIRED).

Line tracks are **unlabelled**: no palmistry name is attached here (role assignment needs a
validated rule set; see :mod:`pandit_palm_vision.pipeline`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np
from pandit_contracts.palm import LineAnalysisStatus, ModelArtifactRef
from pandit_contracts.palm_canonical import BASIS_POINTS, to_basis_points

from pandit_palm_vision.artifacts import ModelArtifact
from pandit_palm_vision.frame import FloatArray, PalmFrame, roi_geometry
from pandit_palm_vision.hand import HandCandidate
from pandit_palm_vision.image_input import ImageInput

ROI_SIZE = 256


@dataclass(frozen=True)
class LineTrackResult:
    """One unlabelled line track in PCF-1 (float, quantized later) with a score."""

    points_pcf: tuple[tuple[float, float], ...]
    score_bp: int

    def __post_init__(self) -> None:
        if len(self.points_pcf) < 2:
            raise ValueError("a track has at least two points")
        if not 0 <= self.score_bp <= BASIS_POINTS:
            raise ValueError("score is integer basis points")


@dataclass(frozen=True)
class LineAnalysisResult:
    status: LineAnalysisStatus
    tracks: tuple[LineTrackResult, ...] = ()
    reasons: tuple[str, ...] = ()
    models: tuple[ModelArtifactRef, ...] = ()
    analyzer_id: str = "UNSPECIFIED"
    analyzer_version: str = "1"


class LineAnalyzer(Protocol):
    analyzer_id: str
    declared_status: LineAnalysisStatus  # the status this analyzer reports (known before it runs)

    def identity(self) -> dict[str, object]:
        """Canonical (integer, string, list) identity: parameters that shape the output."""
        ...

    def models(self) -> tuple[ModelArtifactRef, ...]: ...

    def analyze(
        self, image: ImageInput, frame: PalmFrame, hand: HandCandidate
    ) -> LineAnalysisResult: ...


class ModelUnavailableLineAnalyzer:
    """No palm-line model is available: report that, produce nothing."""

    analyzer_id = "MODEL_UNAVAILABLE"
    declared_status = LineAnalysisStatus.MODEL_UNAVAILABLE

    def identity(self) -> dict[str, object]:
        return {"analyzer": self.analyzer_id}

    def models(self) -> tuple[ModelArtifactRef, ...]:
        return ()

    def analyze(
        self, image: ImageInput, frame: PalmFrame, hand: HandCandidate
    ) -> LineAnalysisResult:
        return LineAnalysisResult(
            status=LineAnalysisStatus.MODEL_UNAVAILABLE,
            reasons=("PALM_LINE_MODEL_UNAVAILABLE",),
            analyzer_id=self.analyzer_id,
        )


class FixtureLineAnalyzer:
    """Returns the tracks it was given. Synthetic fixtures and tests only."""

    analyzer_id = "FIXTURE_SYNTHETIC_LINES"
    declared_status = LineAnalysisStatus.FIXTURE_SYNTHETIC

    def __init__(self, tracks: Sequence[LineTrackResult]) -> None:
        self._tracks = tuple(tracks)

    def identity(self) -> dict[str, object]:
        return {"analyzer": self.analyzer_id, "tracks": len(self._tracks)}

    def models(self) -> tuple[ModelArtifactRef, ...]:
        return ()

    def analyze(
        self, image: ImageInput, frame: PalmFrame, hand: HandCandidate
    ) -> LineAnalysisResult:
        return LineAnalysisResult(
            status=LineAnalysisStatus.FIXTURE_SYNTHETIC,
            tracks=self._tracks,
            reasons=("FIXTURE_NOT_A_DETECTION",),
            analyzer_id=self.analyzer_id,
        )


@dataclass(frozen=True)
class BaselineRidgeParams:
    """Integer parameters (scaled) so they hash canonically; ``None`` threshold = uncalibrated."""

    sigmas_x100: tuple[int, ...] = (150, 250)
    ridge_threshold_x100: int | None = None  # CALIBRATION_REQUIRED
    min_component_pixels: int = 40
    track_samples: int = 24

    def identity(self) -> dict[str, object]:
        return {
            "sigmas_x100": list(self.sigmas_x100),
            "ridge_threshold_x100": self.ridge_threshold_x100,
            "min_component_pixels": self.min_component_pixels,
            "track_samples": self.track_samples,
        }


class BaselineRidgeLineAnalyzer:
    """BASELINE / EXPERIMENTAL multi-scale ridge enhancement on the canonical palm ROI.

    Dark ridges on a lighter ground are enhanced with Hessian eigenvalues at a few scales,
    thresholded, grouped into connected components and reduced to one ordered centre track per
    component. Without a threshold it reports no track. Not validated; not a palmistry model.
    """

    analyzer_id = "BASELINE_RIDGE_EXPERIMENTAL"
    declared_status = LineAnalysisStatus.BASELINE_EXPERIMENTAL

    def __init__(self, params: BaselineRidgeParams | None = None) -> None:
        self.params = params or BaselineRidgeParams()

    def identity(self) -> dict[str, object]:
        return {"analyzer": self.analyzer_id, "params": self.params.identity()}

    def models(self) -> tuple[ModelArtifactRef, ...]:
        return ()

    def ridge_strength(self, gray: FloatArray) -> FloatArray:
        best = np.zeros_like(gray)
        for sigma_x100 in self.params.sigmas_x100:
            sigma = sigma_x100 / 100.0
            blurred = cv2.GaussianBlur(gray, (0, 0), sigma)
            dxx = cv2.Sobel(blurred, cv2.CV_64F, 2, 0, ksize=3)
            dyy = cv2.Sobel(blurred, cv2.CV_64F, 0, 2, ksize=3)
            dxy = cv2.Sobel(blurred, cv2.CV_64F, 1, 1, ksize=3)
            tmp = np.sqrt(((dxx - dyy) * 0.5) ** 2 + dxy**2)
            lam_max = (dxx + dyy) * 0.5 + tmp  # a dark line has a large positive eigenvalue
            best = np.maximum(best, sigma**2 * np.maximum(lam_max, 0.0))
        return best

    def analyze(
        self, image: ImageInput, frame: PalmFrame, hand: HandCandidate
    ) -> LineAnalysisResult:
        status = LineAnalysisStatus.BASELINE_EXPERIMENTAL
        threshold = self.params.ridge_threshold_x100
        if threshold is None:
            return LineAnalysisResult(
                status,
                reasons=("RIDGE_THRESHOLD_CALIBRATION_REQUIRED",),
                analyzer_id=self.analyzer_id,
            )
        matrix = frame.affine_to_roi(ROI_SIZE)
        gray = cv2.cvtColor(image.pixels, cv2.COLOR_BGR2GRAY)
        roi = cv2.warpAffine(gray, matrix, (ROI_SIZE, ROI_SIZE), flags=cv2.INTER_LINEAR)
        strength = self.ridge_strength(roi.astype(np.float64))
        binary = (strength * 100.0 >= threshold).astype(np.uint8)
        count, labels = cv2.connectedComponents(binary, connectivity=8)
        tracks: list[LineTrackResult] = []
        for label in range(1, count):
            ys, xs = np.nonzero(labels == label)
            if xs.size < self.params.min_component_pixels:
                continue
            track_roi = _centre_track(
                xs.astype(np.float64), ys.astype(np.float64), self.params.track_samples
            )
            if track_roi is None:
                continue
            pcf = frame.roi_to_pcf(track_roi, ROI_SIZE)
            score = float(strength[ys, xs].mean() * 100.0 / max(threshold, 1))
            tracks.append(
                LineTrackResult(
                    points_pcf=tuple((float(x), float(y)) for x, y in pcf),
                    score_bp=to_basis_points(min(1.0, score / 4.0)),
                )
            )
        tracks.sort(key=lambda t: (-t.score_bp, t.points_pcf[0]))
        return LineAnalysisResult(
            status, tuple(tracks), ("BASELINE_NOT_VALIDATED",), analyzer_id=self.analyzer_id
        )


def _centre_track(xs: FloatArray, ys: FloatArray, samples: int) -> FloatArray | None:
    """An ordered centre line of a pixel set: bin along the principal axis, average the rest."""
    points = np.stack([xs, ys], axis=1)
    centre = points.mean(axis=0)
    centred = points - centre
    cov = centred.T @ centred
    values, vectors = np.linalg.eigh(cov)
    axis = vectors[:, int(np.argmax(values))]
    t = centred @ axis
    span = float(np.max(t) - np.min(t))
    if span < 3.0:
        return None
    edges = np.linspace(float(np.min(t)), float(np.max(t)), samples + 1)
    out: list[FloatArray] = []
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        sel = (t >= lo) & (t <= hi)
        if sel.any():
            out.append(points[sel].mean(axis=0))
    if len(out) < 2:
        return None
    return np.asarray(out)


class LineModelBackend(Protocol):
    """A learned model's inference: ROI pixel polylines with scores. No implementation ships."""

    def predict(
        self, roi_gray: np.ndarray
    ) -> Sequence[tuple[Sequence[tuple[float, float]], float]]: ...


class ArtifactBackedLineAnalyzer:
    """A learned palm-line model behind the artifact policy (MODEL_REQUIRED: none exists yet)."""

    def __init__(self, artifact: ModelArtifact, backend: LineModelBackend) -> None:
        artifact.require_production_usable()
        self._artifact = artifact
        self._backend = backend
        self.analyzer_id = f"MODEL:{artifact.artifact_id}"
        self.declared_status = (
            LineAnalysisStatus.TRAINED_MODEL
            if artifact.validated
            else LineAnalysisStatus.MODEL_UNVALIDATED
        )

    def identity(self) -> dict[str, object]:
        return {"analyzer": self.analyzer_id, "artifact_sha256": self._artifact.sha256}

    def models(self) -> tuple[ModelArtifactRef, ...]:
        return (self._artifact.ref(),)

    def analyze(
        self, image: ImageInput, frame: PalmFrame, hand: HandCandidate
    ) -> LineAnalysisResult:
        matrix = frame.affine_to_roi(ROI_SIZE)
        gray = cv2.cvtColor(image.pixels, cv2.COLOR_BGR2GRAY)
        roi = cv2.warpAffine(gray, matrix, (ROI_SIZE, ROI_SIZE), flags=cv2.INTER_LINEAR)
        tracks: list[LineTrackResult] = []
        for polyline, score in self._backend.predict(roi):
            pts = np.asarray(polyline, dtype=np.float64)
            if pts.shape[0] < 2:
                continue
            pcf = frame.roi_to_pcf(pts, ROI_SIZE)
            tracks.append(
                LineTrackResult(
                    points_pcf=tuple((float(x), float(y)) for x, y in pcf),
                    score_bp=to_basis_points(score),
                )
            )
        status = (
            LineAnalysisStatus.TRAINED_MODEL
            if self._artifact.validated
            else LineAnalysisStatus.MODEL_UNVALIDATED
        )
        reasons = () if self._artifact.validated else ("MODEL_VALIDATION_REPORT_MISSING",)
        return LineAnalysisResult(
            status,
            tuple(tracks),
            reasons,
            models=(self._artifact.ref(),),
            analyzer_id=self.analyzer_id,
        )


# ----------------------------------------------------------------------------- geometry helpers
def polyline_length(points: Sequence[tuple[float, float]]) -> float:
    pts = np.asarray(points, dtype=np.float64)
    return float(np.hypot(*np.diff(pts, axis=0).T).sum())


def polyline_intersection(
    a: Sequence[tuple[float, float]], b: Sequence[tuple[float, float]]
) -> tuple[float, float] | None:
    """The first crossing point of two polylines (segment pairs in order), or ``None``."""
    pa, pb = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    for i in range(len(pa) - 1):
        for j in range(len(pb) - 1):
            p, r = pa[i], pa[i + 1] - pa[i]
            q, s = pb[j], pb[j + 1] - pb[j]
            denom = r[0] * s[1] - r[1] * s[0]
            if abs(denom) < 1e-12:
                continue
            qp = q - p
            t = (qp[0] * s[1] - qp[1] * s[0]) / denom
            u = (qp[0] * r[1] - qp[1] * r[0]) / denom
            if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
                point = p + t * r
                return (float(point[0]), float(point[1]))
    return None


__all__ = [
    "ROI_SIZE",
    "ArtifactBackedLineAnalyzer",
    "BaselineRidgeLineAnalyzer",
    "BaselineRidgeParams",
    "FixtureLineAnalyzer",
    "LineAnalysisResult",
    "LineAnalyzer",
    "LineModelBackend",
    "LineTrackResult",
    "ModelUnavailableLineAnalyzer",
    "polyline_intersection",
    "polyline_length",
    "roi_geometry",
]
