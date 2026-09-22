"""Ashtakavarga service tests (Phase 9 WP-A1): validation, statuses, the four
profiles all agreeing on their input contract, `from_kundli`, determinism
and JSON round trip."""

from __future__ import annotations

import math

from pandit_astro_engine.ashtakavarga.constants import CONTRIBUTOR_ORDER, Contributor
from pandit_astro_engine.ashtakavarga.models import (
    AshtakavargaReason,
    AshtakavargaRequest,
    AshtakavargaStatus,
    NatalPositions,
)
from pandit_astro_engine.ashtakavarga.profiles import (
    ALL_PROFILE_IDS,
    BPHS_GRID_ID,
    BPHS_VERSE_ID,
    BRIHAT_JATAKA_ID,
    PHALADEEPIKA_ID,
)
from pandit_astro_engine.ashtakavarga.service import AshtakavargaCalculationService
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    LocalDateTimeInput,
    Location,
)

_DELHI = Location(latitude=28.6139, longitude=77.2090, altitude_meters=216)

_FULL_NATAL = {c: float(i * 41) for i, c in enumerate(CONTRIBUTOR_ORDER)}


def _service() -> AshtakavargaCalculationService:
    return AshtakavargaCalculationService()


def test_unknown_profile_id_is_unsupported_profile() -> None:
    request = AshtakavargaRequest(
        natal=NatalPositions(longitudes=_FULL_NATAL), profile_id="NOT_A_REAL_PROFILE"
    )
    facts = _service().calculate(request)
    assert facts.status == AshtakavargaStatus.UNSUPPORTED_PROFILE
    assert facts.reason_code == AshtakavargaReason.UNSUPPORTED_PROFILE
    assert facts.charts == ()


def test_missing_lagna_is_not_evaluable() -> None:
    incomplete = {c: v for c, v in _FULL_NATAL.items() if c != Contributor.LAGNA}
    request = AshtakavargaRequest(
        natal=NatalPositions(longitudes=incomplete), profile_id=BRIHAT_JATAKA_ID
    )
    facts = _service().calculate(request)
    assert facts.status == AshtakavargaStatus.NOT_EVALUABLE
    assert facts.reason_code == AshtakavargaReason.LAGNA_UNAVAILABLE
    assert facts.charts == ()


def test_missing_planet_is_not_evaluable_incomplete() -> None:
    incomplete = {c: v for c, v in _FULL_NATAL.items() if c != Contributor.SATURN}
    request = AshtakavargaRequest(
        natal=NatalPositions(longitudes=incomplete), profile_id=BRIHAT_JATAKA_ID
    )
    facts = _service().calculate(request)
    assert facts.status == AshtakavargaStatus.NOT_EVALUABLE
    assert facts.reason_code == AshtakavargaReason.NATAL_POSITIONS_INCOMPLETE


def test_non_finite_longitude_is_invalid_input() -> None:
    bad = dict(_FULL_NATAL)
    bad[Contributor.MOON] = math.nan
    request = AshtakavargaRequest(natal=NatalPositions(longitudes=bad), profile_id=BPHS_GRID_ID)
    facts = _service().calculate(request)
    assert facts.status == AshtakavargaStatus.INVALID_INPUT
    assert facts.reason_code == AshtakavargaReason.NON_FINITE_LONGITUDE


def test_every_profile_succeeds_on_a_complete_natal_chart() -> None:
    for profile_id in ALL_PROFILE_IDS:
        request = AshtakavargaRequest(
            natal=NatalPositions(longitudes=_FULL_NATAL), profile_id=profile_id
        )
        facts = _service().calculate(request)
        assert facts.status == AshtakavargaStatus.SUCCESS, profile_id
        assert facts.reason_code is None
        assert len(facts.charts) == 7
        assert facts.sarva is not None
        assert facts.profile is not None and facts.profile.profile_id == profile_id


def test_lagna_chart_only_present_for_bphs_profiles() -> None:
    for profile_id in (BRIHAT_JATAKA_ID, PHALADEEPIKA_ID):
        request = AshtakavargaRequest(
            natal=NatalPositions(longitudes=_FULL_NATAL), profile_id=profile_id
        )
        facts = _service().calculate(request)
        assert facts.lagna_chart is None
    for profile_id in (BPHS_GRID_ID, BPHS_VERSE_ID):
        request = AshtakavargaRequest(
            natal=NatalPositions(longitudes=_FULL_NATAL), profile_id=profile_id
        )
        facts = _service().calculate(request)
        assert facts.lagna_chart is not None


def test_result_is_deterministic() -> None:
    request = AshtakavargaRequest(
        natal=NatalPositions(longitudes=_FULL_NATAL), profile_id=BRIHAT_JATAKA_ID
    )
    service = _service()
    first = service.calculate(request)
    second = service.calculate(request)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_json_round_trip() -> None:
    request = AshtakavargaRequest(
        natal=NatalPositions(longitudes=_FULL_NATAL), profile_id=BPHS_VERSE_ID
    )
    facts = _service().calculate(request)
    dumped = facts.model_dump(mode="json")
    restored = type(facts).model_validate(dumped)
    assert restored == facts


def test_from_kundli_populates_all_eight_contributors() -> None:
    kundli_request = AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=1990, month=6, day=15, hour=10, minute=30, timezone="Asia/Kolkata"
        ),
        location=_DELHI,
        include_solar_events=False,
    )
    kundli = KundliCalculationService().calculate(kundli_request)
    natal = NatalPositions.from_kundli(kundli)
    for contributor in CONTRIBUTOR_ORDER:
        assert contributor in natal.longitudes
    request = AshtakavargaCalculationService.from_kundli_request(kundli, BRIHAT_JATAKA_ID)
    facts = _service().calculate(request)
    assert facts.status == AshtakavargaStatus.SUCCESS
