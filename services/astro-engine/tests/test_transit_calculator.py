"""The pure transit calculator on synthetic motion: validation, the facts
contract, provenance and accuracy disclosure, windows, limits, Sade Sati and
serialization (docs/ASTROLOGY_STANDARDS.md TR-01 to TR-15)."""

from __future__ import annotations

import datetime as dt

import pytest
from transit_helpers import (
    JD0,
    T0,
    SyntheticProvider,
    config,
    days,
    linear,
    natal,
    sinusoid,
)

from pandit_astro_engine._version import __version__
from pandit_astro_engine.dashas.models import BirthTimeStatus
from pandit_astro_engine.models import (
    CalculationConfig,
    EphemerisMode,
    NodeConvention,
    ZodiacType,
)
from pandit_astro_engine.models import (
    CelestialBody as B,
)
from pandit_astro_engine.transits import (
    EventKind,
    NatalReference,
    TransitFacts,
    TransitReason,
    TransitRequest,
    TransitStatus,
    calculate_transit,
)
from pandit_astro_engine.transits import events as EV
from pandit_astro_engine.transits import profiles as P
from pandit_astro_engine.transits.models import SectionStatus

VERSION = "test-engine"


def run(request: TransitRequest, provider: SyntheticProvider | None = None) -> TransitFacts:
    return calculate_transit(
        request, provider or SyntheticProvider(), engine_version=VERSION, swisseph_version="test"
    )


def at(**cfg: object) -> TransitRequest:
    return TransitRequest(natal=natal(), config=config(**cfg), at_utc=T0)


def window(start: dt.datetime, end: dt.datetime, **cfg: object) -> TransitRequest:
    return TransitRequest(
        natal=natal(), config=config(**cfg), window_start_utc=start, window_end_utc=end
    )


def assert_failure(facts: TransitFacts, status: TransitStatus, reason: TransitReason) -> None:
    assert facts.status == status and facts.reason_code == reason
    assert facts.snapshot is None and facts.window is None and facts.sade_sati is None
    assert facts.natal is None and facts.accuracy is None and facts.provenance == ()
    assert facts.engine_version == VERSION


# --------------------------------------------------------------------------
# Validation and statuses
# --------------------------------------------------------------------------


def test_tropical_zodiac_is_a_configuration_error() -> None:
    calc = CalculationConfig(zodiac=ZodiacType.TROPICAL, ayanamsa=None)
    facts = run(at(calculation=calc))
    assert_failure(facts, TransitStatus.CONFIGURATION_ERROR, TransitReason.SIDEREAL_ZODIAC_REQUIRED)


@pytest.mark.parametrize(
    "overrides",
    [
        {"reference_profile_id": "TRANSIT_REF_LAGNA_SIGN"},
        {"reference_profile_id": "SOMETHING_ELSE"},
        {"vedha_profile_id": "GOCHARA_VEDHA_OTHER"},
        {"include_sade_sati": True, "sade_sati_profile_id": "DHAIYA_SIGN_BASED_MODERN_V1"},
        {"include_sade_sati": True, "sade_sati_profile_id": "ASHTAMA_SIGN_BASED_MODERN_V1"},
        {"include_sade_sati": True, "sade_sati_profile_id": "SADE_SATI_DEGREE_45_MODERN_V1"},
        {"include_sade_sati": True, "sade_sati_profile_id": "UNKNOWN"},
    ],
)
def test_unsupported_profiles_are_rejected_not_approximated(overrides: dict[str, object]) -> None:
    facts = run(at(**overrides))
    assert_failure(facts, TransitStatus.UNSUPPORTED_PROFILE, TransitReason.UNSUPPORTED_PROFILE)


def test_an_unused_profile_id_is_not_validated() -> None:
    assert run(at(vedha_profile_id="ANY", include_vedha=False)).status == TransitStatus.SUCCESS
    assert run(at(sade_sati_profile_id="ANY")).status == TransitStatus.SUCCESS


def test_no_bodies_is_invalid_input() -> None:
    assert_failure(run(at(bodies=())), TransitStatus.INVALID_INPUT, TransitReason.NO_BODIES)


def test_no_query_is_invalid_input() -> None:
    facts = run(TransitRequest(natal=natal(), config=config()))
    assert_failure(facts, TransitStatus.INVALID_INPUT, TransitReason.NO_QUERY)


