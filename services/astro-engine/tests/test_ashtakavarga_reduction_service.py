"""Service-level tests for the WP-A2/A3 reduction request path: profile
scoping, validation, the full worked example end to end, determinism, JSON
round trip, and `from_kundli_reduction_request`."""

from __future__ import annotations

import math

from ashtakavarga_helpers import load_reduction_pinda_worked_example, natal_longitudes

from pandit_astro_engine.ashtakavarga.constants import Contributor
from pandit_astro_engine.ashtakavarga.models import (
    AshtakavargaReason,
    AshtakavargaReductionRequest,
    AshtakavargaStatus,
    GrahaPindaStatus,
    NatalPositions,
)
from pandit_astro_engine.ashtakavarga.profiles import (
    BPHS_GRID_ID,
    BPHS_VERSE_ID,
    BRIHAT_JATAKA_ID,
    PHALADEEPIKA_ID,
)
from pandit_astro_engine.ashtakavarga.service import AshtakavargaCalculationService
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.models import AstronomicalCalculationRequest, LocalDateTimeInput, Location
from pandit_astro_engine.rashi import Rashi

_DELHI = Location(latitude=28.6139, longitude=77.2090, altitude_meters=216)
_FULL_NATAL = {c: float(i * 41) for i, c in enumerate(Contributor)}


def _service() -> AshtakavargaCalculationService:
    return AshtakavargaCalculationService()


def _example_request() -> AshtakavargaReductionRequest:
    example = load_reduction_pinda_worked_example()
    natal = natal_longitudes(example["natal_longitudes_degrees"])
    return AshtakavargaReductionRequest(
        natal=NatalPositions(
            longitudes=natal,
            rahu_longitude=example["rahu_longitude_degrees"],
            ketu_longitude=example["ketu_longitude_degrees"],
        ),
        profile_id=example["profile_id"],
    )


def test_brihat_jataka_and_phaladeepika_have_no_reduction() -> None:
    for profile_id in (BRIHAT_JATAKA_ID, PHALADEEPIKA_ID):
        request = AshtakavargaReductionRequest(
            natal=NatalPositions(longitudes=_FULL_NATAL, rahu_longitude=10.0, ketu_longitude=190.0),
            profile_id=profile_id,
        )
        facts = _service().calculate_reductions(request)
        assert facts.status == AshtakavargaStatus.NOT_EVALUABLE
        assert facts.reason_code == AshtakavargaReason.REDUCTION_UNSUPPORTED_FOR_PROFILE
        assert facts.charts == ()


def test_unknown_profile_is_unsupported() -> None:
    request = AshtakavargaReductionRequest(
        natal=NatalPositions(longitudes=_FULL_NATAL, rahu_longitude=10.0, ketu_longitude=190.0),
        profile_id="NOT_REAL",
    )
    facts = _service().calculate_reductions(request)
    assert facts.status == AshtakavargaStatus.UNSUPPORTED_PROFILE
    assert facts.reason_code == AshtakavargaReason.UNSUPPORTED_PROFILE


def test_missing_node_positions_is_not_evaluable() -> None:
    for profile_id in (BPHS_GRID_ID, BPHS_VERSE_ID):
        request = AshtakavargaReductionRequest(
            natal=NatalPositions(longitudes=_FULL_NATAL), profile_id=profile_id
        )
        facts = _service().calculate_reductions(request)
        assert facts.status == AshtakavargaStatus.NOT_EVALUABLE
        assert facts.reason_code == AshtakavargaReason.NODE_POSITIONS_REQUIRED


def test_missing_lagna_is_not_evaluable() -> None:
    incomplete = {c: v for c, v in _FULL_NATAL.items() if c != Contributor.LAGNA}
    request = AshtakavargaReductionRequest(
        natal=NatalPositions(longitudes=incomplete, rahu_longitude=10.0, ketu_longitude=190.0),
        profile_id=BPHS_GRID_ID,
    )
    facts = _service().calculate_reductions(request)
    assert facts.status == AshtakavargaStatus.NOT_EVALUABLE
    assert facts.reason_code == AshtakavargaReason.LAGNA_UNAVAILABLE


def test_non_finite_node_longitude_is_invalid_input() -> None:
    request = AshtakavargaReductionRequest(
        natal=NatalPositions(longitudes=_FULL_NATAL, rahu_longitude=math.nan, ketu_longitude=190.0),
        profile_id=BPHS_GRID_ID,
    )
    facts = _service().calculate_reductions(request)
    assert facts.status == AshtakavargaStatus.INVALID_INPUT
    assert facts.reason_code == AshtakavargaReason.NON_FINITE_LONGITUDE


