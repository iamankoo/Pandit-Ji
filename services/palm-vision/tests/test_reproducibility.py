from __future__ import annotations

import json

import pytest
from pandit_contracts.palm import (
    FactType,
    PalmFactSet,
    build_palm_fact,
    build_palm_fact_set,
)

from pandit_palm_vision.reproducibility import (
    TOLERANCE_FILE,
    ToleranceRecord,
    compare_fact_sets,
    load_tolerances,
    repeat_check,
)
from pandit_palm_vision.synthetic import SyntheticPalm
from tests.helpers import PALM_FACING, pipeline_for


def _tolerance(**overrides: object) -> ToleranceRecord:
    fields: dict[str, object] = {
        "tolerance_id": "T-TEST",
        "version": "1",
        "status": "CALIBRATED",
        "max_coord_deviation_fixed": 5,
        "max_score_deviation_bp": 50,
        "calibration_report_sha256": "a" * 64,
    }
    fields.update(overrides)
    return ToleranceRecord(**fields)  # type: ignore[arg-type]


def _perturbed(fact_set: PalmFactSet, coord: int = 0, score: int = 0) -> PalmFactSet:
    """The same fact set with the palm region moved by ``coord`` fixed units (same provenance)."""
    facts = []
    for fact in fact_set.facts:
        if fact.fact_type is FactType.PALM_REGION and fact.geometry is not None:
            moved = tuple((x + coord, y) for x, y in fact.geometry.coords_fixed)
            fields = fact.model_dump(exclude={"fact_id", "fact_hash"})
            fields["geometry"] = {"kind": "POLYGON", "coords_fixed": moved}
            fields["confidence"] = {"score_bp": fact.confidence.score_bp + score}
            fact = build_palm_fact(**fields)
        facts.append(fact)
    return build_palm_fact_set(
        analysis_id=fact_set.analysis_id,
        image_ref=fact_set.image_ref,
        quality_result=fact_set.quality_result,
        facts=facts,
        provenance_blocks=list(fact_set.provenance_blocks),
    )


def test_the_committed_tolerances_are_calibration_required_with_no_invented_number() -> None:
    record = load_tolerances()
    assert record.status == "CALIBRATION_REQUIRED" and not record.calibrated
    assert record.max_coord_deviation_fixed is None and record.max_score_deviation_bp is None
    assert record.calibration_report_sha256 is None
    raw = json.loads(TOLERANCE_FILE.read_text(encoding="utf-8"))
    assert all(raw[k] is None for k in ("max_coord_deviation_fixed", "max_score_deviation_bp"))


def test_a_calibrated_record_needs_all_its_numbers_and_a_report() -> None:
    assert _tolerance().calibrated
    assert not _tolerance(calibration_report_sha256=None).calibrated
    assert not _tolerance(max_score_deviation_bp=None).calibrated
    assert not _tolerance(status="CALIBRATION_REQUIRED").calibrated


def test_identical_pinned_runs_are_identical_not_merely_close(right_palm: SyntheticPalm) -> None:
    pipeline = pipeline_for(right_palm)
    report = repeat_check(
        lambda: pipeline.run(right_palm.image, PALM_FACING).fact_set, load_tolerances(), runs=3
    )
    assert report.verdict == "IDENTICAL" and report.max_coord_deviation_fixed == 0


def test_without_a_calibrated_tolerance_the_framework_measures_and_gives_no_verdict(
    right_palm: SyntheticPalm,
) -> None:
    base = pipeline_for(right_palm).run(right_palm.image, PALM_FACING).fact_set
    report = compare_fact_sets(base, _perturbed(base, coord=3, score=10), load_tolerances())
    assert report.verdict == "CALIBRATION_REQUIRED"
    assert report.max_coord_deviation_fixed == 3 and report.max_score_deviation_bp == 10


def test_with_a_calibrated_tolerance_the_verdict_is_within_or_outside(
    right_palm: SyntheticPalm,
) -> None:
    base = pipeline_for(right_palm).run(right_palm.image, PALM_FACING).fact_set
    assert (
        compare_fact_sets(base, _perturbed(base, 3, 10), _tolerance()).verdict == "WITHIN_TOLERANCE"
    )
    assert (
        compare_fact_sets(base, _perturbed(base, 9, 10), _tolerance()).verdict
        == "OUTSIDE_TOLERANCE"
    )
    assert (
        compare_fact_sets(base, _perturbed(base, 3, 99), _tolerance()).verdict
        == "OUTSIDE_TOLERANCE"
    )


def test_different_inputs_are_not_pinned_identically(
    right_palm: SyntheticPalm, left_palm: SyntheticPalm
) -> None:
    a = pipeline_for(right_palm).run(right_palm.image, PALM_FACING).fact_set
    b = pipeline_for(left_palm).run(left_palm.image, PALM_FACING).fact_set
    assert compare_fact_sets(a, b, _tolerance()).verdict == "INPUTS_NOT_PINNED_IDENTICALLY"


def test_a_structural_difference_is_never_hidden_by_a_tolerance(right_palm: SyntheticPalm) -> None:
    base = pipeline_for(right_palm).run(right_palm.image, PALM_FACING).fact_set
    shorter = build_palm_fact_set(
        analysis_id=base.analysis_id,
        image_ref=base.image_ref,
        quality_result=base.quality_result,
        facts=list(base.facts)[:-1],
        provenance_blocks=list(base.provenance_blocks),
    )
    report = compare_fact_sets(base, shorter, _tolerance(max_coord_deviation_fixed=10**6))
    assert report.verdict == "STRUCTURE_MISMATCH" and report.mismatches


def test_at_least_two_runs_are_needed(right_palm: SyntheticPalm) -> None:
    with pytest.raises(ValueError):
        repeat_check(
            lambda: pipeline_for(right_palm).run(right_palm.image, PALM_FACING).fact_set,
            load_tolerances(),
            runs=1,
        )