def test_a_naive_instant_is_invalid_input() -> None:
    naive = dt.datetime(2024, 1, 1)
    facts = run(TransitRequest(natal=natal(), config=config(), at_utc=naive))
    assert_failure(facts, TransitStatus.INVALID_INPUT, TransitReason.INVALID_INSTANT)


def test_a_naive_window_bound_is_invalid_input() -> None:
    request = TransitRequest(
        natal=natal(),
        config=config(),
        window_start_utc=dt.datetime(2024, 1, 1),
        window_end_utc=T0 + days(10),
    )
    assert_failure(run(request), TransitStatus.INVALID_INPUT, TransitReason.INVALID_INSTANT)


def test_half_a_window_is_invalid() -> None:
    request = TransitRequest(natal=natal(), config=config(), window_start_utc=T0)
    assert_failure(run(request), TransitStatus.INVALID_INPUT, TransitReason.INVALID_WINDOW)


@pytest.mark.parametrize("end_offset", [0, -1])
def test_an_empty_or_reversed_window_is_invalid(end_offset: int) -> None:
    facts = run(window(T0, T0 + days(end_offset)))
    assert_failure(facts, TransitStatus.INVALID_INPUT, TransitReason.INVALID_WINDOW)


def test_non_finite_natal_longitudes_are_invalid_input() -> None:
    for bad in (float("nan"), float("inf")):
        ref = NatalReference(moon_longitude=bad)
        facts = run(TransitRequest(natal=ref, config=config(), at_utc=T0))
        assert_failure(facts, TransitStatus.INVALID_INPUT, TransitReason.NON_FINITE_LONGITUDE)
    ref = NatalReference(moon_longitude=1.0, natal_planets={B.SUN: float("nan")})
    facts = run(TransitRequest(natal=ref, config=config(), at_utc=T0))
    assert facts.reason_code == TransitReason.NON_FINITE_LONGITUDE


def test_an_inconsistent_natal_range_is_invalid_input() -> None:
    ref = NatalReference(
        precision=BirthTimeStatus.APPROXIMATE,
        moon_longitude=200.0,
        moon_longitude_low=61.0,
        moon_longitude_high=70.0,
    )
    facts = run(TransitRequest(natal=ref, config=config(), at_utc=T0))
    assert_failure(facts, TransitStatus.INVALID_INPUT, TransitReason.NATAL_RANGE_INCONSISTENT)


def test_a_window_longer_than_200_years_is_not_evaluable() -> None:
    limit = 200 * 365.2425
    too_big = window(T0, T0 + days(limit) + dt.timedelta(seconds=1), event_kinds=())
    assert_failure(run(too_big), TransitStatus.NOT_EVALUABLE, TransitReason.WINDOW_TOO_LARGE)


def test_a_window_of_exactly_200_years_is_allowed() -> None:
    exact = window(T0, T0 + days(200 * 365.2425), event_kinds=(), bodies=(B.SATURN,))
    assert run(exact).status == TransitStatus.SUCCESS


def test_more_than_the_event_limit_is_not_evaluable_with_no_partial_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(EV, "MAX_EVENTS", 2)
    provider = SyntheticProvider({B.SUN: linear(0.0, 1.0)})
    facts = run(window(T0, T0 + days(200), bodies=(B.SUN,)), provider)
    assert_failure(facts, TransitStatus.NOT_EVALUABLE, TransitReason.EVENT_LIMIT_EXCEEDED)


def test_a_failure_still_records_the_configuration_and_profile_ids() -> None:
    facts = run(at(bodies=()))
    assert facts.configuration.bodies == ()
    assert facts.profile_ids.boundary_profile_id == P.BOUNDARY_PROFILE_ID
    assert facts.standards_version == "1.6.0"


# --------------------------------------------------------------------------
# Successful contract, profile IDs, provenance, accuracy
# --------------------------------------------------------------------------


