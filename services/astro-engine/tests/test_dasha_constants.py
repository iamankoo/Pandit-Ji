"""Vimshottari constants, profiles and the single source of truth."""

from __future__ import annotations

import pytest

from pandit_astro_engine.dashas.constants import (
    LEVEL_ORDER,
    MAX_DEPTH,
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_TOTAL_YEARS,
    VIMSHOTTARI_YEARS,
    DashaLevel,
)
from pandit_astro_engine.dashas.profiles import (
    BALANCE_BPHS_TIME_ID,
    BALANCE_LONGITUDE_ID,
    BALANCE_PHALADEEPIKA_ID,
    BALANCE_PROFILES,
    DEFAULT_BALANCE_PROFILE_ID,
    DEFAULT_YEAR_LENGTH_PROFILE_ID,
    YEAR_365_2425_ID,
    YEAR_LENGTH_PROFILES,
    EvidenceLabel,
    ProfileAvailability,
)
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import NAKSHATRA_LORD, NAKSHATRA_ORDER

B = CelestialBody


def test_vimshottari_sequence_is_the_documented_order() -> None:
    assert list(VIMSHOTTARI_SEQUENCE) == [
        B.KETU,
        B.VENUS,
        B.SUN,
        B.MOON,
        B.MARS,
        B.RAHU,
        B.JUPITER,
        B.SATURN,
        B.MERCURY,
    ]


def test_vimshottari_years_are_the_documented_values_and_total_120() -> None:
    assert VIMSHOTTARI_YEARS == {
        B.KETU: 7,
        B.VENUS: 20,
        B.SUN: 6,
        B.MOON: 10,
        B.MARS: 7,
        B.RAHU: 18,
        B.JUPITER: 16,
        B.SATURN: 19,
        B.MERCURY: 17,
    }
    assert sum(VIMSHOTTARI_YEARS.values()) == VIMSHOTTARI_TOTAL_YEARS == 120


def test_sequence_is_derived_from_the_nakshatra_lord_table_not_duplicated() -> None:
    for index in range(27):
        assert NAKSHATRA_LORD[NAKSHATRA_ORDER[index]] is VIMSHOTTARI_SEQUENCE[index % 9]


def test_every_lord_is_a_nine_graha_body_and_appears_once() -> None:
    assert len(set(VIMSHOTTARI_SEQUENCE)) == 9
    assert set(VIMSHOTTARI_SEQUENCE) == set(CelestialBody)


def test_hierarchy_stops_at_pratyantar() -> None:
    assert LEVEL_ORDER == (
        DashaLevel.MAHADASHA,
        DashaLevel.ANTARDASHA,
        DashaLevel.PRATYANTAR,
    )
    assert MAX_DEPTH == 3
    assert {level.value for level in DashaLevel} == {"mahadasha", "antardasha", "pratyantar"}


def test_default_profiles_are_the_approved_ids() -> None:
    assert DEFAULT_BALANCE_PROFILE_ID == "DASHA_STANDARD_V1_BALANCE_LONGITUDE"
    assert DEFAULT_YEAR_LENGTH_PROFILE_ID == "YEAR_365_2425_FIXED_DAY"
    assert BALANCE_PROFILES[BALANCE_LONGITUDE_ID].is_default
    assert YEAR_LENGTH_PROFILES[YEAR_365_2425_ID].is_default


def test_exactly_one_default_and_it_is_active() -> None:
    for registry in (BALANCE_PROFILES, YEAR_LENGTH_PROFILES):
        defaults = [p for p in registry.values() if p.is_default]
        assert len(defaults) == 1
        assert defaults[0].availability is ProfileAvailability.ACTIVE


def test_source_alternatives_are_preserved_as_inactive_and_labelled() -> None:
    bphs = BALANCE_PROFILES[BALANCE_BPHS_TIME_ID]
    phala = BALANCE_PROFILES[BALANCE_PHALADEEPIKA_ID]
    for profile in (bphs, phala):
        assert profile.availability is ProfileAvailability.INACTIVE
        assert profile.unavailable_reason
        assert profile.references
    assert phala.evidence_label is EvidenceLabel.UNRESOLVED_CONFLICT


def test_the_default_balance_profile_is_an_engineering_convention_not_a_source_claim() -> None:
    profile = BALANCE_PROFILES[BALANCE_LONGITUDE_ID]
    assert profile.evidence_label is EvidenceLabel.ENGINEERING_CONVENTION
    assert YEAR_LENGTH_PROFILES[YEAR_365_2425_ID].evidence_label is (
        EvidenceLabel.ENGINEERING_CONVENTION
    )


def test_default_year_is_exactly_365_2425_days() -> None:
    days = YEAR_LENGTH_PROFILES[YEAR_365_2425_ID].days()
    assert days.numerator * 10000 == 3652425 * days.denominator
    # 365.2425 days is a whole number of seconds, so no sub-microsecond remainder arises.
    assert (days * 86_400).denominator == 1


@pytest.mark.parametrize("profile_id", list(YEAR_LENGTH_PROFILES))
def test_year_profiles_with_a_fixed_length_report_it(profile_id: str) -> None:
    profile = YEAR_LENGTH_PROFILES[profile_id]
    if profile.days_numerator is None:
        with pytest.raises(ValueError):
            profile.days()
    else:
        assert profile.days() > 0
