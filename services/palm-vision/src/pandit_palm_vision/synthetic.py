"""SYNTHETIC palm fixtures: generated, minimal, non-identifying (Phase 13 test and harness data).

Everything here is drawn by code: a schematic hand with known landmarks and known line tracks.
It is **not** a photograph of a person, **not** a model of real hands and **not** training data.
It exists to exercise the pipeline, the quality gate, the side logic, the coordinate frame, the
evaluation harness and the reproducibility framework with ground truth that is known by
construction. A pipeline that works on these images has proved its plumbing, nothing about the
accuracy of palm-line detection on real hands.

Convention (shared with :mod:`pandit_palm_vision.side`): for a palm facing the camera in an
unmirrored image, a **right** hand has its thumb on the image right.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import cv2
import numpy as np
from pandit_contracts.palm import HandSide
from pandit_contracts.palm_canonical import to_basis_points

from pandit_palm_vision.frame import PalmFrame, build_frame
from pandit_palm_vision.hand import HandCandidate
from pandit_palm_vision.image_input import ImageInput, image_from_array
from pandit_palm_vision.lines import LineTrackResult

# Landmarks of an upright right hand, palm facing the camera, unmirrored (normalized x, y).
_RIGHT_HAND: tuple[tuple[float, float], ...] = (
    (0.50, 0.88),  # 0 wrist
    (0.62, 0.78), (0.70, 0.68), (0.76, 0.60), (0.80, 0.52),  # thumb: CMC, MCP, IP, tip
    (0.60, 0.52), (0.62, 0.40), (0.63, 0.31), (0.64, 0.23),  # index
    (0.50, 0.48), (0.50, 0.35), (0.50, 0.25), (0.50, 0.16),  # middle
    (0.41, 0.51), (0.40, 0.39), (0.39, 0.30), (0.38, 0.22),  # ring
    (0.33, 0.56), (0.31, 0.47), (0.30, 0.40), (0.29, 0.34),  # pinky
)  # fmt: skip

# Schematic line tracks in the palm-canonical frame (PCF-1, palm units), not anatomical claims.
_LINES_PCF: tuple[tuple[tuple[float, float], ...], ...] = (
    ((0.20, 0.55), (0.30, 0.38), (0.34, 0.22), (0.28, 0.08)),
    ((0.15, 0.50), (0.00, 0.47), (-0.20, 0.44), (-0.40, 0.42)),
    ((0.30, 0.78), (0.05, 0.80), (-0.20, 0.76), (-0.42, 0.70)),
)


@dataclass(frozen=True)
class SyntheticPalm:
    image: ImageInput
    landmarks: tuple[tuple[float, float], ...]
    side: HandSide  # the true side of the drawn hand
    mirrored: bool  # whether the image is a mirrored (selfie-style) capture
    lines: tuple[LineTrackResult, ...]  # ground-truth line tracks in PCF-1
    frame: PalmFrame

    def candidate(
        self, assumes_mirrored: bool = False, presence_bp: int = 9800, score_bp: int = 9500
    ) -> HandCandidate:
        """The candidate a correct detector would return, naming the hand as that detector does.

        A detector that assumes the wrong mirroring names the opposite hand, which is exactly
        the situation the side logic must catch (not guess around).
        """
        correct = self.mirrored == assumes_mirrored
        true_label = "Left" if self.side is HandSide.LEFT else "Right"
        other = "Right" if true_label == "Left" else "Left"
        label = true_label if correct else other
        return HandCandidate(
            landmarks=self.landmarks,
            handedness_label=label,  # type: ignore[arg-type]
            handedness_score_bp=score_bp,
            presence_bp=presence_bp,
        )


def _rotate(points: Any, degrees: float, centre: Any) -> Any:
    rad = np.radians(degrees)
    c, s = np.cos(rad), np.sin(rad)
    rot = np.array([[c, -s], [s, c]])
    return (points - centre) @ rot.T + centre


def make_synthetic_palm(
    side: HandSide = HandSide.RIGHT,
    *,
    width: int = 480,
    height: int = 640,
    seed: int = 0,
    rotation_deg: float = 0.0,
    scale: float = 1.0,
    shift: tuple[float, float] = (0.0, 0.0),
    mirrored: bool = False,
    blur_sigma: float = 0.0,
    brightness: int = 0,
    contrast: float = 1.0,
    noise_sigma: float = 0.0,
    background: str = "plain",
    occlude: bool = False,
    draw_lines: bool = True,
    palm_width_factor: float = 1.0,
    image_id: str | None = None,
) -> SyntheticPalm:
    """Draw a schematic hand. ``side`` is the true side; ``mirrored`` flips the whole image."""
    if side is HandSide.UNDETERMINED:
        raise ValueError("a synthetic hand has a side")
    pts = np.asarray(_RIGHT_HAND, dtype=np.float64).copy()
    centre = np.array([0.5, 0.55])
    pts[:, 0] = centre[0] + (pts[:, 0] - centre[0]) * palm_width_factor
    pts = centre + (pts - centre) * scale + np.asarray(shift)
    # rotate in PIXEL space: normalized coordinates are anisotropic, so rotating them directly
    # would shear the hand
    size = np.array([float(width), float(height)])
    pts = _rotate(pts * size, rotation_deg, (centre + np.asarray(shift)) * size) / size
    if side is HandSide.LEFT:
        pts[:, 0] = 1.0 - pts[:, 0]
    # ``pts`` is the hand as an unmirrored capture shows it; a mirrored capture flips it at the end.
    final = pts.copy()
    if mirrored:
        final[:, 0] = 1.0 - final[:, 0]
    landmarks = tuple((float(x), float(y)) for x, y in final)

    rng = np.random.default_rng(seed)
    if background == "noisy":
        noise_bg = rng.integers(60, 200, size=(height, width, 3), dtype=np.int64).astype(np.uint8)
        canvas = cv2.GaussianBlur(noise_bg, (0, 0), 3.0)
    else:
        canvas = np.full((height, width, 3), (205, 205, 200), dtype=np.uint8)

    skin = (140, 165, 215)
    px = np.stack([pts[:, 0] * width, pts[:, 1] * height], axis=1)
    palm_idx = [0, 1, 5, 9, 13, 17]
    cv2.fillPoly(canvas, [np.round(px[palm_idx]).astype(np.int32)], skin)
    thickness = max(6, int(0.045 * width * scale))
    for finger in ((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20)):
        for a, b in zip(finger[:-1], finger[1:], strict=True):
            cv2.line(
                canvas,
                tuple(int(v) for v in np.round(px[a])),
                tuple(int(v) for v in np.round(px[b])),
                skin,
                thickness,
                cv2.LINE_8,
            )
    for idx in range(21):
        cv2.circle(canvas, tuple(int(v) for v in np.round(px[idx])), thickness // 2, skin, -1)

    # Ground-truth lines are defined in PCF-1 of the drawn hand and mapped to pixels through the
    # frame of the unmirrored drawing, so the truth is exact by construction. The same PCF-1
    # coordinates result from the mirrored image when the pipeline is told it is mirrored.
    label: Literal["Left", "Right"] = "Right" if side is HandSide.RIGHT else "Left"
    drawn = tuple((float(x), float(y)) for x, y in pts)
    frame_drawn = build_frame(HandCandidate(drawn, label, 9500, 9800), side, width, height, False)
    frame = build_frame(HandCandidate(landmarks, label, 9500, 9800), side, width, height, mirrored)
    lines: list[LineTrackResult] = []
    for polyline in _LINES_PCF:
        pcf = np.asarray(polyline, dtype=np.float64)
        pix = frame_drawn.from_pcf(pcf)
        lines.append(
            LineTrackResult(
                points_pcf=tuple((float(x), float(y)) for x, y in pcf),
                score_bp=to_basis_points(1.0),
            )
        )
        if draw_lines:
            cv2.polylines(
                canvas,
                [np.round(pix).astype(np.int32)],
                False,
                (60, 70, 120),
                max(2, thickness // 6),
                cv2.LINE_AA,
            )

    if occlude:
        cx, cy = (int(v) for v in np.round(px[9] + (px[0] - px[9]) * 0.45))
        cv2.circle(canvas, (cx, cy), max(20, int(0.18 * width)), (30, 30, 30), -1)

    work: Any = (canvas.astype(np.float64) - 128.0) * contrast + 128.0 + brightness
    if noise_sigma > 0:
        work = work + rng.normal(0.0, noise_sigma, work.shape)
    img: Any = np.clip(np.round(work), 0, 255).astype(np.uint8)
    if blur_sigma > 0:
        img = cv2.GaussianBlur(img, (0, 0), blur_sigma)
    if mirrored:
        # the geometry above is drawn unmirrored; flip the pixels (landmarks are already flipped)
        img = img[:, ::-1].copy()
    name = image_id or f"SYNTH-{side.value}-{seed}"
    return SyntheticPalm(
        image=image_from_array(np.ascontiguousarray(img), name),
        landmarks=landmarks,
        side=side,
        mirrored=mirrored,
        lines=tuple(lines),
        frame=frame,
    )