def test_success_records_versions_conventions_and_profile_ids() -> None:
    facts = run(at())
    assert facts.status == TransitStatus.SUCCESS and facts.reason_code is None
    assert facts.standards_version == "1.6.0" and facts.engine_version == VERSION
    assert facts.system_id == "transit_gochara" and facts.time_base == "utc"
    assert facts.boundary_convention == "half_open_start_inclusive_end_exclusive"
    ids = facts.profile_ids
    assert ids.reference_profile_id == P.REF_MOON_SIGN_ID
    assert ids.favourable_reading_ids == P.FAVOURABLE_READING_IDS
    assert ids.vedha_profile_id == P.VEDHA_PHALADEEPIKA_ID
    assert ids.contact_profile_id == P.CONTACT_PROFILE_ID
    assert ids.events_profile_id is None  # no window
    assert ids.lagna_profile_id is None and ids.sade_sati_profile_id is None


def test_profile_ids_follow_the_requested_features() -> None:
    facts = run(
        window(
            T0,
            T0 + days(10),
            include_lagna_fact=True,
            include_sade_sati=True,
            include_vedha=False,
            include_contacts=False,
        )
    )
    ids = facts.profile_ids
    assert ids.lagna_profile_id == P.REF_LAGNA_SIGN_ID
    assert ids.sade_sati_profile_id == P.SADE_SATI_ID
    assert ids.events_profile_id == P.EVENTS_PROFILE_ID
    assert ids.vedha_profile_id is None and ids.contact_profile_id is None


def test_provenance_labels_never_blur_source_derived_convention_and_modern_tradition() -> None:
    facts = run(window(T0, T0 + days(5), include_sade_sati=True, include_lagna_fact=True))
    label = {e.entry_id: e.evidence_label for e in facts.provenance}
    assert label["reference"] == P.EvidenceLabel.SOURCE_SUPPORTED
    assert label[f"favourable:{P.FAV_PHALADEEPIKA_ID}"] == P.EvidenceLabel.SOURCE_SUPPORTED
    assert label[f"favourable:{P.FAV_BPHS_DERIVED_ID}"] == P.EvidenceLabel.DERIVED_CALCULATION
    assert label["favourable_conflict"] == P.EvidenceLabel.UNRESOLVED_CONFLICT
    assert label["vedha"] == P.EvidenceLabel.SOURCE_SUPPORTED
    assert label["contacts"] == P.EvidenceLabel.ENGINEERING_CONVENTION
    assert label["events"] == P.EvidenceLabel.ENGINEERING_CONVENTION
    assert label["lagna"] == P.EvidenceLabel.ENGINEERING_CONVENTION
    assert label["sade_sati"] == P.EvidenceLabel.MODERN_TRADITION
    assert label["boundary"] == P.EvidenceLabel.ENGINEERING_CONVENTION
    assert label["accuracy"] == P.EvidenceLabel.ENGINEERING_EVIDENCE
    ids = [e.entry_id for e in facts.provenance]
    assert len(ids) == len(set(ids))


def test_vedha_provenance_says_single_source() -> None:
    facts = run(at())
    vedha = next(e for e in facts.provenance if e.entry_id == "vedha")
    assert "single" in vedha.statement.lower()
    assert vedha.references and vedha.references[0].verification_level == "IMAGE-TRANSLATION"


def test_sade_sati_provenance_denies_classical_certainty() -> None:
    facts = run(window(T0, T0 + days(5), include_sade_sati=True))
    entry = next(e for e in facts.provenance if e.entry_id == "sade_sati")
    assert "not found as a combined unit" in entry.statement
    assert facts.sade_sati is not None
    assert facts.sade_sati.evidence_label == P.EvidenceLabel.MODERN_TRADITION
    assert "not found as a combined unit" in facts.sade_sati.classical_status


def test_accuracy_block_never_claims_exactness() -> None:
    facts = run(at())
    accuracy = facts.accuracy
    assert accuracy is not None
    assert accuracy.instants_are_exact is False
    assert accuracy.ephemeris_modes == (EphemerisMode.MOSHIER,)
    assert accuracy.zodiac == "sidereal" and accuracy.ayanamsa == "lahiri"
    assert accuracy.node_convention == "mean"
    assert accuracy.search_tolerance_seconds == pytest.approx(0.000864, rel=1e-3)
    assert "ayanamsa" in accuracy.ayanamsa_sensitivity_note
    assert "UT1-UTC" in accuracy.time_scale_note
    assert "42-sample" in accuracy.engineering_evidence
    assert accuracy.evidence_label == P.EvidenceLabel.ENGINEERING_EVIDENCE


