"""Phase 9 WP-C, Profile A: BPHS Ch. 26 (`docs/ASTROLOGY_STANDARDS.md` PD-01
to PD-11). The checkpoint table below is transcribed directly from BPHS's
own stated discrete progression (v.2-5), not derived from the
implementation under test.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.partial_degree_drishti.bphs import (
    BphsDrishtiReason,
    BphsDrishtiRequest,
    BphsDrishtiResult,
    BphsDrishtiStatus,
    calculate_bphs_drishti,
)
from pandit_astro_engine.partial_degree_drishti.profiles import BPHS_26_ID, BPHS_26_PROFILE

MERCURY = CelestialBody.MERCURY  # a non-special planet throughout


def _calc(
    body: CelestialBody, aspecting_longitude: float, aspected_longitude: float
) -> BphsDrishtiResult:
    return calculate_bphs_drishti(
        BphsDrishtiRequest(
            aspecting_body=body,
            aspecting_longitude=aspecting_longitude,
            aspected_longitude=aspected_longitude,
        )
    )


# --------------------------------------------------------------- checkpoints


@pytest.mark.parametrize(
    "delta,expected_house,expected_value",
    [
        (0.0, 1, 0.0),
        (30.0, 2, 0.0),
        (60.0, 3, 15.0),
        (90.0, 4, 45.0),
        (120.0, 5, 30.0),
        (150.0, 6, 0.0),
        (180.0, 7, 60.0),
        (210.0, 8, 45.0),
        (300.0, 11, 0.0),
        (330.0, 12, 0.0),
    ],
)
def test_checkpoints_match_bphs_stated_progression(
    delta: float, expected_house: int, expected_value: float
) -> None:
    result = _calc(MERCURY, 0.0, delta)
    assert result.house == expected_house
    assert result.status is BphsDrishtiStatus.SUCCESS
    assert result.value == expected_value
    assert result.reason_code is None


def test_house_8_is_success_not_a_conflict() -> None:
    """The refinement over an earlier, coarser draft: house 8 resolves
    correctly under BPHS's own confirmed reduction; only 9 and 10 don't."""
    result = _calc(MERCURY, 0.0, 210.0)
    assert result.status is BphsDrishtiStatus.SUCCESS
    assert result.value == 45.0


@pytest.mark.parametrize("delta", [240.0, 270.0])
def test_houses_9_and_10_are_not_evaluable_for_non_special_planets(delta: float) -> None:
    result = _calc(MERCURY, 0.0, delta)
    assert result.status is BphsDrishtiStatus.NOT_EVALUABLE
    assert result.reason_code is BphsDrishtiReason.REDUCTION_RULE_CONFLICT
    assert result.value is None


@pytest.mark.parametrize("delta,house", [(0.0, 1), (30.0, 2), (150.0, 6), (300.0, 11), (330.0, 12)])
def test_never_aspected_houses_are_success_zero_not_not_evaluable(delta: float, house: int) -> None:
    result = _calc(MERCURY, 0.0, delta)
    assert result.status is BphsDrishtiStatus.SUCCESS
    assert result.value == 0.0
    assert result.reason_code is None
    assert result.house == house


# ------------------------------------------------- branch = interpolation


@pytest.mark.parametrize("delta", [31.0, 45.0, 75.0, 89.9, 91.0, 105.0, 135.0, 165.0, 179.9])
def test_general_formula_equals_linear_interpolation(delta: float) -> None:
    """Project-level derivation (PD-04): every branch of BPHS's own v.6-9
    formula is algebraically identical to linear interpolation between the
    v.2-5 checkpoints. This computes both ways and asserts equality,
    rather than merely asserting it in a comment."""
    checkpoints = {
        0.0: 0.0,
        30.0: 0.0,
        60.0: 15.0,
        90.0: 45.0,
        120.0: 30.0,
        150.0: 0.0,
        180.0: 60.0,
    }
    boundaries = sorted(checkpoints)
    lower = max(b for b in boundaries if b <= delta)
    upper = min(b for b in boundaries if b >= delta)
    if lower == upper:
        expected = checkpoints[lower]
    else:
        fraction = (delta - lower) / (upper - lower)
        expected = checkpoints[lower] + fraction * (checkpoints[upper] - checkpoints[lower])
    actual = _calc(MERCURY, 0.0, delta).value
    assert actual is not None
    assert actual == pytest.approx(expected)


# --------------------------------------------------------- special planets


@pytest.mark.parametrize(
    "body,peak_delta,house",
    [
        (CelestialBody.SATURN, 60.0, 3),
        (CelestialBody.SATURN, 270.0, 10),
        (CelestialBody.MARS, 90.0, 4),
        (CelestialBody.MARS, 210.0, 8),
        (CelestialBody.JUPITER, 120.0, 5),
        (CelestialBody.JUPITER, 240.0, 9),
    ],
)
def test_special_planet_exact_peak_is_success_full(
    body: CelestialBody, peak_delta: float, house: int
) -> None:
    result = _calc(body, 0.0, peak_delta)
    assert result.status is BphsDrishtiStatus.SUCCESS
    assert result.value == 60.0
    assert result.house == house
    assert result.is_own_special_house is True


@pytest.mark.parametrize(
    "body,near_peak_delta",
    [
        (CelestialBody.SATURN, 61.0),
        (CelestialBody.SATURN, 271.0),
        (CelestialBody.MARS, 91.0),
        (CelestialBody.MARS, 211.0),
        (CelestialBody.JUPITER, 121.0),
        (CelestialBody.JUPITER, 241.0),
    ],
)
def test_special_planet_off_peak_is_not_evaluable(
    body: CelestialBody, near_peak_delta: float
) -> None:
    """No tolerance is invented: even one degree off the exact peak is
    withheld, per the locked, conservative handling."""
    result = _calc(body, 0.0, near_peak_delta)
    assert result.status is BphsDrishtiStatus.NOT_EVALUABLE
    assert result.reason_code is BphsDrishtiReason.SPECIAL_FORMULA_INTERIOR_UNRESOLVED
    assert result.is_own_special_house is True


def test_special_planet_at_a_house_it_does_not_own_uses_the_general_rule() -> None:
    """Jupiter does not own house 10 (Saturn does) -- Jupiter there falls
    under the ordinary disputed-house handling, not a special-formula case."""
    result = _calc(CelestialBody.JUPITER, 0.0, 270.0)
    assert result.is_own_special_house is False
    assert result.status is BphsDrishtiStatus.NOT_EVALUABLE
    assert result.reason_code is BphsDrishtiReason.REDUCTION_RULE_CONFLICT


def test_special_planet_at_a_generic_house_matches_the_general_value() -> None:
    """Saturn aspecting its own 5th house is not special for Saturn (only
    Jupiter owns the 5th) -- ordinary checkpoint value applies."""
    result = _calc(CelestialBody.SATURN, 0.0, 120.0)
    assert result.is_own_special_house is False
    assert result.status is BphsDrishtiStatus.SUCCESS
    assert result.value == 30.0


# ------------------------------------------------------------- Rahu/Ketu


@pytest.mark.parametrize("body", [CelestialBody.RAHU, CelestialBody.KETU])
@pytest.mark.parametrize("delta", [0.0, 60.0, 90.0, 180.0, 270.0])
def test_nodes_are_not_evaluable_everywhere(body: CelestialBody, delta: float) -> None:
    result = _calc(body, 0.0, delta)
    assert result.status is BphsDrishtiStatus.NOT_EVALUABLE
    assert result.reason_code is BphsDrishtiReason.ASPECTING_NODE_UNRESOLVED
    assert result.value is None


def test_nodes_are_accepted_not_rejected_as_malformed() -> None:
    """Structurally valid CelestialBody values -- a computed result, not a
    validation error (unlike Chara Karaka's definitive Ketu exclusion)."""
    request = BphsDrishtiRequest(
        aspecting_body=CelestialBody.RAHU, aspecting_longitude=0.0, aspected_longitude=90.0
    )
    assert request.aspecting_body is CelestialBody.RAHU
    result = calculate_bphs_drishti(request)
    assert result.status is BphsDrishtiStatus.NOT_EVALUABLE


def test_nodes_preserve_separation_and_house() -> None:
    result = _calc(CelestialBody.RAHU, 10.0, 100.0)
    assert result.separation_degrees == 90.0
    assert result.house == 4


# ------------------------------------------------------------------ misc


def test_deterministic() -> None:
    request = BphsDrishtiRequest(
        aspecting_body=CelestialBody.MARS, aspecting_longitude=15.0, aspected_longitude=200.0
    )
    first = calculate_bphs_drishti(request)
    second = calculate_bphs_drishti(request)
    assert first == second


@pytest.mark.parametrize("bad_longitude", [-0.5, 360.0, 400.0])
def test_invalid_longitude_is_rejected(bad_longitude: float) -> None:
    with pytest.raises(ValidationError, match="invalid longitude"):
        BphsDrishtiRequest(
            aspecting_body=MERCURY, aspecting_longitude=bad_longitude, aspected_longitude=10.0
        )


def test_success_result_contract_forbids_partial_construction() -> None:
    with pytest.raises(ValidationError):
        BphsDrishtiResult(
            profile_id=BPHS_26_ID,
            status=BphsDrishtiStatus.SUCCESS,
            reason_code=BphsDrishtiReason.REDUCTION_RULE_CONFLICT,
            separation_degrees=60.0,
            house=3,
            is_own_special_house=False,
            value=15.0,
        )


def test_not_evaluable_result_contract_forbids_a_value() -> None:
    with pytest.raises(ValidationError):
        BphsDrishtiResult(
            profile_id=BPHS_26_ID,
            status=BphsDrishtiStatus.NOT_EVALUABLE,
            reason_code=BphsDrishtiReason.REDUCTION_RULE_CONFLICT,
            separation_degrees=240.0,
            house=9,
            is_own_special_house=False,
            value=15.0,
        )


def test_profile_provenance() -> None:
    assert BPHS_26_PROFILE.profile_id == BPHS_26_ID
    assert BPHS_26_PROFILE.reference.source_id == "SRC-BPHS-SANTHANAM-1984"
    assert "Ch. 26" in BPHS_26_PROFILE.reference.locator


def test_does_not_conflate_with_graha_drishti_or_rashi_drishti() -> None:
    """Regression: this module's continuous degree-based refinement must
    never be confused with, or substituted for, Phase 5/6's discrete
    graha drishti (`aspects.py`) or WP-B's sign-to-sign Rashi Drishti
    (`jaimini.rashi_drishti`) -- different modules, different rules,
    different inputs."""
    from pandit_astro_engine.aspects import aspected_houses
    from pandit_astro_engine.jaimini.rashi_drishti import rashi_drishti
    from pandit_astro_engine.rashi import Rashi

    # Distinct systems, no shared table or function.
    assert aspected_houses(CelestialBody.MARS, 1) == [4, 7, 8]
    assert len(rashi_drishti(Rashi.ARIES)) == 3
    assert _calc(MERCURY, 0.0, 60.0).value == 15.0
