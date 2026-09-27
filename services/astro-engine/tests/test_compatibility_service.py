"""Phase 11 compatibility service (`docs/ASTROLOGY_STANDARDS.md` v1.25.0,
CM-01 to CM-12): the minimum-age gate, consent and input validation, no
gender or role input, birth-time uncertainty, structured failures that leak
no birth data, consistency with the Phase 5 Kundli and determinism."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from pydantic import ValidationError

from pandit_astro_engine.compatibility import (
    CompatibilityFacts,
    CompatibilityProfileId,
    CompatibilityRequest,
    CompatibilityService,
    FactorReason,
    FactorStatus,
    MatchParticipantInput,
    MatchReason,
    MatchStatus,
    completed_years,
)
from pandit_astro_engine.dashas.models import BirthTimeInput, BirthTimeStatus
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CalculationConfig,
    LocalDateTimeInput,
    Location,
    ZodiacType,
)

AK = CompatibilityProfileId.ASHTAKOOT_MUHURTA_CHINTAMANI
TP = CompatibilityProfileId.TEN_PORUTHAM_KALAPRAKASIKA
DELHI = Location(latitude=28.6139, longitude=77.209)
TODAY = dt.date(2026, 9, 27)
SERVICE = CompatibilityService()


def person(
    year: int = 1990,
    month: int = 5,
    day: int = 10,
    hour: int = 8,
    tz: str = "Asia/Kolkata",
    birth_time: BirthTimeInput | None = None,
) -> MatchParticipantInput:
    return MatchParticipantInput(
        local_datetime=LocalDateTimeInput(year=year, month=month, day=day, hour=hour, timezone=tz),
        location=DELHI,
        birth_time=birth_time or BirthTimeInput(),
    )


def request(**kwargs: Any) -> CompatibilityRequest:
    base: dict[str, Any] = {
        "profile": AK,
        "person_a": person(),
        "person_b": person(1992, 11, 3, 21),
        "as_of_date": TODAY,
        "participant_consent_attested": True,
    }
    base.update(kwargs)
    return CompatibilityRequest(**base)


class ExplodingAstronomy:
    """Fails the test if any astronomy is attempted."""

    def calculate(self, request: object) -> object:
        raise AssertionError("no astronomy may run for a blocked request")


# --------------------------------------------------------------------------
# Minimum age
# --------------------------------------------------------------------------


def test_completed_years() -> None:
    assert completed_years(dt.date(2008, 9, 27), dt.date(2026, 9, 27)) == 18
    assert completed_years(dt.date(2008, 9, 28), dt.date(2026, 9, 27)) == 17
    assert completed_years(dt.date(2008, 2, 29), dt.date(2026, 2, 28)) == 17
    assert completed_years(dt.date(2008, 2, 29), dt.date(2026, 3, 1)) == 18
    assert completed_years(dt.date(2008, 2, 29), dt.date(2028, 2, 29)) == 20
    assert completed_years(dt.date(2030, 1, 1), dt.date(2026, 1, 1)) is None


@pytest.mark.parametrize("profile", [AK, TP])
def test_a_minor_is_blocked_without_any_fact(profile: CompatibilityProfileId) -> None:
    service = CompatibilityService(ExplodingAstronomy())  # type: ignore[arg-type]
    facts = service.match(request(profile=profile, person_b=person(2008, 9, 28, 10)))
    assert facts.status is MatchStatus.BLOCKED_BY_POLICY
    assert facts.reason is MatchReason.PARTICIPANT_UNDER_MINIMUM_AGE
    assert [c.minimum_age_met for c in facts.policy_checks] == [True, False]
    assert facts.placements == () and facts.factors == () and facts.doshas == ()
    assert facts.ashtakoot_total is None and facts.porutham_summary is None
    dumped = facts.model_dump_json()
    for leak in ("nakshatra", "rashi", "moon", "Asia/Kolkata", "28.6139"):
        assert leak not in dumped


def test_exactly_eighteen_is_allowed() -> None:
    facts = SERVICE.match(request(person_b=person(2008, 9, 27, 10)))
    assert facts.status is MatchStatus.PARTIAL


def test_a_birth_after_the_as_of_date_is_not_verifiable() -> None:
    facts = SERVICE.match(request(as_of_date=dt.date(1991, 1, 1)))
    assert facts.status is MatchStatus.BLOCKED_BY_POLICY
    assert facts.reason is MatchReason.PARTICIPANT_UNDER_MINIMUM_AGE  # A is a baby then
    facts = SERVICE.match(request(as_of_date=dt.date(1980, 1, 1)))
    assert facts.reason is MatchReason.AGE_NOT_VERIFIABLE


# --------------------------------------------------------------------------
# Input validation, consent, no gender or role
# --------------------------------------------------------------------------


def test_consent_must_be_attested() -> None:
    with pytest.raises(ValidationError):
        request(participant_consent_attested=False)
    with pytest.raises(ValidationError):
        CompatibilityRequest(profile=AK, person_a=person(), person_b=person(), as_of_date=TODAY)  # type: ignore[call-arg]


def test_profile_has_no_default_and_second_person_is_required() -> None:
    with pytest.raises(ValidationError):
        CompatibilityRequest(  # type: ignore[call-arg]
            person_a=person(), person_b=person(), as_of_date=TODAY,
            participant_consent_attested=True,
        )  # fmt: skip
    with pytest.raises(ValidationError):
        CompatibilityRequest(  # type: ignore[call-arg]
            profile=AK, person_a=person(), as_of_date=TODAY, participant_consent_attested=True
        )


@pytest.mark.parametrize("field", ["gender", "role", "sex", "bride", "groom"])
def test_no_gender_or_role_field_is_accepted(field: str) -> None:
    data = request().model_dump(mode="json")
    data["person_a"][field] = "x"
    with pytest.raises(ValidationError):
        CompatibilityRequest.model_validate(data)
    data = request().model_dump(mode="json")
    data[field] = "x"
    with pytest.raises(ValidationError):
        CompatibilityRequest.model_validate(data)


def test_invalid_inputs_are_structured() -> None:
    bad_date = SERVICE.match(request(person_a=person(1990, 2, 30)))
    assert bad_date.status is MatchStatus.INVALID_INPUT
    assert bad_date.reason is MatchReason.INVALID_BIRTH_DATE
    bad_tz = SERVICE.match(request(person_a=person(tz="Mars/Olympus")))
    assert bad_tz.reason is MatchReason.INVALID_TIMEZONE
    tropical = SERVICE.match(
        request(config=CalculationConfig(zodiac=ZodiacType.TROPICAL, ayanamsa=None))
    )
    assert tropical.reason is MatchReason.SIDEREAL_ZODIAC_REQUIRED


def test_internal_errors_leak_nothing() -> None:
    class Broken:
        def calculate(self, request: object) -> object:
            raise RuntimeError("secret 28.6139 Asia/Kolkata")

    facts = CompatibilityService(Broken()).match(request())  # type: ignore[arg-type]
    assert facts.status is MatchStatus.INTERNAL_ERROR
    assert "28.6139" not in facts.model_dump_json() and "secret" not in facts.model_dump_json()


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------


@pytest.mark.parametrize("profile", [AK, TP])
def test_results_are_partial_and_carry_methodology(profile: CompatibilityProfileId) -> None:
    facts = SERVICE.match(request(profile=profile))
    assert facts.status is MatchStatus.PARTIAL
    assert facts.methodology_version == "1.0.0" and facts.standards_version == "1.25.0"
    assert facts.provenance and facts.unresolved_choices and facts.not_implemented
    assert facts.system.value in ("NORTH_INDIAN_ASHTAKOOT", "SOUTH_INDIAN_TEN_PORUTHAM")
    assert any("verdict" in note for note in facts.notes)
    if profile is AK:
        assert facts.ashtakoot_total is not None and facts.ashtakoot_total.points is None
        assert facts.porutham_summary is None
    else:
        assert facts.porutham_summary is not None and facts.ashtakoot_total is None


def test_placements_match_the_phase5_kundli() -> None:
    facts = SERVICE.match(request())
    kundli = KundliCalculationService().calculate(
        AstronomicalCalculationRequest(local_datetime=person().local_datetime, location=DELHI)
    )
    moon = next(p for p in kundli.planets if p.body.value == "moon")
    assert facts.placements[0].nakshatra is moon.nakshatra.nakshatra
    assert facts.placements[0].pada == moon.nakshatra.pada
    assert facts.placements[0].rashi is moon.rashi


def test_approximate_times() -> None:
    wide = BirthTimeInput(status=BirthTimeStatus.APPROXIMATE, uncertainty_seconds=12 * 3600)
    facts = SERVICE.match(request(person_b=person(1992, 11, 3, 21, birth_time=wide)))
    b = facts.placements[1]
    assert b.nakshatra is None and b.moon_longitude_low is not None
    tara = next(f for f in facts.factors if f.factor_id == "tara")
    assert tara.reason is FactorReason.MOON_POSITION_UNCERTAIN
    narrow = BirthTimeInput(status=BirthTimeStatus.APPROXIMATE, uncertainty_seconds=60)
    facts = SERVICE.match(request(person_b=person(1992, 11, 3, 21, birth_time=narrow)))
    assert facts.placements[1].nakshatra is not None
    missing = BirthTimeInput(status=BirthTimeStatus.APPROXIMATE)
    facts = SERVICE.match(request(person_b=person(1992, 11, 3, 21, birth_time=missing)))
    assert facts.placements[1].rashi is None


def test_unknown_birth_time_makes_every_factor_not_evaluable() -> None:
    unknown = BirthTimeInput(status=BirthTimeStatus.NOT_EVALUABLE)
    facts = SERVICE.match(request(person_a=person(birth_time=unknown)))
    assert facts.status is MatchStatus.NOT_EVALUABLE
    assert facts.reason is MatchReason.NO_FACTOR_EVALUABLE
    assert {f.reason for f in facts.factors} == {FactorReason.BIRTH_TIME_NOT_EVALUABLE}
    assert all(f.status is FactorStatus.NOT_EVALUABLE for f in facts.factors)


def test_deterministic_and_round_trips() -> None:
    first, second = SERVICE.match(request()), SERVICE.match(request())
    assert first == second
    assert CompatibilityFacts.model_validate_json(first.model_dump_json()) == first


def test_facts_contain_no_statement_of_effect() -> None:
    facts = SERVICE.match(request())
    dumped = " ".join(x.model_dump_json() for x in (*facts.factors, *facts.doshas)).lower()
    for word in ("widow", "death of", "will die", "incompatible", "is compatible"):
        assert word not in dumped
