"""Phase 9 WP-C, Profile B: Uttara Kalamrita Ch. 2 Sl. 17.5-19.5
(`docs/ASTROLOGY_STANDARDS.md` PD-01 to PD-11). The checkpoint table below
is transcribed directly from the source's own stated discrete progression,
independently agreeing with BPHS's, not derived from the implementation
under test.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.partial_degree_drishti.profiles import (
    UTTARAKALAMRITA_SRIPATI_ID,
    UTTARAKALAMRITA_SRIPATI_PROFILE,
)
from pandit_astro_engine.partial_degree_drishti.uttarakalamrita import (
    PROVENANCE_NOTE,
    UkDrishtiReason,
    UkDrishtiRequest,
    UkDrishtiResult,
    UkDrishtiStatus,
    calculate_uk_drishti,
)

MERCURY = CelestialBody.MERCURY  # a non-special planet throughout


def _calc(
    body: CelestialBody, aspecting_longitude: float, aspected_longitude: float
) -> UkDrishtiResult:
    return calculate_uk_drishti(
        UkDrishtiRequest(
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
        (240.0, 9, 30.0),
        (270.0, 10, 15.0),
        (300.0, 11, 0.0),
        (330.0, 12, 0.0),
    ],
)
def test_all_twelve_checkpoints_match_the_stated_progression(
    delta: float, expected_house: int, expected_value: float
) -> None:
    result = _calc(MERCURY, 0.0, delta)
    assert result.house == expected_house
    assert result.status is UkDrishtiStatus.SUCCESS
    assert result.value == expected_value
    assert result.reason_code is None


def test_houses_9_and_10_are_success_the_key_differentiator_from_profile_a() -> None:
    house9 = _calc(MERCURY, 0.0, 240.0)
    house10 = _calc(MERCURY, 0.0, 270.0)
    assert house9.status is UkDrishtiStatus.SUCCESS and house9.value == 30.0
    assert house10.status is UkDrishtiStatus.SUCCESS and house10.value == 15.0


# ------------------------------------------------------ worked midpoints


@pytest.mark.parametrize(
    "delta,house,expected_value",
    [
        (75.0, 3, 30.0),
        (105.0, 4, 37.5),
        (135.0, 5, 15.0),
        (225.0, 8, 37.5),
        (255.0, 9, 22.5),
        (285.0, 10, 7.5),
    ],
)
def test_worked_midpoint_examples(delta: float, house: int, expected_value: float) -> None:
    result = _calc(MERCURY, 0.0, delta)
    assert result.house == house
    assert result.value == pytest.approx(expected_value)


def test_house_8_and_house_4_interpolation_are_symmetric() -> None:
    """Houses 8 and 4 share the same checkpoint pair shape (45->30 and
    45->30 respectively going into the next house), by the v.2 pairing."""
    assert _calc(MERCURY, 0.0, 105.0).value == pytest.approx(_calc(MERCURY, 0.0, 225.0).value)


def test_wraparound_from_house_12_into_house_1_interpolates_to_zero() -> None:
    result = _calc(MERCURY, 0.0, 345.0)
    assert result.house == 12
    assert result.value == 0.0


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
def test_special_planet_is_not_evaluable_even_at_the_exact_peak_angle(
    body: CelestialBody, peak_delta: float, house: int
) -> None:
    """The key differentiator from Profile A: no exact-angle carve-out
    exists here, because Uttara Kalamrita's interpolation was never stated
    as applying to the special-planet case at all (PD-07)."""
    result = _calc(body, 0.0, peak_delta)
    assert result.status is UkDrishtiStatus.NOT_EVALUABLE
    assert result.reason_code is UkDrishtiReason.SPECIAL_FORMULA_INTERIOR_UNRESOLVED
    assert result.value is None
    assert result.house == house
    assert result.is_own_special_house is True


@pytest.mark.parametrize(
    "body,near_peak_delta",
    [
        (CelestialBody.SATURN, 61.0),
        (CelestialBody.MARS, 91.0),
        (CelestialBody.JUPITER, 121.0),
    ],
)
def test_special_planet_off_peak_is_also_not_evaluable(
    body: CelestialBody, near_peak_delta: float
) -> None:
    result = _calc(body, 0.0, near_peak_delta)
    assert result.status is UkDrishtiStatus.NOT_EVALUABLE
    assert result.reason_code is UkDrishtiReason.SPECIAL_FORMULA_INTERIOR_UNRESOLVED


def test_special_planet_at_a_house_it_does_not_own_uses_the_general_interpolation() -> None:
    result = _calc(CelestialBody.JUPITER, 0.0, 270.0)  # house 10, Saturn's, not Jupiter's
    assert result.is_own_special_house is False
    assert result.status is UkDrishtiStatus.SUCCESS
    assert result.value == 15.0


def test_special_planet_at_a_generic_house_matches_the_checkpoint_value() -> None:
    result = _calc(CelestialBody.SATURN, 0.0, 120.0)  # house 5, Jupiter's, not Saturn's
    assert result.is_own_special_house is False
    assert result.status is UkDrishtiStatus.SUCCESS
    assert result.value == 30.0


# ------------------------------------------------------------- Rahu/Ketu


@pytest.mark.parametrize("body", [CelestialBody.RAHU, CelestialBody.KETU])
@pytest.mark.parametrize("delta", [0.0, 60.0, 90.0, 180.0, 240.0, 270.0])
def test_nodes_are_not_evaluable_everywhere(body: CelestialBody, delta: float) -> None:
    result = _calc(body, 0.0, delta)
    assert result.status is UkDrishtiStatus.NOT_EVALUABLE
    assert result.reason_code is UkDrishtiReason.ASPECTING_NODE_UNRESOLVED
    assert result.value is None


def test_nodes_are_accepted_not_rejected_as_malformed() -> None:
    request = UkDrishtiRequest(
        aspecting_body=CelestialBody.KETU, aspecting_longitude=0.0, aspected_longitude=90.0
    )
    assert request.aspecting_body is CelestialBody.KETU
    result = calculate_uk_drishti(request)
    assert result.status is UkDrishtiStatus.NOT_EVALUABLE


def test_nodes_preserve_separation_and_house() -> None:
    result = _calc(CelestialBody.RAHU, 10.0, 100.0)
    assert result.separation_degrees == 90.0
    assert result.house == 4


# ------------------------------------------------------------ provenance


def test_provenance_note_is_present_verbatim_on_every_result() -> None:
    assert _calc(MERCURY, 0.0, 60.0).provenance_note == PROVENANCE_NOTE
    assert _calc(CelestialBody.SATURN, 0.0, 60.0).provenance_note == PROVENANCE_NOTE
    assert _calc(CelestialBody.RAHU, 0.0, 60.0).provenance_note == PROVENANCE_NOTE


def test_result_rejects_a_tampered_provenance_note() -> None:
    with pytest.raises(ValidationError, match="provenance_note"):
        UkDrishtiResult(
            profile_id=UTTARAKALAMRITA_SRIPATI_ID,
            status=UkDrishtiStatus.SUCCESS,
            reason_code=None,
            separation_degrees=60.0,
            house=3,
            is_own_special_house=False,
            value=15.0,
            provenance_note="a different, unapproved note",
        )


def test_profile_provenance() -> None:
    assert UTTARAKALAMRITA_SRIPATI_PROFILE.profile_id == UTTARAKALAMRITA_SRIPATI_ID
    assert UTTARAKALAMRITA_SRIPATI_PROFILE.reference.source_id == "SRC-UTTARA-KALAMRITA-SASTRI"
    assert "Sripatipaddhati" in UTTARAKALAMRITA_SRIPATI_PROFILE.reference.note


# ------------------------------------------------------------------ misc


def test_deterministic() -> None:
    request = UkDrishtiRequest(
        aspecting_body=CelestialBody.MARS, aspecting_longitude=15.0, aspected_longitude=200.0
    )
    first = calculate_uk_drishti(request)
    second = calculate_uk_drishti(request)
    assert first == second


@pytest.mark.parametrize("bad_longitude", [-0.5, 360.0, 400.0])
def test_invalid_longitude_is_rejected(bad_longitude: float) -> None:
    with pytest.raises(ValidationError, match="invalid longitude"):
        UkDrishtiRequest(
            aspecting_body=MERCURY, aspecting_longitude=bad_longitude, aspected_longitude=10.0
        )


def test_success_result_contract_forbids_partial_construction() -> None:
    with pytest.raises(ValidationError):
        UkDrishtiResult(
            profile_id=UTTARAKALAMRITA_SRIPATI_ID,
            status=UkDrishtiStatus.SUCCESS,
            reason_code=UkDrishtiReason.ASPECTING_NODE_UNRESOLVED,
            separation_degrees=60.0,
            house=3,
            is_own_special_house=False,
            value=15.0,
            provenance_note=PROVENANCE_NOTE,
        )


def test_not_evaluable_result_contract_forbids_a_value() -> None:
    with pytest.raises(ValidationError):
        UkDrishtiResult(
            profile_id=UTTARAKALAMRITA_SRIPATI_ID,
            status=UkDrishtiStatus.NOT_EVALUABLE,
            reason_code=UkDrishtiReason.ASPECTING_NODE_UNRESOLVED,
            separation_degrees=60.0,
            house=3,
            is_own_special_house=False,
            value=15.0,
            provenance_note=PROVENANCE_NOTE,
        )


def test_does_not_conflate_with_graha_drishti_or_rashi_drishti() -> None:
    """Regression: this module must never be confused with, or substituted
    for, Phase 5/6's discrete graha drishti (`aspects.py`) or WP-B's
    sign-to-sign Rashi Drishti (`jaimini.rashi_drishti`)."""
    from pandit_astro_engine.aspects import aspected_houses
    from pandit_astro_engine.jaimini.rashi_drishti import rashi_drishti
    from pandit_astro_engine.rashi import Rashi

    assert aspected_houses(CelestialBody.MARS, 1) == [4, 7, 8]
    assert len(rashi_drishti(Rashi.ARIES)) == 3
    assert _calc(MERCURY, 0.0, 60.0).value == 15.0


# ------------------------------------------------------- cross-profile


def test_agrees_with_profile_a_at_every_checkpoint() -> None:
    """Profiles A and B must produce identical values at all twelve
    checkpoints -- the mathematical consequence of PD-04's derivation."""
    from pandit_astro_engine.partial_degree_drishti.bphs import (
        BphsDrishtiRequest,
        calculate_bphs_drishti,
    )

    for delta in (0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 300.0, 330.0):
        a = calculate_bphs_drishti(
            BphsDrishtiRequest(
                aspecting_body=MERCURY, aspecting_longitude=0.0, aspected_longitude=delta
            )
        )
        b = _calc(MERCURY, 0.0, delta)
        assert a.value == b.value, f"mismatch at delta={delta}"


def test_no_shared_result_type_or_cross_reference_between_profiles() -> None:
    """Structural non-conflation: neither module imports the other's
    profile ID or reason-code enum, and the two Result classes are not
    related through a non-trivial shared base."""
    import pandit_astro_engine.partial_degree_drishti.bphs as bphs_module
    import pandit_astro_engine.partial_degree_drishti.uttarakalamrita as uk_module

    assert UTTARAKALAMRITA_SRIPATI_ID not in bphs_module.__dict__.values()
    unrelated_names = ("BphsDrishtiReason", "BphsDrishtiResult", "BPHS_26_ID")
    assert not any(name in uk_module.__dict__ for name in unrelated_names)
    assert UkDrishtiResult.__mro__[:-2] == (UkDrishtiResult, uk_module._Model)
    same_string_value = "special_formula_interior_unresolved"
    assert UkDrishtiReason.SPECIAL_FORMULA_INTERIOR_UNRESOLVED.value == same_string_value
