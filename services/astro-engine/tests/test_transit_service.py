"""`TransitCalculationService` with the real Swiss-backed provider: UTC and time
zones, nodes, historical and future dates, Sade Sati on Saturn's real motion,
determinism and invariants (docs/ASTROLOGY_STANDARDS.md TR-02 to TR-13).

Published ingress and station *dates* (Tier 5 pages) are used only at date
level: published times disagree by hours between sources (TR-10)."""

from __future__ import annotations

import datetime as dt
import random
import time
from zoneinfo import ZoneInfo

import pytest
from transit_helpers import natal

from pandit_astro_engine import ephemeris
from pandit_astro_engine.dashas.models import BirthTimeStatus
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CalculationConfig,
    EphemerisMode,
    LocalDateTimeInput,
    Location,
    NodeConvention,
    ZodiacType,
)
from pandit_astro_engine.models import (
    CelestialBody as B,
)
from pandit_astro_engine.transits import (
    EventKind,
    NatalReference,
    SwissPositionProvider,
    TransitCalculationService,
    TransitConfiguration,
    TransitFacts,
    TransitReason,
    TransitStatus,
)
from pandit_astro_engine.transits.constants import SEARCH_TOLERANCE_DAYS
from pandit_astro_engine.transits.models import SectionStatus
from pandit_astro_engine.transits.positions import datetime_to_jd, jd_to_datetime

UTC = dt.timezone.utc
SERVICE = TransitCalculationService()
INGRESS = (EventKind.SIGN_INGRESS,)
STATIONS = (EventKind.STATION_RETROGRADE, EventKind.STATION_DIRECT)


def utc(year: int, month: int = 1, day: int = 1, hour: int = 0) -> dt.datetime:
    return dt.datetime(year, month, day, hour, tzinfo=UTC)


@pytest.fixture(scope="module")
def independence_natal() -> NatalReference:
    request = AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=1947, month=8, day=15, hour=0, minute=0, timezone="Asia/Kolkata"
        ),
        location=Location(latitude=28.6139, longitude=77.2090, altitude_meters=216),
        include_solar_events=False,
    )
    return NatalReference.from_kundli(KundliCalculationService().calculate(request))


# --------------------------------------------------------------------------
# Time conversion
# --------------------------------------------------------------------------


def test_julian_day_round_trip_is_microsecond_accurate() -> None:
    rng = random.Random(8)
    for _ in range(200):
        instant = utc(rng.randint(1900, 2100), rng.randint(1, 12), rng.randint(1, 28)) + (
            dt.timedelta(microseconds=rng.randint(0, 86_400_000_000))
        )
        back = jd_to_datetime(datetime_to_jd(instant))
        assert abs((back - instant).total_seconds()) < 1e-4


def test_the_time_zone_of_the_instant_does_not_change_the_result() -> None:
    ny = ZoneInfo("America/New_York")
    summer_local = dt.datetime(2025, 7, 1, 12, 0, tzinfo=ny)  # EDT, UTC-4
    winter_local = dt.datetime(2025, 1, 1, 12, 0, tzinfo=ny)  # EST, UTC-5
    assert summer_local.astimezone(UTC).hour == 16 and winter_local.astimezone(UTC).hour == 17
    for local in (summer_local, winter_local):
        via_local = SERVICE.snapshot(natal(), local)
        via_utc = SERVICE.snapshot(natal(), local.astimezone(UTC))
        assert via_local.snapshot is not None and via_utc.snapshot is not None
        assert via_local.snapshot.julian_day_ut == via_utc.snapshot.julian_day_ut
        assert via_local.snapshot.states == via_utc.snapshot.states


def test_an_hour_of_dst_shift_moves_the_moon_by_a_measurable_amount() -> None:
    # 12:00 local on either side of the DST change are different UTC instants: not the same state.
    ny = ZoneInfo("America/New_York")
    a = SERVICE.snapshot(natal(), dt.datetime(2025, 3, 8, 12, tzinfo=ny))
    b = SERVICE.snapshot(natal(), dt.datetime(2025, 3, 9, 12, tzinfo=ny))
    assert a.snapshot is not None and b.snapshot is not None
    moon_a = next(s for s in a.snapshot.states if s.body == B.MOON)
    moon_b = next(s for s in b.snapshot.states if s.body == B.MOON)
    assert 11.0 < (moon_b.longitude - moon_a.longitude) % 360.0 < 15.0
    assert (b.snapshot.julian_day_ut - a.snapshot.julian_day_ut) == pytest.approx(
        23.0 / 24.0, abs=1e-6
    )  # 23 real hours: the day the clocks moved forward


