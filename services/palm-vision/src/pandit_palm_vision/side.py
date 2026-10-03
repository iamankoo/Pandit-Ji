"""Left/right hand classification (Phase 13; standards PM-10).

The side is never guessed. It is established only when **all** of these hold, otherwise it is
``UNDETERMINED`` with explicit reasons:

1. the capture says the palm faces the camera (``CaptureContext.palm_facing``): the side cannot
   be read from a 2D image of the back of a hand with the same rule;
2. the mirroring of the input (``CaptureContext.mirrored``) and the mirroring the detector
   assumes when it names a hand (``DetectionResult.assumes_mirrored_input``) are both known;
3. the detector's label, corrected for any mirroring mismatch, agrees with an independent
   geometric reading of the landmarks;
4. the label's score reaches a configured minimum, when one is configured.

Limitation (stated, not hidden): the mirroring and palm-facing declarations are **capture facts the
caller must supply truthfully**. A mirrored image of a right hand is geometrically a left hand, so
no 2D evidence distinguishes a false mirroring declaration from the truth: it yields the opposite
side. The checks above catch a detector label that contradicts the declared capture, not a false
declaration.

Geometric convention (an engineering convention, **to be validated on real labelled images**):
for a palm facing the camera in an unmirrored image, the sign of the cross product of
``index_mcp - wrist`` and ``pinky_mcp - wrist`` (image coordinates, y downward) is negative for
a right hand and positive for a left hand; a mirrored image flips it. The synthetic fixtures use
the same convention, so tests prove consistency, not correctness on real photographs.
"""

from __future__ import annotations

from dataclasses import dataclass

from pandit_contracts.palm import HandSide

from pandit_palm_vision.hand import INDEX_MCP, PINKY_MCP, WRIST, HandCandidate
from pandit_palm_vision.image_input import CaptureContext

# A cross product this close to zero means the three landmarks are (nearly) collinear.
_DEGENERATE = 1e-9


@dataclass(frozen=True)
class SideResult:
    side: HandSide
    confidence_bp: int
    reasons: tuple[str, ...]
    method: str = "DETECTOR_LABEL_CHECKED_AGAINST_LANDMARK_GEOMETRY_V1"


def _flip(side: HandSide) -> HandSide:
    if side is HandSide.LEFT:
        return HandSide.RIGHT
    if side is HandSide.RIGHT:
        return HandSide.LEFT
    return side


def geometric_side(landmarks: tuple[tuple[float, float], ...]) -> HandSide:
    """The side implied by the landmarks for a palm-facing hand in an unmirrored image."""
    wx, wy = landmarks[WRIST]
    ix, iy = landmarks[INDEX_MCP]
    px, py = landmarks[PINKY_MCP]
    cross = (ix - wx) * (py - wy) - (iy - wy) * (px - wx)
    if abs(cross) < _DEGENERATE:
        return HandSide.UNDETERMINED
    return HandSide.RIGHT if cross < 0 else HandSide.LEFT


def classify_side(
    candidate: HandCandidate,
    context: CaptureContext,
    assumes_mirrored_input: bool | None,
    min_confidence_bp: int | None = None,
) -> SideResult:
    undetermined = HandSide.UNDETERMINED
    if context.palm_facing is None:
        return SideResult(undetermined, 0, ("PALM_FACING_UNKNOWN",))
    if context.palm_facing is False:
        return SideResult(undetermined, 0, ("NOT_PALM_FACING",))
    if context.mirrored is None:
        return SideResult(undetermined, 0, ("INPUT_MIRRORING_UNKNOWN",))
    if assumes_mirrored_input is None:
        return SideResult(undetermined, 0, ("DETECTOR_MIRRORING_ASSUMPTION_UNKNOWN",))

    labelled = HandSide.LEFT if candidate.handedness_label == "Left" else HandSide.RIGHT
    if context.mirrored != assumes_mirrored_input:
        labelled = _flip(labelled)

    geometric = geometric_side(candidate.landmarks)
    if geometric is HandSide.UNDETERMINED:
        return SideResult(undetermined, 0, ("LANDMARK_GEOMETRY_DEGENERATE",))
    if context.mirrored:
        geometric = _flip(geometric)
    if geometric is not labelled:
        return SideResult(undetermined, 0, ("SIDE_LABEL_GEOMETRY_DISAGREE",))

    if min_confidence_bp is not None and candidate.handedness_score_bp < min_confidence_bp:
        return SideResult(undetermined, candidate.handedness_score_bp, ("SIDE_CONFIDENCE_LOW",))
    return SideResult(labelled, candidate.handedness_score_bp, ())
