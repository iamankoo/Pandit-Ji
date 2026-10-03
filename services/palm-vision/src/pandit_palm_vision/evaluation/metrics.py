"""Evaluation metrics, all returning integers (basis points or fixed-point) or ``None``.

``None`` means the metric is undefined for the data (an empty denominator): it is never
reported as 0 or 100 percent. Nothing here sets or implies an acceptance threshold.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from pandit_contracts.palm_canonical import BASIS_POINTS, PCF_SCALE, to_fixed

BoolMask = npt.NDArray[np.bool_]
Polyline = Sequence[tuple[float, float]]


def ratio_bp(numerator: int, denominator: int) -> int | None:
    if denominator <= 0:
        return None
    return round(numerator * BASIS_POINTS / denominator)


@dataclass(frozen=True)
class Confusion:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    @property
    def precision_bp(self) -> int | None:
        return ratio_bp(self.tp, self.tp + self.fp)

    @property
    def recall_bp(self) -> int | None:
        return ratio_bp(self.tp, self.tp + self.fn)

    @property
    def false_positive_rate_bp(self) -> int | None:
        return ratio_bp(self.fp, self.fp + self.tn)

    @property
    def accuracy_bp(self) -> int | None:
        return ratio_bp(self.tp + self.tn, self.tp + self.fp + self.fn + self.tn)


def confusion(predicted: Sequence[bool], truth: Sequence[bool]) -> Confusion:
    if len(predicted) != len(truth):
        raise ValueError("predictions and truth differ in length")
    tp = sum(1 for p, t in zip(predicted, truth, strict=True) if p and t)
    fp = sum(1 for p, t in zip(predicted, truth, strict=True) if p and not t)
    fn = sum(1 for p, t in zip(predicted, truth, strict=True) if not p and t)
    tn = sum(1 for p, t in zip(predicted, truth, strict=True) if not p and not t)
    return Confusion(tp, fp, fn, tn)


def accuracy_bp(correct: int, total: int) -> int | None:
    return ratio_bp(correct, total)


def iou_dice_bp(pred: BoolMask, truth: BoolMask) -> tuple[int | None, int | None]:
    """Intersection over union and Dice of two boolean masks (both ``None`` if both empty)."""
    inter = int(np.logical_and(pred, truth).sum())
    union = int(np.logical_or(pred, truth).sum())
    total = int(pred.sum()) + int(truth.sum())
    return ratio_bp(inter, union), ratio_bp(2 * inter, total)


def mean_landmark_error_fixed(
    pred: Sequence[tuple[float, float]], truth: Sequence[tuple[float, float]]
) -> int | None:
    """Mean Euclidean error of matched landmarks in palm units (fixed point, 10^-4)."""
    if len(pred) != len(truth) or not pred:
        return None
    errors = np.hypot(
        np.asarray(pred, dtype=np.float64)[:, 0] - np.asarray(truth, dtype=np.float64)[:, 0],
        np.asarray(pred, dtype=np.float64)[:, 1] - np.asarray(truth, dtype=np.float64)[:, 1],
    )
    return to_fixed(float(errors.mean()), PCF_SCALE)


def _resample(points: Polyline, count: int) -> npt.NDArray[np.float64]:
    pts = np.asarray(points, dtype=np.float64)
    seg = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    if cum[-1] <= 0:
        return np.repeat(pts[:1], count, axis=0)
    targets = np.linspace(0.0, cum[-1], count)
    return np.stack(
        [np.interp(targets, cum, pts[:, 0]), np.interp(targets, cum, pts[:, 1])], axis=1
    )


def polyline_distance(a: Polyline, b: Polyline, samples: int = 32) -> float:
    """Mean symmetric nearest-point distance between two polylines (palm units)."""
    pa, pb = _resample(a, samples), _resample(b, samples)
    dist = np.hypot(pa[:, None, 0] - pb[None, :, 0], pa[:, None, 1] - pb[None, :, 1])
    return float(0.5 * (dist.min(axis=1).mean() + dist.min(axis=0).mean()))


@dataclass(frozen=True)
class LineMatch:
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision_bp(self) -> int | None:
        return ratio_bp(self.true_positives, self.true_positives + self.false_positives)

    @property
    def recall_bp(self) -> int | None:
        return ratio_bp(self.true_positives, self.true_positives + self.false_negatives)


def match_lines(
    predicted: Sequence[Polyline], truth: Sequence[Polyline], tolerance_fixed: int
) -> LineMatch:
    """One-to-one greedy matching of predicted to true polylines within ``tolerance_fixed``.

    The tolerance is an explicit argument: there is no default distance (CALIBRATION_REQUIRED).
    """
    tol = tolerance_fixed / PCF_SCALE
    pairs = sorted(
        (polyline_distance(p, t), i, j)
        for i, p in enumerate(predicted)
        for j, t in enumerate(truth)
    )
    used_p: set[int] = set()
    used_t: set[int] = set()
    for distance, i, j in pairs:
        if distance <= tol and i not in used_p and j not in used_t:
            used_p.add(i)
            used_t.add(j)
    tp = len(used_p)
    return LineMatch(tp, len(predicted) - tp, len(truth) - tp)


@dataclass(frozen=True)
class CalibrationBin:
    lo_bp: int
    hi_bp: int
    count: int
    mean_confidence_bp: int | None
    accuracy_bp: int | None


def calibration_bins(
    confidences_bp: Sequence[int], correct: Sequence[bool], bins: int = 10
) -> tuple[tuple[CalibrationBin, ...], int | None]:
    """Reliability bins and the expected calibration error (bp). Descriptive only."""
    if len(confidences_bp) != len(correct):
        raise ValueError("confidences and outcomes differ in length")
    n = len(confidences_bp)
    out: list[CalibrationBin] = []
    ece_num = 0.0
    for b in range(bins):
        lo = b * BASIS_POINTS // bins
        hi = (b + 1) * BASIS_POINTS // bins
        last = b == bins - 1
        idx = [i for i, c in enumerate(confidences_bp) if lo <= c < hi or (last and c == hi)]
        if not idx:
            out.append(CalibrationBin(lo, hi, 0, None, None))
            continue
        mean_conf = sum(confidences_bp[i] for i in idx) / len(idx)
        acc = sum(1 for i in idx if correct[i]) / len(idx) * BASIS_POINTS
        out.append(CalibrationBin(lo, hi, len(idx), round(mean_conf), round(acc)))
        ece_num += len(idx) * abs(mean_conf - acc)
    return tuple(out), (round(ece_num / n) if n else None)