def test_worked_example_end_to_end_via_the_service() -> None:
    example = load_reduction_pinda_worked_example()
    facts = _service().calculate_reductions(_example_request())
    assert facts.status == AshtakavargaStatus.SUCCESS
    sun_reduction = next(c for c in facts.charts if c.chart == Contributor.SUN)
    for sign_name, expected in example["expected_trikona_corrected"].items():
        assert sun_reduction.trikona_corrected[Rashi(sign_name)] == expected
    for sign_name, expected in example["expected_ekadhipatya_corrected"].items():
        assert sun_reduction.ekadhipatya_corrected[Rashi(sign_name)] == expected

    sun_pinda = next(p for p in facts.pinda if p.chart == Contributor.SUN)
    assert sun_pinda.rasi_pinda == example["expected_rasi_pinda"] == 100
    assert sun_pinda.graha_pinda_status == GrahaPindaStatus.AVAILABLE
    assert sun_pinda.graha_pinda == example["expected_graha_pinda"] == 48
    assert sun_pinda.yoga_pinda == example["expected_yoga_pinda"] == 148

    nonzero = {
        (
            c.sign.value,
            c.occupying_contributor.value if c.occupying_contributor else None,
            c.multiplier,
            c.product,
        )
        for c in sun_pinda.graha_contributions
        if c.product
    }
    expected_nonzero = {
        (c["sign"], c["occupying_contributor"], c["multiplier"], c["product"])
        for c in example["expected_graha_pinda_nonzero_contributions"]
    }
    assert nonzero == expected_nonzero

    # The Ascendant's own BPHS chart goes through the identical pipeline --
    # and, for this natal chart, genuinely hits the equal-value/one-occupied
    # conflict itself (Scorpio, occupied by Saturn, and Aries, empty, both
    # Trikona-corrected to 2), so its own Ekadhipatya, Rasi, Graha and Yoga
    # Pinda are all correctly withheld rather than silently computed.
    assert facts.lagna_chart is not None
    assert facts.lagna_chart.status == AshtakavargaStatus.NOT_EVALUABLE
    assert facts.lagna_chart.reason_code == AshtakavargaReason.EKADHIPATYA_EQUAL_VALUE_CONFLICT
    assert facts.lagna_chart.ekadhipatya_corrected is None
    conflict_signs = {
        (c.occupied_sign.value, c.empty_sign.value) for c in facts.lagna_chart.ekadhipatya_conflicts
    }
    assert ("scorpio", "aries") in conflict_signs

    assert facts.lagna_pinda is not None
    assert facts.lagna_pinda.status == AshtakavargaStatus.NOT_EVALUABLE
    assert facts.lagna_pinda.reason_code == AshtakavargaReason.EKADHIPATYA_EQUAL_VALUE_CONFLICT
    assert facts.lagna_pinda.rasi_pinda is None
    assert facts.lagna_pinda.graha_pinda is None
    assert facts.lagna_pinda.yoga_pinda is None


def test_result_is_deterministic() -> None:
    service = _service()
    request = _example_request()
    first = service.calculate_reductions(request)
    second = service.calculate_reductions(request)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_json_round_trip() -> None:
    facts = _service().calculate_reductions(_example_request())
    dumped = facts.model_dump(mode="json")
    restored = type(facts).model_validate(dumped)
    assert restored == facts


def test_wp_a1_facts_are_unaffected_by_the_reduction_path() -> None:
    """Backward compatibility: the plain WP-A1 request/response pair is
    untouched by anything added for WP-A2/A3."""
    from pandit_astro_engine.ashtakavarga.models import AshtakavargaRequest

    request = AshtakavargaRequest(
        natal=NatalPositions(longitudes=_FULL_NATAL), profile_id=BPHS_GRID_ID
    )
    facts = _service().calculate(request)
    assert facts.status == AshtakavargaStatus.SUCCESS
    assert not hasattr(facts, "pinda")
    assert not hasattr(facts, "lagna_pinda")


def test_from_kundli_reduction_request_populates_nodes() -> None:
    kundli_request = AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=1990, month=6, day=15, hour=10, minute=30, timezone="Asia/Kolkata"
        ),
        location=_DELHI,
        include_solar_events=False,
    )
    kundli = KundliCalculationService().calculate(kundli_request)
    request = AshtakavargaCalculationService.from_kundli_reduction_request(kundli, BPHS_GRID_ID)
    assert request.natal.rahu_longitude is not None
    assert request.natal.ketu_longitude is not None
    facts = _service().calculate_reductions(request)
    assert facts.status == AshtakavargaStatus.SUCCESS