def test_moshier_use_is_a_warning_and_files_mode_is_not() -> None:
    assert "ephemeris_mode_moshier" in run(at()).warnings
    files = SyntheticProvider(mode=EphemerisMode.SWISS_EPHEMERIS_FILES)
    facts = run(at(), files)
    assert "ephemeris_mode_moshier" not in facts.warnings
    assert facts.accuracy is not None
    assert facts.accuracy.ephemeris_modes == (EphemerisMode.SWISS_EPHEMERIS_FILES,)


def test_true_node_selection_is_warned_and_recorded() -> None:
    calc = CalculationConfig(node_convention=NodeConvention.TRUE)
    facts = run(at(calculation=calc))
    assert "true_node_convention_selected" in facts.warnings
    assert facts.accuracy is not None and facts.accuracy.node_convention == "true"


def test_the_venus_wording_anomaly_is_surfaced_on_the_result() -> None:
    # Moon sign 0; Venus in house 2 (sign 1), which has a Vedha pair.
    provider = SyntheticProvider({B.VENUS: linear(45.0, 0.0)})
    request = TransitRequest(natal=natal(moon=1.0), config=config(), at_utc=T0)
    facts = run(request, provider)
    assert P.VENUS_VEDHA_ANOMALY_WARNING in facts.warnings


# --------------------------------------------------------------------------
# Natal handling
# --------------------------------------------------------------------------


def test_natal_summary_reports_what_was_and_was_not_resolved() -> None:
    facts = run(at())
    assert facts.natal is not None
    assert facts.natal.moon_sign_status == SectionStatus.AVAILABLE
    assert facts.natal.moon_sign is not None and facts.natal.moon_sign.value == "aries"
    assert facts.natal.natal_planet_count == 1


def test_an_ambiguous_natal_moon_still_yields_positions_and_events() -> None:
    ref = NatalReference(
        precision=BirthTimeStatus.APPROXIMATE, moon_longitude_low=29.0, moon_longitude_high=31.0
    )
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1)})
    request = TransitRequest(
        natal=ref,
        config=config(bodies=(B.SUN,), include_sade_sati=True),
        window_start_utc=T0,
        window_end_utc=T0 + days(20),
    )
    facts = run(request, provider)
    assert facts.status == TransitStatus.SUCCESS
    assert facts.natal is not None
    assert facts.natal.moon_sign_status == SectionStatus.NOT_EVALUABLE
    assert facts.natal.moon_sign_reason == TransitReason.NATAL_MOON_SIGN_AMBIGUOUS
    assert facts.window is not None and facts.window.event_count == 1
    assert facts.window.start_snapshot.moon_relative_status == SectionStatus.NOT_EVALUABLE
    assert facts.sade_sati is not None
    assert facts.sade_sati.status == SectionStatus.NOT_EVALUABLE
    assert facts.sade_sati.reason_code == TransitReason.NATAL_MOON_SIGN_AMBIGUOUS
    assert facts.sade_sati.segments == () and facts.sade_sati.episodes == ()


def test_an_unknown_natal_time_is_not_guessed() -> None:
    ref = NatalReference(precision=BirthTimeStatus.NOT_EVALUABLE)
    facts = run(TransitRequest(natal=ref, config=config(), at_utc=T0))
    assert facts.natal is not None
    assert facts.natal.moon_sign_reason == TransitReason.NATAL_TIME_UNKNOWN
    assert facts.snapshot is not None and facts.snapshot.favourable == ()


# --------------------------------------------------------------------------
# Windows and events
# --------------------------------------------------------------------------


def test_a_window_reports_start_state_events_and_count() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1), B.MARS: linear(100.0, 0.05)})
    facts = run(window(T0, T0 + days(20), bodies=(B.SUN, B.MARS)), provider)
    assert facts.window is not None
    win = facts.window
    assert win.event_count == len(win.events) == 1
    assert win.start_snapshot.at_utc == T0
    assert [s.body for s in win.start_snapshot.states] == [B.SUN, B.MARS]
    event = win.events[0]
    assert event.kind == EventKind.SIGN_INGRESS and event.body == B.SUN
    assert (event.from_value, event.to_value) == ("aries", "taurus")
    assert event.evidence_label == P.EvidenceLabel.ENGINEERING_CONVENTION


