"""The palm-canonical frame PCF-1, palm region, mount regions and landmark conversion.

Standards PM-14 and `research/PALM_READING.md` section 8:

* origin: the wrist landmark; unit: the pixel distance from the wrist landmark to the
  middle-finger base landmark (the "palm unit"); the +y axis points from the wrist to the middle
  finger base; coordinates are quantized once to integers at 10^-4 of the palm unit
  (round-half-even);
* a **left** hand is mirrored on the x axis so left and right hands are comparable, and an input
  that is a mirrored capture (a selfie preview) is un-mirrored; the combined flip is recorded
  explicitly (``mirrored_for_canonical``), never silent;
* the transform is deterministic: float64 arithmetic, one rounding at the output.

The mount regions are **project-derived geometry** (`PROJECT_DERIVED`, standards PM-07): the
books draw the mounts only on maps, so their boundaries here are an engineering definition,
versioned (``MOUNT_REGION_DEFINITION_ID``) and unvalidated. They are positions, not a claim
about mount development (a volume property that one 2D image cannot show).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from pandit_contracts.palm import HandSide
from pandit_contracts.palm_canonical import PCF_SCALE, to_fixed

from pandit_palm_vision.hand import (
    INDEX_MCP,
    LANDMARK_COUNT,
    MIDDLE_MCP,
    PINKY_MCP,
    RING_MCP,
    THUMB_CMC,
    THUMB_MCP,
    WRIST,
    HandCandidate,
)

PCF_ID = "PCF-1"
PALM_REGION_DEFINITION_ID = "PALM_REGION_LANDMARK_POLYGON_V1"
MOUNT_REGION_DEFINITION_ID = "MOUNT_REGION_PROJECT_DERIVED_V1"

# Polygon of the palm: wrist, thumb base (CMC), then the four finger bases and back.
PALM_POLYGON_LANDMARKS = (WRIST, THUMB_CMC, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP)

# Mount regions anchored under the finger bases. Offsets are in palm units (PCF-1).
_MOUNT_DEPTH_OFFSET = 0.18  # the region centre lies this far from the finger base toward the wrist
_MOUNT_HALF_HEIGHT = 0.15
_MOUNT_WIDTH_FACTOR = 0.9  # of the spacing between neighbouring finger bases
MOUNT_ANCHORS: dict[str, int] = {
    "MOUNT.JUPITER": INDEX_MCP,
    "MOUNT.SATURN": MIDDLE_MCP,
    "MOUNT.APOLLO_SUN": RING_MCP,
    "MOUNT.MERCURY": PINKY_MCP,
}
# Mounts whose region is not produced: the sources disagree (Mars) or no definition exists yet.
MOUNTS_NOT_EVALUABLE: dict[str, str] = {
    "MOUNT.MARS": "SOURCE_CONFLICT_MARS_REGION",
    "MOUNT.MOON": "REGION_DEFINITION_NOT_IMPLEMENTED",
}

FloatArray = npt.NDArray[np.float64]

ROI_MARGIN = 0.25


def roi_geometry(roi_size: int, margin: float = ROI_MARGIN) -> tuple[float, float, float]:
    """(scale, x_min, y_max) of the square palm ROI in PCF-1.

    The ROI covers x in [-0.75 - margin, 0.75 + margin] and y in [-margin, 1.2 + margin] of the
    palm unit, scaled uniformly to ``roi_size`` pixels.
    """
    x_min, x_max = -0.75 - margin, 0.75 + margin
    y_min, y_max = -margin, 1.2 + margin
    return roi_size / max(x_max - x_min, y_max - y_min), x_min, y_max


class DegenerateHandError(ValueError):
    """The wrist and the middle-finger base coincide: no frame can be defined."""


@dataclass(frozen=True)
class PalmFrame:
    """Similarity transform from image pixels to PCF-1 (and back)."""

    origin_px: tuple[float, float]
    unit_px: float
    axis_y: tuple[float, float]  # unit vector wrist -> middle MCP, in pixel space
    axis_x: tuple[float, float]
    mirrored_for_canonical: bool
    image_width: int
    image_height: int

    def to_pcf(self, points_px: FloatArray) -> FloatArray:
        rel = points_px - np.asarray(self.origin_px, dtype=np.float64)
        x = (rel @ np.asarray(self.axis_x, dtype=np.float64)) / self.unit_px
        y = (rel @ np.asarray(self.axis_y, dtype=np.float64)) / self.unit_px
        if self.mirrored_for_canonical:
            x = -x
        return np.stack([x, y], axis=1)

    def from_pcf(self, points: FloatArray) -> FloatArray:
        x = -points[:, 0] if self.mirrored_for_canonical else points[:, 0]
        y = points[:, 1]
        ax = np.asarray(self.axis_x, dtype=np.float64)
        ay = np.asarray(self.axis_y, dtype=np.float64)
        rel = (x[:, None] * ax + y[:, None] * ay) * self.unit_px
        return rel + np.asarray(self.origin_px, dtype=np.float64)

    def roi_to_pcf(
        self, points_roi: FloatArray, roi_size: int, margin: float = ROI_MARGIN
    ) -> FloatArray:
        """ROI-image pixel coordinates back to PCF-1 (the inverse of ``affine_to_roi``)."""
        scale, x_min, y_max = roi_geometry(roi_size, margin)
        return np.stack(
            [points_roi[:, 0] / scale + x_min, y_max - points_roi[:, 1] / scale], axis=1
        )

    def affine_to_roi(self, roi_size: int, margin: float = ROI_MARGIN) -> FloatArray:
        """2x3 matrix mapping image pixels to an ``roi_size`` square ROI image.

        The transform is deterministic and carries the same mirroring as ``to_pcf``.
        """
        scale, x_min, y_max = roi_geometry(roi_size, margin)
        # pixel -> PCF: p' = A (p - o) / u with the mirroring on x
        sx = -1.0 if self.mirrored_for_canonical else 1.0
        ax, ay = (
            np.asarray(self.axis_x, dtype=np.float64),
            np.asarray(self.axis_y, dtype=np.float64),
        )
        basis = np.stack([sx * ax, ay], axis=0) / self.unit_px  # 2x2: PCF coords from rel px
        # roi_x = (x' - x_min) * scale ; roi_y = (y_max - y') * scale (image y points down)
        flip = np.array([[1.0, 0.0], [0.0, -1.0]])
        linear = scale * (flip @ basis)
        origin = np.asarray(self.origin_px, dtype=np.float64)
        offset = scale * np.array([-x_min, y_max]) - linear @ origin
        return np.concatenate([linear, offset[:, None]], axis=1)


def landmarks_px(candidate: HandCandidate, width: int, height: int) -> FloatArray:
    """Normalized landmarks to pixel coordinates (float64)."""
    pts = np.asarray(candidate.landmarks, dtype=np.float64)
    return np.stack([pts[:, 0] * width, pts[:, 1] * height], axis=1)


def build_frame(
    candidate: HandCandidate,
    side: HandSide,
    width: int,
    height: int,
    input_mirrored: bool = False,
) -> PalmFrame:
    """The PCF-1 frame of a hand. The side must be known: no frame is built for a guess.

    A left hand is mirrored so left and right are comparable, and an input that is itself a
    mirrored capture is un-mirrored: the two flips combine (exclusive or) and are recorded in
    ``mirrored_for_canonical``, never applied silently.
    """
    if side is HandSide.UNDETERMINED:
        raise ValueError("a palm frame needs a determined side (no silent mirroring)")
    px = landmarks_px(candidate, width, height)
    wrist, middle = px[WRIST], px[MIDDLE_MCP]
    vector = middle - wrist
    unit = float(np.hypot(vector[0], vector[1]))
    if unit < 1e-9:
        raise DegenerateHandError("wrist and middle-finger base coincide")
    axis_y = vector / unit
    axis_x = np.array([-axis_y[1], axis_y[0]])
    return PalmFrame(
        origin_px=(float(wrist[0]), float(wrist[1])),
        unit_px=unit,
        axis_y=(float(axis_y[0]), float(axis_y[1])),
        axis_x=(float(axis_x[0]), float(axis_x[1])),
        mirrored_for_canonical=(side is HandSide.LEFT) != input_mirrored,
        image_width=width,
        image_height=height,
    )


def quantize(points: FloatArray) -> tuple[tuple[int, int], ...]:
    """PCF-1 floats to fixed-point integers, rounded once (half-even)."""
    return tuple((to_fixed(float(x)), to_fixed(float(y))) for x, y in points)


def landmark_points_pcf(candidate: HandCandidate, frame: PalmFrame) -> FloatArray:
    px = landmarks_px(candidate, frame.image_width, frame.image_height)
    return frame.to_pcf(px)


def palm_polygon_pcf(landmarks_pcf: FloatArray) -> FloatArray:
    return landmarks_pcf[list(PALM_POLYGON_LANDMARKS)]


def mount_polygon_pcf(name: str, landmarks_pcf: FloatArray) -> FloatArray:
    """A rectangle under a finger base, in PCF-1 (project-derived, unvalidated)."""
    anchor = MOUNT_ANCHORS[name]
    base = landmarks_pcf[anchor]
    neighbours = [i for i in (INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP) if i != anchor]
    spacing = min(abs(float(landmarks_pcf[i][0] - base[0])) for i in neighbours)
    half_width = 0.5 * _MOUNT_WIDTH_FACTOR * spacing
    cx, cy = float(base[0]), float(base[1]) - _MOUNT_DEPTH_OFFSET
    h = _MOUNT_HALF_HEIGHT
    return np.array(
        [[cx - half_width, cy - h], [cx + half_width, cy - h], [cx + half_width, cy + h],
         [cx - half_width, cy + h]],
        dtype=np.float64,
    )  # fmt: skip


def venus_polygon_pcf(landmarks_pcf: FloatArray) -> FloatArray:
    """The thumb-base region: wrist, thumb base, thumb joint and the index finger base."""
    return landmarks_pcf[[WRIST, THUMB_CMC, THUMB_MCP, INDEX_MCP]]


__all__ = [
    "LANDMARK_COUNT",
    "MOUNT_ANCHORS",
    "MOUNT_REGION_DEFINITION_ID",
    "MOUNTS_NOT_EVALUABLE",
    "PALM_REGION_DEFINITION_ID",
    "PCF_ID",
    "PCF_SCALE",
    "ROI_MARGIN",
    "DegenerateHandError",
    "PalmFrame",
    "build_frame",
    "landmark_points_pcf",
    "landmarks_px",
    "mount_polygon_pcf",
    "palm_polygon_pcf",
    "quantize",
    "roi_geometry",
    "venus_polygon_pcf",
]
