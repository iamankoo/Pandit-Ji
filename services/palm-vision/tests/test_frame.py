from __future__ import annotations

import numpy as np
import pytest
from pandit_contracts.palm import HandSide

from pandit_palm_vision.frame import (
    MOUNT_ANCHORS,
    PCF_SCALE,
    DegenerateHandError,
    build_frame,
    landmark_points_pcf,
    landmarks_px,
    mount_polygon_pcf,
    palm_polygon_pcf,
    quantize,
    roi_geometry,
    venus_polygon_pcf,
)
from pandit_palm_vision.hand import MIDDLE_MCP, WRIST, HandCandidate
from pandit_palm_vision.synthetic import SyntheticPalm, make_synthetic_palm


def _frame_and_landmarks(palm: SyntheticPalm) -> tuple[object, np.ndarray]:
    candidate = palm.candidate(False)
    frame = build_frame(candidate, palm.side, 480, 640, palm.mirrored)
    return frame, landmark_points_pcf(candidate, frame)


def test_the_wrist_is_the_origin_and_the_middle_base_is_one_unit_up(
    right_palm: SyntheticPalm,
) -> None:
    _, pts = _frame_and_landmarks(right_palm)
    assert pts[WRIST] == pytest.approx((0.0, 0.0), abs=1e-9)
    assert pts[MIDDLE_MCP][0] == pytest.approx(0.0, abs=1e-9)
    assert pts[MIDDLE_MCP][1] == pytest.approx(1.0, abs=1e-9)


def test_pixels_to_pcf_and_back_is_the_identity(right_palm: SyntheticPalm) -> None:
    candidate = right_palm.candidate(False)
    frame = build_frame(candidate, right_palm.side, 480, 640, False)
    px = landmarks_px(candidate, 480, 640)
    assert frame.from_pcf(frame.to_pcf(px)) == pytest.approx(px, abs=1e-9)


def test_left_and_right_hands_become_comparable_and_the_mirroring_is_recorded(
    right_palm: SyntheticPalm, left_palm: SyntheticPalm
) -> None:
    frame_r, pts_r = _frame_and_landmarks(right_palm)
    frame_l, pts_l = _frame_and_landmarks(left_palm)
    assert frame_r.mirrored_for_canonical is False  # type: ignore[attr-defined]
    assert frame_l.mirrored_for_canonical is True  # type: ignore[attr-defined]
    # the synthetic left hand is the mirror of the right: after the recorded mirroring they agree
    assert pts_l == pytest.approx(pts_r, abs=1e-9)


def test_a_mirrored_capture_gives_the_same_canonical_coordinates() -> None:
    plain = make_synthetic_palm(HandSide.RIGHT, seed=5)
    mirrored = make_synthetic_palm(HandSide.RIGHT, seed=5, mirrored=True)
    q_plain = quantize(_frame_and_landmarks(plain)[1])
    q_mirror = quantize(_frame_and_landmarks(mirrored)[1])
    assert (
        max(
            abs(a - c)
            for p, q in zip(q_plain, q_mirror, strict=True)
            for a, c in zip(p, q, strict=True)
        )
        <= 1
    )
    assert _frame_and_landmarks(mirrored)[0].mirrored_for_canonical is True  # type: ignore[attr-defined]


def test_the_canonical_frame_is_rotation_and_scale_invariant() -> None:
    base = make_synthetic_palm(HandSide.RIGHT, seed=7)
    moved = make_synthetic_palm(
        HandSide.RIGHT, seed=7, rotation_deg=25.0, scale=0.8, shift=(0.03, -0.02)
    )
    a = quantize(_frame_and_landmarks(base)[1])
    b = quantize(_frame_and_landmarks(moved)[1])
    # equal up to the rounding of the synthetic image coordinates (a few 10^-4 palm units)
    assert (
        max(abs(x - y) for p, q in zip(a, b, strict=True) for x, y in zip(p, q, strict=True)) <= 60
    )


def test_quantization_is_integer_and_half_even() -> None:
    q = quantize(np.array([[0.00004, 1.00006], [-0.12345, 0.5]]))
    assert q == ((0, 10001), (-1234, 5000))
    assert all(isinstance(v, int) for pair in q for v in pair)


def test_no_frame_is_built_for_an_undetermined_side(right_palm: SyntheticPalm) -> None:
    with pytest.raises(ValueError, match="determined side"):
        build_frame(right_palm.candidate(False), HandSide.UNDETERMINED, 480, 640)


def test_a_degenerate_hand_has_no_frame() -> None:
    flat = HandCandidate(((0.5, 0.5),) * 21, "Right", 9000, 9000)
    with pytest.raises(DegenerateHandError):
        build_frame(flat, HandSide.RIGHT, 100, 100)


def test_the_roi_transform_maps_the_landmarks_to_where_the_inverse_says(
    right_palm: SyntheticPalm,
) -> None:
    candidate = right_palm.candidate(False)
    frame = build_frame(candidate, right_palm.side, 480, 640, False)
    matrix = frame.affine_to_roi(256)
    px = landmarks_px(candidate, 480, 640)
    roi_pts = px @ matrix[:, :2].T + matrix[:, 2]
    back = frame.roi_to_pcf(roi_pts, 256)
    assert back == pytest.approx(frame.to_pcf(px), abs=1e-9)
    scale, x_min, y_max = roi_geometry(256)
    wrist_roi = roi_pts[WRIST]
    assert wrist_roi[0] == pytest.approx((0.0 - x_min) * scale)
    assert wrist_roi[1] == pytest.approx((y_max - 0.0) * scale)


def test_regions_are_polygons_in_the_canonical_frame(right_palm: SyntheticPalm) -> None:
    _, pts = _frame_and_landmarks(right_palm)
    assert palm_polygon_pcf(pts).shape == (6, 2)
    assert venus_polygon_pcf(pts).shape == (4, 2)
    for name in MOUNT_ANCHORS:
        poly = mount_polygon_pcf(name, pts)
        assert poly.shape == (4, 2)
        assert (
            poly[:, 1] < pts[MOUNT_ANCHORS[name]][1]
        ).all()  # under the finger base, toward the wrist
    assert PCF_SCALE == 10_000
