"""A small deterministic SYNTHETIC evaluation set (generated; non-identifying; plumbing only).

Used to exercise the harness, the dataset governance checks and the reproducibility framework
end to end. Its reports say nothing about accuracy on real hands (``SYNTHETIC_PLUMBING_ONLY``).
"""

from __future__ import annotations

from pandit_contracts.palm import HandSide

from pandit_palm_vision.evaluation.dataset import DatasetManifest, SampleRecord
from pandit_palm_vision.evaluation.harness import EvalSample, GroundTruth
from pandit_palm_vision.frame import landmark_points_pcf, palm_polygon_pcf
from pandit_palm_vision.hand import HandCandidate, MappingHandDetector
from pandit_palm_vision.image_input import CaptureContext
from pandit_palm_vision.synthetic import SyntheticPalm, make_synthetic_palm


def ground_truth_of(palm: SyntheticPalm) -> GroundTruth:
    candidate = HandCandidate(palm.landmarks, "Right", 9500, 9800)
    points = landmark_points_pcf(candidate, palm.frame)
    return GroundTruth(
        hand_present=True,
        side=palm.side,
        landmarks_pcf=tuple((float(x), float(y)) for x, y in points),
        palm_polygon_pcf=tuple((float(x), float(y)) for x, y in palm_polygon_pcf(points)),
        lines=tuple(track.points_pcf for track in palm.lines),
        usable=True,
    )


_VARIATIONS: tuple[dict[str, object], ...] = (
    {"lighting": "indoor", "background": "plain", "orientation": "upright", "kwargs": {}},
    {"lighting": "low", "background": "plain", "orientation": "upright",
     "kwargs": {"brightness": -15}},
    {"lighting": "mixed", "background": "textured", "orientation": "rotated",
     "kwargs": {"rotation_deg": 12.0, "background": "noisy", "noise_sigma": 4.0}},
    {"lighting": "outdoor", "background": "plain", "orientation": "mirrored_capture",
     "kwargs": {"mirrored": True}},
)  # fmt: skip


def synthetic_eval_set(
    contributors: int = 4,
) -> tuple[DatasetManifest, list[EvalSample], MappingHandDetector]:
    """``contributors`` synthetic contributors, both hands each, split by contributor."""
    splits = ("train", "validation", "test")
    records: list[SampleRecord] = []
    samples: list[EvalSample] = []
    candidates: dict[str, tuple[HandCandidate, ...]] = {}
    for c in range(contributors):
        split = splits[c % len(splits)]
        for h, side in enumerate((HandSide.LEFT, HandSide.RIGHT)):
            var = _VARIATIONS[(c + h) % len(_VARIATIONS)]
            kwargs = dict(var["kwargs"])  # type: ignore[call-overload]
            # Every contributor's hand differs a little (a small deterministic shift and scale),
            # so no two synthetic images are byte-identical and none can leak across splits.
            kwargs.setdefault("shift", (0.004 * c - 0.01 * h, 0.003 * c))
            kwargs.setdefault("scale", 1.0 - 0.01 * c - 0.005 * h)
            palm = make_synthetic_palm(
                side, seed=100 * c + h, image_id=f"SYNTH-{c:02d}-{side.value}", **kwargs
            )
            record = SampleRecord(
                image_id=palm.image.image_id,
                content_sha256=palm.image.content_sha256,
                contributor_id=f"SYNTH-CONTRIB-{c:02d}",
                split=split,  # type: ignore[arg-type]
                hand_side=side,
                device_id="SYNTHETIC_RENDERER",
                lighting=str(var["lighting"]),
                background=str(var["background"]),
                resolution="medium",
                orientation=str(var["orientation"]),
                occlusion="none",
                synthetic=True,
            )
            records.append(record)
            candidates[palm.image.image_id] = (palm.candidate(assumes_mirrored=False),)
            samples.append(
                EvalSample(
                    record,
                    palm.image,
                    CaptureContext(mirrored=palm.mirrored, palm_facing=True),
                    ground_truth_of(palm),
                )
            )
    manifest = DatasetManifest(
        dataset_id="SYNTHETIC_PLUMBING_SET",
        dataset_version="1",
        annotation_version="SYNTHETIC_BY_CONSTRUCTION",
        guideline_version="NOT_APPLICABLE",
        label_vocabulary=("HAND_PRESENT", "HAND_SIDE", "LANDMARKS_21", "LINE_TRACK_POLYLINE"),
        synthetic=True,
        records=tuple(records),
    )
    return manifest, samples, MappingHandDetector(candidates)
