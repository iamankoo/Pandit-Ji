"""Reproducibility framework (Phase 13; owner decisions K and G, standards PM-15 and PM-31).

A learned palm model is reproducible when a pinned model artifact, preprocessing, runtime,
dependency versions, input image and configuration give *equivalent structured facts within an
explicitly documented, versioned numerical tolerance*. This module is that framework:

* :class:`ToleranceRecord`: the versioned tolerances. Every numeric tolerance is ``None``, status
  ``CALIBRATION_REQUIRED``, until measured on representative evaluation data. **No number is
  invented.** The committed record is
  ``services/palm-vision/tolerances/palm_reproducibility_tolerances.json``; a measured record is
  added there (a new ``tolerance_id`` version), never edited in place.
* :func:`compare_fact_sets`: compares two fact sets structurally and numerically and reports
  ``IDENTICAL`` (equal fact-set hash), ``WITHIN_TOLERANCE`` / ``OUTSIDE_TOLERANCE`` (only when a
  tolerance is calibrated), or ``CALIBRATION_REQUIRED`` (the deviations are measured and shown,
  no verdict is given), and ``INPUTS_NOT_PINNED_IDENTICALLY`` when the provenance identities
  differ, because equivalence is only meaningful for pinned inputs.

No claim of exact (bit-for-bit) reproducibility is made for a learned component unless it is
demonstrated by an ``IDENTICAL`` result over the evaluation set.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pandit_contracts.palm import PalmFact, PalmFactSet
from pydantic import BaseModel, ConfigDict

TOLERANCE_FILE = (
    Path(__file__).resolve().parents[2] / "tolerances" / "palm_reproducibility_tolerances.json"
)

Verdict = Literal[
    "IDENTICAL",
    "WITHIN_TOLERANCE",
    "OUTSIDE_TOLERANCE",
    "CALIBRATION_REQUIRED",
    "STRUCTURE_MISMATCH",
    "INPUTS_NOT_PINNED_IDENTICALLY",
]


class ToleranceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tolerance_id: str
    version: str
    status: Literal["CALIBRATION_REQUIRED", "CALIBRATED"]
    # Maximum absolute deviation of a fixed-point coordinate (PCF-1, 10^-4 palm unit).
    max_coord_deviation_fixed: int | None
    # Maximum absolute deviation of a score in basis points.
    max_score_deviation_bp: int | None
    calibration_report_sha256: str | None
    note: str = ""

    @property
    def calibrated(self) -> bool:
        return (
            self.status == "CALIBRATED"
            and self.max_coord_deviation_fixed is not None
            and self.max_score_deviation_bp is not None
            and self.calibration_report_sha256 is not None
        )


def load_tolerances(path: Path = TOLERANCE_FILE) -> ToleranceRecord:
    return ToleranceRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))


@dataclass(frozen=True)
class FactDeviation:
    key: str
    max_coord_deviation_fixed: int
    score_deviation_bp: int
    value_equal: bool
    visibility_equal: bool


@dataclass(frozen=True)
class ReproducibilityReport:
    verdict: Verdict
    fact_count: int
    max_coord_deviation_fixed: int
    max_score_deviation_bp: int
    mismatches: tuple[str, ...]
    tolerance_id: str
    tolerance_status: str


def _key(fact: PalmFact) -> tuple[str, str, str, str]:
    return (
        fact.fact_type.value,
        fact.region_id or "",
        fact.fact_class.value,
        fact.hand_side.value,
    )


def _coord_deviation(a: PalmFact, b: PalmFact) -> int | None:
    if (a.geometry is None) != (b.geometry is None):
        return None
    if a.geometry is None or b.geometry is None:
        return 0
    ca, cb = a.geometry.coords_fixed, b.geometry.coords_fixed
    if len(ca) != len(cb):
        return None
    return max(
        (max(abs(x1 - x2), abs(y1 - y2)) for (x1, y1), (x2, y2) in zip(ca, cb, strict=True)),
        default=0,
    )


def compare_fact_sets(
    first: PalmFactSet, second: PalmFactSet, tolerance: ToleranceRecord
) -> ReproducibilityReport:
    def report(
        verdict: Verdict, count: int, coord: int, score: int, mismatches: tuple[str, ...]
    ) -> ReproducibilityReport:
        return ReproducibilityReport(
            verdict, count, coord, score, mismatches, tolerance.tolerance_id, tolerance.status
        )

    if first.provenance_blocks != second.provenance_blocks or first.image_ref != second.image_ref:
        return report("INPUTS_NOT_PINNED_IDENTICALLY", 0, 0, 0, ("provenance or image differs",))
    if first.fact_set_hash == second.fact_set_hash:
        return report("IDENTICAL", len(first.facts), 0, 0, ())

    left = {_key(f): f for f in first.facts}
    right = {_key(f): f for f in second.facts}
    if len(left) != len(first.facts) or len(right) != len(second.facts):
        return report("STRUCTURE_MISMATCH", 0, 0, 0, ("non-unique fact keys",))
    if set(left) != set(right):
        only = sorted(set(left) ^ set(right))
        return report("STRUCTURE_MISMATCH", 0, 0, 0, tuple("/".join(k) for k in only))

    max_coord = 0
    max_score = 0
    mismatches: list[str] = []
    for key in sorted(left):
        a, b = left[key], right[key]
        coord = _coord_deviation(a, b)
        if coord is None:
            mismatches.append("/".join(key) + ": geometry shape differs")
            continue
        if a.visibility != b.visibility:
            mismatches.append("/".join(key) + ": visibility differs")
        if a.value != b.value:
            mismatches.append("/".join(key) + ": value differs")
        max_coord = max(max_coord, coord)
        max_score = max(max_score, abs(a.confidence.score_bp - b.confidence.score_bp))
    if mismatches:
        return report("STRUCTURE_MISMATCH", len(left), max_coord, max_score, tuple(mismatches))
    if not tolerance.calibrated:
        return report("CALIBRATION_REQUIRED", len(left), max_coord, max_score, ())
    assert tolerance.max_coord_deviation_fixed is not None
    assert tolerance.max_score_deviation_bp is not None
    within = (
        max_coord <= tolerance.max_coord_deviation_fixed
        and max_score <= tolerance.max_score_deviation_bp
    )
    return report(
        "WITHIN_TOLERANCE" if within else "OUTSIDE_TOLERANCE", len(left), max_coord, max_score, ()
    )


def repeat_check(
    run: Callable[[], PalmFactSet], tolerance: ToleranceRecord, runs: int = 2
) -> ReproducibilityReport:
    """Run the same pinned computation ``runs`` times and compare every run to the first."""
    if runs < 2:
        raise ValueError("at least two runs are needed")
    first = run()
    worst: ReproducibilityReport | None = None
    for _ in range(runs - 1):
        current = compare_fact_sets(first, run(), tolerance)
        if worst is None or _rank(current.verdict) > _rank(worst.verdict):
            worst = current
    assert worst is not None
    return worst


def _rank(verdict: Verdict) -> int:
    order: tuple[Verdict, ...] = (
        "IDENTICAL",
        "WITHIN_TOLERANCE",
        "CALIBRATION_REQUIRED",
        "OUTSIDE_TOLERANCE",
        "STRUCTURE_MISMATCH",
        "INPUTS_NOT_PINNED_IDENTICALLY",
    )
    return order.index(verdict)