def test_event_instants_are_utc_and_match_their_julian_day() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1)})
    facts = run(window(T0, T0 + days(20), bodies=(B.SUN,)), provider)
    assert facts.window is not None
    event = facts.window.events[0]
    assert event.instant_utc.tzinfo is not None
    assert event.instant_utc.utcoffset() == dt.timedelta(0)
    assert abs((event.instant_utc - (T0 + days(5))).total_seconds()) < 0.01
    assert event.julian_day_ut == pytest.approx(JD0 + 5.0, abs=1e-7)
    assert event.event_id == f"TRN:SIGN_INGRESS:sun:{event.instant_utc.isoformat()}"


def test_events_can_be_requested_by_kind() -> None:
    provider = SyntheticProvider({B.SATURN: sinusoid(30.0, 1.0, 100.0)})
    only_stations = run(
        window(
            T0,
            T0 + days(200),
            bodies=(B.SATURN,),
            event_kinds=(EventKind.STATION_RETROGRADE, EventKind.STATION_DIRECT),
        ),
        provider,
    )
    assert only_stations.window is not None
    assert {e.kind for e in only_stations.window.events} <= {
        EventKind.STATION_RETROGRADE,
        EventKind.STATION_DIRECT,
    }
    none = run(window(T0, T0 + days(200), bodies=(B.SATURN,), event_kinds=()), provider)
    assert none.window is not None and none.window.events == ()
    assert none.profile_ids.events_profile_id is None


def test_nakshatra_ingress_is_opt_in() -> None:
    provider = SyntheticProvider({B.MOON: linear(13.0, 1.0)})
    default = run(window(T0, T0 + days(5), bodies=(B.MOON,)), provider)
    opted = run(
        window(T0, T0 + days(5), bodies=(B.MOON,), event_kinds=(EventKind.NAKSHATRA_INGRESS,)),
        provider,
    )
    assert default.window is not None and default.window.events == ()
    assert opted.window is not None and len(opted.window.events) == 1
    assert opted.window.events[0].from_value == "ashwini"
    assert opted.window.events[0].to_value == "bharani"
    assert opted.window.events[0].contacts_after == ()


def test_backward_motion_is_flagged_on_ingress_events() -> None:
    provider = SyntheticProvider({B.RAHU: linear(31.0, -0.5)})  # falls through 30 degrees
    facts = run(window(T0, T0 + days(10), bodies=(B.RAHU,)), provider)
    assert facts.window is not None
    (event,) = facts.window.events
    assert (event.from_value, event.to_value) == ("taurus", "aries")
    assert event.backward_motion is True and event.retrograde is True


def test_ingress_events_carry_the_contacts_holding_from_that_instant() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1)})
    ref = natal(moon=45.0, planets={B.JUPITER: 50.0})  # natal Moon and Jupiter in Taurus
    request = TransitRequest(
        natal=ref,
        config=config(bodies=(B.SUN,)),
        window_start_utc=T0,
        window_end_utc=T0 + days(20),
    )
    facts = run(request, provider)
    assert facts.window is not None
    (event,) = facts.window.events
    natal_bodies = {c.natal_body for c in event.contacts_after if c.kind.value == "conjunction"}
    assert natal_bodies == {B.MOON, B.JUPITER}


def test_ingress_contacts_are_absent_when_natal_planets_are_unknown() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1)})
    ref = NatalReference(precision=BirthTimeStatus.EXACT, moon_longitude=45.0)
    request = TransitRequest(
        natal=ref,
        config=config(bodies=(B.SUN,)),
        window_start_utc=T0,
        window_end_utc=T0 + days(20),
    )
    facts = run(request, provider)
    assert facts.window is not None and facts.window.events[0].contacts_after == ()
    assert facts.window.start_snapshot.contacts_status == SectionStatus.NOT_EVALUABLE


def test_a_snapshot_and_a_window_can_be_requested_together() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1)})
    request = TransitRequest(
        natal=natal(),
        config=config(bodies=(B.SUN,)),
        at_utc=T0 + days(1),
        window_start_utc=T0,
        window_end_utc=T0 + days(20),
    )
    facts = run(request, provider)
    assert facts.snapshot is not None and facts.window is not None
    assert facts.snapshot.at_utc == T0 + days(1)