# --------------------------------------------------------------------------
# Snapshots on the real ephemeris
# --------------------------------------------------------------------------


def test_snapshot_of_the_independence_chart_is_complete_and_consistent(
    independence_natal: NatalReference,
) -> None:
    facts = SERVICE.snapshot(independence_natal, utc(2026, 9, 21, 12))
    assert facts.status == TransitStatus.SUCCESS
    assert facts.natal is not None and facts.natal.moon_sign is not None
    assert facts.natal.moon_sign.value == "cancer"  # the Phase 5 golden case
    snapshot = facts.snapshot
    assert snapshot is not None
    assert [s.body for s in snapshot.states] == list(B)
    assert snapshot.moon_relative_status == SectionStatus.AVAILABLE
    for state in snapshot.states:
        assert 0.0 <= state.longitude < 360.0
        assert state.house_from_moon is not None and 1 <= state.house_from_moon <= 12
        assert state.retrograde == (state.speed_longitude < 0.0)
        assert state.ephemeris_mode in EphemerisMode
    assert len(snapshot.favourable) == 9
    assert snapshot.contacts_status == SectionStatus.AVAILABLE
    assert facts.snapshot is not None and facts.window is None


def test_the_natal_moon_transiting_its_own_sign_is_house_one(
    independence_natal: NatalReference,
) -> None:
    assert independence_natal.moon_longitude is not None
    # The transiting Moon returns to the natal Moon's sign roughly every 27.3 days.
    first = utc(2026, 9, 1)
    houses = []
    for day in range(0, 30):
        facts = SERVICE.snapshot(independence_natal, first + dt.timedelta(days=day))
        assert facts.snapshot is not None
        houses.append(next(s for s in facts.snapshot.states if s.body == B.MOON).house_from_moon)
    assert 1 in houses and houses.count(1) in (2, 3)  # about 2.3 days in the sign
    assert set(houses) == set(range(1, 13))


@pytest.mark.parametrize("year", [1900, 1947, 2000, 2100])
def test_historical_and_future_instants_succeed(year: int) -> None:
    facts = SERVICE.snapshot(natal(), utc(year, 6, 15, 6))
    assert facts.status == TransitStatus.SUCCESS
    assert facts.snapshot is not None and len(facts.snapshot.states) == 9


def test_mean_node_is_always_retrograde_and_ketu_is_opposite() -> None:
    rng = random.Random(3)
    for _ in range(40):
        instant = utc(rng.randint(1900, 2100), rng.randint(1, 12), rng.randint(1, 28))
        facts = SERVICE.snapshot(natal(), instant)
        assert facts.snapshot is not None
        rahu = next(s for s in facts.snapshot.states if s.body == B.RAHU)
        ketu = next(s for s in facts.snapshot.states if s.body == B.KETU)
        assert rahu.retrograde and ketu.retrograde
        assert (ketu.longitude - rahu.longitude) % 360.0 == pytest.approx(180.0, abs=1e-9)
        assert ketu.speed_longitude == rahu.speed_longitude


def test_true_node_is_an_explicit_alternate_and_never_silently_mixed() -> None:
    mean = SERVICE.snapshot(natal(), utc(2025, 3, 1))
    true = SERVICE.snapshot(
        natal(),
        utc(2025, 3, 1),
        TransitConfiguration(calculation=CalculationConfig(node_convention=NodeConvention.TRUE)),
    )
    assert mean.snapshot is not None and true.snapshot is not None
    mean_rahu = next(s for s in mean.snapshot.states if s.body == B.RAHU)
    true_rahu = next(s for s in true.snapshot.states if s.body == B.RAHU)
    assert mean_rahu.longitude != true_rahu.longitude
    assert "true_node_convention_selected" in true.warnings
    assert "true_node_convention_selected" not in mean.warnings


