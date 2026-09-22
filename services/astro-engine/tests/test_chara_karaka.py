"""Phase 9 WP-B-2: Chara Karaka (BPHS Ch. 32 v. 1-17).

The 8-body worked example below is transcribed directly from BPHS's own
printed "standard nativity" table (Santhanam translation, printed p. 319,
page-image verified -- see `research/ASTROLOGY_SOURCES.md` Group 13), not
derived from the implementation under test. Saturn's own printed longitude
was not legible in the scan margin; it is given an engineering placeholder
value here (clearly below Mars's, so Saturn still ranks last/Dara Karaka),
never presented as the source's own figure.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pandit_astro_engine.jaimini.chara_karaka import (
    CharaKarakaReason,
    CharaKarakaRequest,
    CharaKarakaRole,
    CharaKarakaStatus,
    calculate_chara_karaka,
)
from pandit_astro_engine.jaimini.profiles import (
    CHARA_KARAKA_EIGHT_BODY_ID,
    CHARA_KARAKA_PROFILES,
    CHARA_KARAKA_SEVEN_BODY_ID,
)
from pandit_astro_engine.models import CelestialBody

SUN, MOON, MARS, MERCURY, JUPITER, VENUS, SATURN, RAHU = (
    CelestialBody.SUN,
    CelestialBody.MOON,
    CelestialBody.MARS,
    CelestialBody.MERCURY,
    CelestialBody.JUPITER,
    CelestialBody.VENUS,
    CelestialBody.SATURN,
    CelestialBody.RAHU,
)


def _dms(d: int, m: int, s: float) -> float:
    return d + m / 60 + s / 3600


#: BPHS's own printed "standard nativity" (Ch. 29) worked example, p. 319.
_WORKED_EXAMPLE_DEGREES: dict[CelestialBody, float] = {
    MOON: _dms(27, 35, 46),
    VENUS: _dms(27, 17, 30),
    JUPITER: _dms(26, 7, 13),
    RAHU: 30 - _dms(22, 22, 54),  # source gives Rahu's *comparison* degree; reverse it back
    MERCURY: _dms(14, 54, 13),
    SUN: _dms(6, 18, 46),
    MARS: _dms(3, 9, 41),
    SATURN: 1.0,  # engineering placeholder -- see module docstring
}

_SEVEN_BODIES = (SUN, MOON, MARS, MERCURY, JUPITER, VENUS, SATURN)


def test_worked_example_matches_bphs_own_table_exactly() -> None:
    result = calculate_chara_karaka(
        CharaKarakaRequest(
            profile_id=CHARA_KARAKA_EIGHT_BODY_ID, longitudes=_WORKED_EXAMPLE_DEGREES
        )
    )
    assert result.status is CharaKarakaStatus.SUCCESS
    assert result.roles is not None
    expected = {
        CharaKarakaRole.ATMA_KARAKA: MOON,
        CharaKarakaRole.AMATYA_KARAKA: VENUS,
        CharaKarakaRole.BHRATRU_KARAKA: JUPITER,
        CharaKarakaRole.MATRU_KARAKA: RAHU,
        CharaKarakaRole.PITRU_KARAKA: MERCURY,
        CharaKarakaRole.PUTRA_KARAKA: SUN,
        CharaKarakaRole.GNATI_KARAKA: MARS,
        CharaKarakaRole.DARA_KARAKA: SATURN,
    }
    for role in result.roles:
        assert role.body == expected[role.role]
        assert role.status is CharaKarakaStatus.SUCCESS


def test_rahu_reverse_degree_convention() -> None:
    # Rahu at 5 degrees into its sign -> comparison degree is 30 - 5 = 25.
    longitudes = dict.fromkeys(_SEVEN_BODIES, 1.0)
    longitudes[RAHU] = 5.0
    result = calculate_chara_karaka(
        CharaKarakaRequest(profile_id=CHARA_KARAKA_EIGHT_BODY_ID, longitudes=longitudes)
    )
    rahu_candidate = next(c for c in result.candidates if c.body is RAHU)
    assert rahu_candidate.normalized_degree == 5.0
    assert rahu_candidate.comparison_degree == 25.0
    assert result.roles is not None
    assert result.roles[0].body is RAHU  # highest comparison degree -> Atma Karaka


def test_highest_comparison_degree_is_atma_karaka() -> None:
    longitudes = {
        SUN: 1.0,
        MOON: 2.0,
        MARS: 3.0,
        MERCURY: 4.0,
        JUPITER: 5.0,
        VENUS: 6.0,
        SATURN: 29.9,
    }
    result = calculate_chara_karaka(
        CharaKarakaRequest(profile_id=CHARA_KARAKA_SEVEN_BODY_ID, longitudes=longitudes)
    )
    assert result.roles is not None
    assert result.roles[0].role is CharaKarakaRole.ATMA_KARAKA
    assert result.roles[0].body is SATURN


def test_lowest_comparison_degree_gets_the_last_available_role() -> None:
    longitudes = {
        SUN: 1.0,
        MOON: 2.0,
        MARS: 3.0,
        MERCURY: 4.0,
        JUPITER: 5.0,
        VENUS: 6.0,
        SATURN: 0.1,
    }
    result = calculate_chara_karaka(
        CharaKarakaRequest(profile_id=CHARA_KARAKA_SEVEN_BODY_ID, longitudes=longitudes)
    )
    assert result.roles is not None
    # 7-body profile: 7 distinct ranks fill roles 1-7 (Gnati Karaka is last).
    assert result.roles[6].role is CharaKarakaRole.GNATI_KARAKA
    assert result.roles[6].body is SATURN


def test_seven_body_profile_always_leaves_dara_karaka_a_rank_deficit() -> None:
    longitudes = {
        SUN: 1.0,
        MOON: 10.0,
        MARS: 15.0,
        MERCURY: 20.0,
        JUPITER: 25.0,
        VENUS: 5.0,
        SATURN: 29.0,
    }
    result = calculate_chara_karaka(
        CharaKarakaRequest(profile_id=CHARA_KARAKA_SEVEN_BODY_ID, longitudes=longitudes)
    )
    assert result.status is CharaKarakaStatus.SUCCESS
    assert result.roles is not None
    dara = result.roles[-1]
    assert dara.role is CharaKarakaRole.DARA_KARAKA
    assert dara.status is CharaKarakaStatus.NOT_EVALUABLE
    assert dara.reason_code is CharaKarakaReason.RANK_DEFICIT
    assert dara.body is None


def test_exact_degree_minute_second_tie_at_the_top_is_unresolved() -> None:
    longitudes = dict.fromkeys(_SEVEN_BODIES, 1.0)
    longitudes[SUN] = _dms(15, 30, 45)
    longitudes[MOON] = _dms(15, 30, 45)  # identical to the second of arc
    result = calculate_chara_karaka(
        CharaKarakaRequest(profile_id=CHARA_KARAKA_SEVEN_BODY_ID, longitudes=longitudes)
    )
    assert result.status is CharaKarakaStatus.NOT_EVALUABLE
    assert result.reason_code is CharaKarakaReason.TIE_UNRESOLVED
    assert result.roles is None
    # Candidates are still fully reported even though no role could be assigned.
    assert len(result.candidates) == 7


def test_degree_and_minute_tie_broken_by_seconds_is_not_a_tie() -> None:
    longitudes = dict.fromkeys(_SEVEN_BODIES, 1.0)
    longitudes[SUN] = _dms(15, 30, 45)
    longitudes[MOON] = _dms(15, 30, 46)  # one arc-second higher -> Moon wins outright
    result = calculate_chara_karaka(
        CharaKarakaRequest(profile_id=CHARA_KARAKA_SEVEN_BODY_ID, longitudes=longitudes)
    )
    assert result.status is CharaKarakaStatus.SUCCESS
    assert result.roles is not None
    assert result.roles[0].body is MOON
    assert result.roles[0].tie_group is None


def test_mid_rank_tie_is_shared_and_pushes_the_deficit_to_the_bottom_role() -> None:
    longitudes = {
        MOON: 27.0,
        VENUS: 20.0,
        JUPITER: 20.0,  # ties with Venus for rank 2
        MERCURY: 15.0,
        SUN: 10.0,
        MARS: 5.0,
        SATURN: 1.0,
    }
    result = calculate_chara_karaka(
        CharaKarakaRequest(profile_id=CHARA_KARAKA_SEVEN_BODY_ID, longitudes=longitudes)
    )
    assert result.status is CharaKarakaStatus.SUCCESS
    assert result.roles is not None
    amatya = result.roles[1]
    assert amatya.role is CharaKarakaRole.AMATYA_KARAKA
    assert amatya.tie_group == (JUPITER, VENUS)
    # The tie absorbed one rank, so the deficit surfaces at the *last*
    # available role for this profile (Gnati Karaka, the 7th of 7), never
    # at the tied rank itself.
    gnati = result.roles[6]
    assert gnati.role is CharaKarakaRole.GNATI_KARAKA
    assert gnati.status is CharaKarakaStatus.NOT_EVALUABLE
    assert gnati.reason_code is CharaKarakaReason.RANK_DEFICIT


def test_ketu_is_never_a_candidate() -> None:
    with pytest.raises(ValidationError, match="Ketu is never a Chara Karaka candidate"):
        CharaKarakaRequest(
            profile_id=CHARA_KARAKA_SEVEN_BODY_ID,
            longitudes={**dict.fromkeys(_SEVEN_BODIES[:-1], 1.0), CelestialBody.KETU: 5.0},
        )


def test_unknown_profile_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown Chara Karaka profile_id"):
        CharaKarakaRequest(profile_id="not-a-profile", longitudes={})


def test_missing_body_is_rejected() -> None:
    with pytest.raises(ValidationError, match="missing required bodies"):
        CharaKarakaRequest(profile_id=CHARA_KARAKA_SEVEN_BODY_ID, longitudes={SUN: 1.0})


def test_unexpected_body_for_profile_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unexpected bodies"):
        CharaKarakaRequest(
            profile_id=CHARA_KARAKA_SEVEN_BODY_ID,
            longitudes={**dict.fromkeys(_SEVEN_BODIES, 1.0), RAHU: 5.0},
        )


@pytest.mark.parametrize("bad_longitude", [-0.5, 360.0, 400.0])
def test_invalid_longitude_is_rejected(bad_longitude: float) -> None:
    longitudes = dict.fromkeys(_SEVEN_BODIES, 1.0)
    longitudes[SUN] = bad_longitude
    with pytest.raises(ValidationError, match="invalid longitude"):
        CharaKarakaRequest(profile_id=CHARA_KARAKA_SEVEN_BODY_ID, longitudes=longitudes)


def test_deterministic_results() -> None:
    request = CharaKarakaRequest(
        profile_id=CHARA_KARAKA_EIGHT_BODY_ID, longitudes=_WORKED_EXAMPLE_DEGREES
    )
    first = calculate_chara_karaka(request)
    second = calculate_chara_karaka(request)
    assert first == second


def test_success_result_contract_forbids_partial_construction() -> None:
    from pandit_astro_engine.jaimini.chara_karaka import CharaKarakaResult

    with pytest.raises(ValidationError):
        CharaKarakaResult(
            profile_id=CHARA_KARAKA_SEVEN_BODY_ID,
            status=CharaKarakaStatus.SUCCESS,
            reason_code=CharaKarakaReason.TIE_UNRESOLVED,  # success must not carry a reason
            candidates=(),
            roles=(),
        )


def test_not_evaluable_result_contract_forbids_a_role_list() -> None:
    from pandit_astro_engine.jaimini.chara_karaka import CharaKarakaResult

    with pytest.raises(ValidationError):
        CharaKarakaResult(
            profile_id=CHARA_KARAKA_SEVEN_BODY_ID,
            status=CharaKarakaStatus.NOT_EVALUABLE,
            reason_code=CharaKarakaReason.TIE_UNRESOLVED,
            candidates=(),
            roles=(),  # not-evaluable must not carry a role list
        )


def test_profile_provenance() -> None:
    seven = CHARA_KARAKA_PROFILES[CHARA_KARAKA_SEVEN_BODY_ID]
    eight = CHARA_KARAKA_PROFILES[CHARA_KARAKA_EIGHT_BODY_ID]
    assert seven.reference.source_id == "SRC-BPHS-SANTHANAM-1984"
    assert eight.reference.source_id == "SRC-BPHS-SANTHANAM-1984"
    assert CelestialBody.RAHU not in seven.bodies
    assert CelestialBody.RAHU in eight.bodies
    assert CelestialBody.KETU not in seven.bodies and CelestialBody.KETU not in eight.bodies