def test_a_non_utc_aware_datetime_is_the_same_instant() -> None:
    ist = dt.timezone(dt.timedelta(hours=5, minutes=30))
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1)})
    utc_facts = run(
        TransitRequest(natal=natal(), config=config(bodies=(B.SUN,)), at_utc=T0), provider
    )
    ist_facts = run(
        TransitRequest(natal=natal(), config=config(bodies=(B.SUN,)), at_utc=T0.astimezone(ist)),
        provider,
    )
    assert utc_facts.snapshot is not None and ist_facts.snapshot is not None
    assert utc_facts.snapshot.julian_day_ut == ist_facts.snapshot.julian_day_ut
    assert utc_facts.snapshot.states == ist_facts.snapshot.states


# --------------------------------------------------------------------------
# Sade Sati integration on synthetic Saturn
# --------------------------------------------------------------------------


def test_sade_sati_over_a_window_uses_saturns_sign_timeline() -> None:
    # Saturn oscillates around 330 degrees (the Aquarius | Pisces boundary); natal Moon in Pisces.
    provider = SyntheticProvider({B.SATURN: sinusoid(330.0, 2.0, 400.0, drift=0.01)})
    ref = natal(moon=345.0)
    request = TransitRequest(
        natal=ref,
        config=config(bodies=(B.SATURN,), include_sade_sati=True, event_kinds=()),
        window_start_utc=T0,
        window_end_utc=T0 + days(1500),
    )
    facts = run(request, provider)
    sade = facts.sade_sati
    assert sade is not None and sade.status == SectionStatus.AVAILABLE
    assert sade.natal_moon_sign is not None and sade.natal_moon_sign.value == "pisces"
    assert [s.value for s in sade.band_signs] == ["aquarius", "pisces", "aries"]
    assert sade.segments and sade.episodes
    assert sade.profile_id == P.SADE_SATI_ID
    for segment in sade.segments:
        assert segment.sign.value in {"aquarius", "pisces", "aries"}
    # Episodes list only their own segments, in order, and cover every segment once.
    listed = [sid for ep in sade.episodes for sid in ep.segment_ids]
    assert listed == [s.segment_id for s in sade.segments]


def test_a_sade_sati_snapshot_state_is_reported_without_a_window() -> None:
    provider = SyntheticProvider({B.SATURN: linear(345.0, 0.0)})
    request = TransitRequest(
        natal=natal(moon=345.0), config=config(include_sade_sati=True), at_utc=T0
    )
    facts = run(request, provider)
    assert facts.snapshot is not None and facts.snapshot.sade_sati is not None
    assert facts.snapshot.sade_sati.in_band and facts.snapshot.sade_sati.phase == 2
    assert facts.sade_sati is None  # segments need a window


# --------------------------------------------------------------------------
# Determinism and serialization
# --------------------------------------------------------------------------


def test_identical_requests_give_identical_results() -> None:
    provider = SyntheticProvider({B.MERCURY: sinusoid(30.0, 4.0, 40.0, drift=0.3)})
    request = window(T0, T0 + days(300), bodies=(B.MERCURY,), include_sade_sati=True)
    first = run(request, provider)
    second = run(request, provider)
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()


def test_the_result_round_trips_through_json() -> None:
    provider = SyntheticProvider({B.SUN: linear(29.5, 0.1), B.SATURN: linear(330.0, 0.02)})
    facts = run(window(T0, T0 + days(60), include_sade_sati=True), provider)
    restored = TransitFacts.model_validate_json(facts.model_dump_json())
    assert restored == facts


def test_a_failure_round_trips_through_json_too() -> None:
    facts = run(at(bodies=()))
    assert TransitFacts.model_validate_json(facts.model_dump_json()) == facts


def test_a_success_must_not_carry_a_reason_and_a_failure_must() -> None:
    good = run(at())
    with pytest.raises(ValueError):
        TransitFacts.model_validate({**good.model_dump(), "reason_code": "no_query"})
    bad = run(at(bodies=()))
    with pytest.raises(ValueError):
        TransitFacts.model_validate({**bad.model_dump(), "reason_code": None})


def test_the_facts_contain_no_verdict_or_interpretation_vocabulary() -> None:
    facts = run(window(T0, T0 + days(10), include_sade_sati=True))
    text = facts.model_dump_json().lower()
    for word in ("auspicious", "inauspicious", "benefic", "malefic", "predict", "remedy", "career"):
        assert word not in text, word