def test_tropical_zodiac_is_refused_by_the_service() -> None:
    calc = CalculationConfig(zodiac=ZodiacType.TROPICAL, ayanamsa=None)
    facts = SERVICE.snapshot(natal(), utc(2025, 1, 1), TransitConfiguration(calculation=calc))
    assert facts.status == TransitStatus.CONFIGURATION_ERROR
    assert facts.reason_code == TransitReason.SIDEREAL_ZODIAC_REQUIRED


def test_the_swiss_provider_refuses_the_tropical_zodiac_directly() -> None:
    with pytest.raises(ValueError):
        SwissPositionProvider(CalculationConfig(zodiac=ZodiacType.TROPICAL, ayanamsa=None))


@pytest.mark.skipif(
    ephemeris.configured_ephemeris_path() is not None, reason="ephemeris files are configured"
)
def test_moshier_fallback_can_be_forbidden() -> None:
    calc = CalculationConfig(allow_moshier_fallback=False)
    facts = SERVICE.snapshot(natal(), utc(2025, 1, 1), TransitConfiguration(calculation=calc))
    assert facts.status == TransitStatus.CONFIGURATION_ERROR
    assert facts.reason_code == TransitReason.EPHEMERIS_UNAVAILABLE


def test_the_result_records_the_swiss_version_and_the_mode() -> None:
    facts = SERVICE.snapshot(natal(), utc(2025, 1, 1))
    assert facts.swisseph_version == ephemeris.swisseph_version()
    assert facts.accuracy is not None
    assert facts.accuracy.instants_are_exact is False
    assert facts.accuracy.ephemeris_modes
    assert facts.accuracy.ayanamsa == "lahiri"


def test_a_snapshot_is_deterministic() -> None:
    first = SERVICE.snapshot(natal(), utc(2025, 5, 5, 5))
    second = SERVICE.snapshot(natal(), utc(2025, 5, 5, 5))
    assert first == second and first.model_dump_json() == second.model_dump_json()


def test_the_result_round_trips_through_json_on_real_data(
    independence_natal: NatalReference,
) -> None:
    facts = SERVICE.events(
        independence_natal,
        utc(2025, 1, 1),
        utc(2026, 1, 1),
        TransitConfiguration(bodies=(B.SATURN, B.JUPITER), include_sade_sati=True),
    )
    assert TransitFacts.model_validate_json(facts.model_dump_json()) == facts


# --------------------------------------------------------------------------
# Saturn's real ingresses and stations (date level only)
# --------------------------------------------------------------------------


def test_saturn_sign_ingresses_2019_to_2026_match_the_published_dates() -> None:
    facts = SERVICE.events(
        natal(),
        utc(2019, 6, 1),
        utc(2026, 1, 1),
        TransitConfiguration(bodies=(B.SATURN,), event_kinds=INGRESS),
    )
    assert facts.window is not None
    got = [(e.instant_utc.date(), e.from_value, e.to_value) for e in facts.window.events]
    assert got == [
        (dt.date(2020, 1, 24), "sagittarius", "capricorn"),
        (dt.date(2022, 4, 29), "capricorn", "aquarius"),
        (dt.date(2022, 7, 12), "aquarius", "capricorn"),  # retrograde re-entry
        (dt.date(2023, 1, 17), "capricorn", "aquarius"),
        (dt.date(2025, 3, 29), "aquarius", "pisces"),
    ]
    backward = [e.backward_motion for e in facts.window.events]
    assert backward == [False, False, True, False, False]


def test_saturn_stations_in_2025_match_the_published_dates() -> None:
    facts = SERVICE.events(
        natal(),
        utc(2025, 1, 1),
        utc(2026, 1, 1),
        TransitConfiguration(bodies=(B.SATURN,), event_kinds=STATIONS),
    )
    assert facts.window is not None
    got = [(e.kind, e.instant_utc.date()) for e in facts.window.events]
    assert got == [
        (EventKind.STATION_RETROGRADE, dt.date(2025, 7, 13)),
        (EventKind.STATION_DIRECT, dt.date(2025, 11, 28)),
    ]
    assert all(abs(e.speed_longitude) < 1e-5 for e in facts.window.events)


def test_the_state_before_and_after_a_real_ingress_differs_by_exactly_one_sign() -> None:
    facts = SERVICE.events(
        natal(),
        utc(2025, 3, 1),
        utc(2025, 5, 1),
        TransitConfiguration(bodies=(B.SATURN,), event_kinds=INGRESS),
    )
    assert facts.window is not None
    (event,) = facts.window.events
    for delta, sign in ((-SEARCH_TOLERANCE_DAYS * 3, "aquarius"), (0.0, "pisces")):
        moment = jd_to_datetime(event.julian_day_ut + delta)
        state = SERVICE.snapshot(natal(), moment, TransitConfiguration(bodies=(B.SATURN,)))
        assert state.snapshot is not None
        assert state.snapshot.states[0].sign.value == sign


# --------------------------------------------------------------------------
# Sade Sati on real motion (MODERN_TRADITION)
# --------------------------------------------------------------------------


def test_sade_sati_for_a_pisces_moon_over_2020_to_2035() -> None:
    ref = natal(moon=340.5)  # Pisces: band Aquarius (12th), Pisces (1st), Aries (2nd)
    facts = SERVICE.sade_sati(ref, utc(2020, 1, 1), utc(2035, 1, 1))
    assert facts.status == TransitStatus.SUCCESS
    sade = facts.sade_sati
    assert sade is not None and sade.status == SectionStatus.AVAILABLE
    assert sade.evidence_label.value == "modern_tradition"
    assert [s.value for s in sade.band_signs] == ["aquarius", "pisces", "aries"]
    starts = [s.start_utc.date() for s in sade.segments if s.start_utc is not None]
    assert starts == [
        dt.date(2022, 4, 29),
        dt.date(2023, 1, 17),
        dt.date(2025, 3, 29),
        dt.date(2027, 6, 2),
        dt.date(2027, 10, 20),
        dt.date(2028, 2, 23),
        dt.date(2029, 10, 5),
    ]
    assert len(sade.episodes) == 3
    flags = [e.retrograde_reentry_of_previous_episode for e in sade.episodes]
    assert flags == [False, True, True]  # 2023 (exit backward) and 2029 (entered backward)
    assert sade.episodes[1].ended_by_backward_motion is False
    assert sade.episodes[2].entered_by_backward_motion is True


def test_sade_sati_segments_tile_within_each_real_episode() -> None:
    facts = SERVICE.sade_sati(natal(moon=340.5), utc(2000, 1, 1), utc(2060, 1, 1))
    assert facts.sade_sati is not None
    by_id = {s.segment_id: s for s in facts.sade_sati.segments}
    for episode in facts.sade_sati.episodes:
        run = [by_id[i] for i in episode.segment_ids]
        for left, right in zip(run, run[1:], strict=False):
            assert left.end_utc == right.start_utc
        assert episode.start_utc == run[0].start_utc and episode.end_utc == run[-1].end_utc


def test_sade_sati_never_mixes_in_the_other_reserved_variants() -> None:
    facts = SERVICE.sade_sati(natal(moon=10.0), utc(2020, 1, 1), utc(2030, 1, 1))
    assert facts.profile_ids.sade_sati_profile_id == "SADE_SATI_SIGN_BASED_MODERN_V1"
    text = facts.model_dump_json().lower()
    for name in ("dhaiya", "ashtama"):
        assert name not in text


def test_sade_sati_for_an_approximate_natal_time_that_reaches_a_sign_boundary() -> None:
    ref = NatalReference(
        precision=BirthTimeStatus.APPROXIMATE, moon_longitude_low=359.0, moon_longitude_high=1.0
    )
    facts = SERVICE.sade_sati(ref, utc(2020, 1, 1), utc(2030, 1, 1))
    assert facts.sade_sati is not None
    assert facts.sade_sati.status == SectionStatus.NOT_EVALUABLE
    assert facts.sade_sati.reason_code == TransitReason.NATAL_MOON_SIGN_AMBIGUOUS