def test_an_ingress_exactly_at_the_window_start_creates_no_spurious_sade_sati_segment() -> None:
    # Saturn stands on 330.0 (the Aquarius | Pisces boundary) at the window start, moving
    # forward: it is already in Pisces at the start. The ingress instant is only located to
    # within the solver tolerance, so it must not replay as an Aquarius segment.
    provider = SyntheticProvider({B.SATURN: linear(330.0, 0.05)})
    request = TransitRequest(
        natal=natal(moon=345.0),  # Pisces: band Aquarius, Pisces, Aries
        config=config(bodies=(B.SATURN,), include_sade_sati=True),
        window_start_utc=T0,
        window_end_utc=T0 + days(400),
    )
    facts = run(request, provider)
    assert facts.status == TransitStatus.SUCCESS
    assert facts.sade_sati is not None
    first = facts.sade_sati.segments[0]
    assert first.sign.value == "pisces" and first.clipped_at_window_start
    assert all(s.sign.value != "aquarius" for s in facts.sade_sati.segments)
    # The event itself is still reported once, at the start within the tolerance.
    assert facts.window is not None
    (event,) = [e for e in facts.window.events if e.kind == EventKind.SIGN_INGRESS][:1]
    assert 0.0 <= event.julian_day_ut - JD0 <= 1e-7


def test_the_start_state_and_the_first_event_agree_away_from_the_boundary() -> None:
    provider = SyntheticProvider({B.SATURN: linear(329.0, 0.05)})  # crosses 330 at day 20
    request = window(T0, T0 + days(100), bodies=(B.SATURN,))
    facts = run(request, provider)
    assert facts.window is not None
    start_state = facts.window.start_snapshot.states[0]
    assert start_state.sign.value == "aquarius"
    (event,) = facts.window.events
    assert event.from_value == "aquarius" and event.to_value == "pisces"


# --------------------------------------------------------------------------
# Failure mapping: nothing leaks as a stack trace
# --------------------------------------------------------------------------


class _RaisingProvider:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def position(self, julian_day_ut: float, body: B):  # type: ignore[no-untyped-def]
        raise self.error


def test_an_ephemeris_calculation_error_is_a_structured_not_evaluable() -> None:
    from pandit_astro_engine.errors import EphemerisCalculationError

    facts = run(at(), _RaisingProvider(EphemerisCalculationError("date out of range")))  # type: ignore[arg-type]
    assert_failure(facts, TransitStatus.NOT_EVALUABLE, TransitReason.EPHEMERIS_ERROR)
    assert facts.detail is not None and "out of range" in facts.detail


def test_missing_ephemeris_data_is_a_configuration_error() -> None:
    from pandit_astro_engine.errors import EphemerisDataUnavailableError

    facts = run(at(), _RaisingProvider(EphemerisDataUnavailableError(None)))  # type: ignore[arg-type]
    assert_failure(facts, TransitStatus.CONFIGURATION_ERROR, TransitReason.EPHEMERIS_UNAVAILABLE)


def test_an_inconsistent_sade_sati_chain_is_an_internal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pandit_astro_engine.transits import calculator
    from pandit_astro_engine.transits.sade_sati import InconsistentTimelineError

    def boom(*args: object, **kwargs: object) -> None:
        raise InconsistentTimelineError("ingress from 10, expected 11")

    monkeypatch.setattr(calculator, "build_sade_sati", boom)
    request = window(T0, T0 + days(10), include_sade_sati=True)
    facts = run(request)
    assert_failure(facts, TransitStatus.INTERNAL_ERROR, TransitReason.INTERNAL_ERROR)


def test_the_service_never_leaks_an_unexpected_exception() -> None:
    from pandit_astro_engine.transits import TransitCalculationService

    service = TransitCalculationService(_RaisingProvider(RuntimeError("boom")))  # type: ignore[arg-type]
    facts = service.calculate(at())
    assert facts.status == TransitStatus.INTERNAL_ERROR
    assert facts.reason_code == TransitReason.INTERNAL_ERROR
    assert facts.snapshot is None and facts.window is None
    assert facts.detail is None  # no stack trace, no message
    assert facts.engine_version == __version__


def test_the_node_id_map_matches_the_supported_conventions() -> None:
    from pandit_astro_engine import ephemeris

    assert set(ephemeris.SWE_NODE_ID) == {c.value for c in NodeConvention}