# --------------------------------------------------------------------------
# Invariants over random natal charts and windows
# --------------------------------------------------------------------------


def test_window_invariants_on_random_charts_and_windows() -> None:
    rng = random.Random(2026)
    for _ in range(6):
        start = utc(rng.randint(1950, 2080), rng.randint(1, 12), rng.randint(1, 28))
        end = start + dt.timedelta(days=rng.randint(200, 900))
        ref = natal(
            moon=rng.uniform(0, 360),
            planets={B.SUN: rng.uniform(0, 360), B.SATURN: rng.uniform(0, 360)},
        )
        facts = SERVICE.events(
            ref,
            start,
            end,
            TransitConfiguration(
                bodies=(B.SUN, B.MERCURY, B.JUPITER, B.SATURN, B.RAHU),
                event_kinds=(EventKind.SIGN_INGRESS, *STATIONS),
            ),
        )
        assert facts.status == TransitStatus.SUCCESS and facts.window is not None
        events = facts.window.events
        keys = [(e.julian_day_ut, list(B).index(e.body)) for e in events]
        assert keys == sorted(keys)
        assert all(start <= e.instant_utc < end for e in events)
        assert len({e.event_id for e in events}) == len(events)
        start_states = {s.body: s for s in facts.window.start_snapshot.states}
        for body in (B.SUN, B.MERCURY, B.JUPITER, B.SATURN, B.RAHU):
            chain = [e for e in events if e.body == body and e.kind == EventKind.SIGN_INGRESS]
            expected_from = start_states[body].sign.value
            for event in chain:
                assert event.from_value == expected_from, (body, event.event_id)
                expected_from = event.to_value
            stations = [e for e in events if e.body == body and e.kind != EventKind.SIGN_INGRESS]
            for previous, current in zip(stations, stations[1:], strict=False):
                assert previous.kind != current.kind
            if stations:
                first_kind = stations[0].kind
                assert (first_kind == EventKind.STATION_DIRECT) == start_states[body].retrograde
        assert all(e.body != B.RAHU or e.kind == EventKind.SIGN_INGRESS for e in events)


def test_adjacent_real_windows_partition_the_events() -> None:
    config = TransitConfiguration(
        bodies=(B.MARS, B.SATURN), event_kinds=(EventKind.SIGN_INGRESS, *STATIONS)
    )
    whole = SERVICE.events(natal(), utc(2022, 1, 1), utc(2024, 1, 1), config)
    left = SERVICE.events(natal(), utc(2022, 1, 1), utc(2023, 1, 1), config)
    right = SERVICE.events(natal(), utc(2023, 1, 1), utc(2024, 1, 1), config)
    assert whole.window is not None and left.window is not None and right.window is not None
    assert [e.event_id for e in whole.window.events] == [
        e.event_id for e in left.window.events + right.window.events
    ]


def test_every_request_is_reproducible_on_real_data() -> None:
    args = (natal(moon=200.0), utc(2024, 1, 1), utc(2024, 7, 1))
    config = TransitConfiguration(bodies=(B.MOON, B.SUN, B.MERCURY), include_sade_sati=True)
    assert SERVICE.events(*args, config) == SERVICE.events(*args, config)


def test_event_windows_and_events_are_bounded_by_the_documented_limits() -> None:
    too_big = SERVICE.events(natal(), utc(1800, 1, 1), utc(2100, 1, 1))
    assert too_big.status == TransitStatus.NOT_EVALUABLE
    assert too_big.reason_code == TransitReason.WINDOW_TOO_LARGE


def test_a_multi_decade_window_of_slow_planets_is_fast() -> None:
    started = time.perf_counter()
    facts = SERVICE.events(
        natal(),
        utc(1950, 1, 1),
        utc(2040, 1, 1),
        TransitConfiguration(bodies=(B.SATURN, B.JUPITER, B.RAHU), event_kinds=INGRESS),
    )
    elapsed = time.perf_counter() - started
    assert facts.status == TransitStatus.SUCCESS and facts.window is not None
    assert facts.window.event_count > 30
    assert elapsed < 30.0  # measured well under 2 s on the development machine
