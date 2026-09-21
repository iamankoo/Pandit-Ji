"""The transit calculator (Phase 8): a pure function of a request and a
`PositionProvider`. It returns structured `TransitFacts` (a status and reason
code on any domain failure), never a stack trace, and never guesses.

Facts only: no interpretation, no verdict, no remedy (docs TR-01).
"""

from __future__ import annotations

import datetime as dt

from pandit_astro_engine.dashas.models import BirthTimeStatus
from pandit_astro_engine.errors import EphemerisCalculationError, EphemerisDataUnavailableError
from pandit_astro_engine.models import CelestialBody, EphemerisMode, NodeConvention, ZodiacType
from pandit_astro_engine.nakshatra import NAKSHATRA_ORDER
from pandit_astro_engine.rashi import rashi_from_index
from pandit_astro_engine.transits import evaluate
from pandit_astro_engine.transits.constants import (
    BOUNDARY_CONVENTION,
    HORIZONS_EVIDENCE,
    MAX_WINDOW_DAYS,
    SEARCH_TOLERANCE_DAYS,
    SEARCH_TOLERANCE_SECONDS,
    TRANSIT_STANDARDS_VERSION,
)
from pandit_astro_engine.transits.events import (
    EventLimitExceededError,
    RawEvent,
    scan_body,
    scan_window,
)
from pandit_astro_engine.transits.models import (
    AccuracyDisclosure,
    EventKind,
    NatalSummary,
    ProvenanceEntry,
    SadeSatiFacts,
    SectionStatus,
    TransitConfiguration,
    TransitContact,
    TransitEvent,
    TransitFacts,
    TransitProfileIds,
    TransitReason,
    TransitRequest,
    TransitStatus,
    TransitWindow,
)
from pandit_astro_engine.transits.positions import (
    PositionProvider,
    datetime_to_jd,
    jd_to_datetime,
)
from pandit_astro_engine.transits.profiles import (
    ACCURACY_PROFILE_ID,
    BOUNDARY_PROFILE_ID,
    CONTACT_PROFILE_ID,
    EVENTS_PROFILE_ID,
    FAVOURABLE_READING_IDS,
    FAVOURABLE_READINGS,
    REF_LAGNA_SIGN_ID,
    REF_MOON_SIGN_ID,
    SADE_SATI_CLASSICAL_STATUS,
    SADE_SATI_ID,
    VEDHA_PHALADEEPIKA_ID,
    VEDHA_REFERENCE,
    VENUS_VEDHA_ANOMALY_WARNING,
    EvidenceLabel,
    SourceReference,
)
from pandit_astro_engine.transits.sade_sati import (
    InconsistentTimelineError,
    SignIngress,
    build_sade_sati,
)

_TIME_SCALE_NOTE = (
    "UTC instants map to Julian Day UT with the Phase 4 conversion; the sub-second UT1-UTC "
    "difference is not modelled"
)
_AYANAMSA_NOTE = (
    "a sidereal ingress instant depends on the ayanamsa value; published ingress times for the "
    "same event differ by hours between sources, so published times are not used as references"
)


# --------------------------------------------------------------------------
# Failures
# --------------------------------------------------------------------------


def _profile_ids(config: TransitConfiguration, *, window: bool) -> TransitProfileIds:
    return TransitProfileIds(
        reference_profile_id=config.reference_profile_id,
        favourable_reading_ids=FAVOURABLE_READING_IDS,
        vedha_profile_id=config.vedha_profile_id if config.include_vedha else None,
        contact_profile_id=CONTACT_PROFILE_ID if config.include_contacts else None,
        events_profile_id=EVENTS_PROFILE_ID if window and config.event_kinds else None,
        boundary_profile_id=BOUNDARY_PROFILE_ID,
        sade_sati_profile_id=config.sade_sati_profile_id if config.include_sade_sati else None,
        lagna_profile_id=REF_LAGNA_SIGN_ID if config.include_lagna_fact else None,
    )


def _failure(
    request: TransitRequest,
    status: TransitStatus,
    reason: TransitReason,
    engine_version: str,
    swisseph_version: str | None,
    detail: str | None = None,
) -> TransitFacts:
    has_window = request.window_start_utc is not None or request.window_end_utc is not None
    return TransitFacts(
        status=status,
        reason_code=reason,
        detail=detail,
        engine_version=engine_version,
        swisseph_version=swisseph_version,
        configuration=request.config,
        profile_ids=_profile_ids(request.config, window=has_window),
    )


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def _aware(value: dt.datetime | None) -> bool:
    return value is not None and value.tzinfo is not None and value.utcoffset() is not None


def _validate(request: TransitRequest) -> tuple[TransitStatus, TransitReason, str] | None:
    config = request.config
    if config.calculation.zodiac != ZodiacType.SIDEREAL or config.calculation.ayanamsa is None:
        return (
            TransitStatus.CONFIGURATION_ERROR,
            TransitReason.SIDEREAL_ZODIAC_REQUIRED,
            "the transit engine requires the sidereal zodiac",
        )
    if config.reference_profile_id != REF_MOON_SIGN_ID:
        return (
            TransitStatus.UNSUPPORTED_PROFILE,
            TransitReason.UNSUPPORTED_PROFILE,
            f"reference profile {config.reference_profile_id!r}; the Lagna fact is enabled with "
            "include_lagna_fact",
        )
    if config.include_vedha and config.vedha_profile_id != VEDHA_PHALADEEPIKA_ID:
        return (
            TransitStatus.UNSUPPORTED_PROFILE,
            TransitReason.UNSUPPORTED_PROFILE,
            f"vedha profile {config.vedha_profile_id!r}",
        )
    if config.include_sade_sati and config.sade_sati_profile_id != SADE_SATI_ID:
        return (
            TransitStatus.UNSUPPORTED_PROFILE,
            TransitReason.UNSUPPORTED_PROFILE,
            f"Sade Sati profile {config.sade_sati_profile_id!r} is reserved or unknown",
        )
    if not config.bodies:
        return TransitStatus.INVALID_INPUT, TransitReason.NO_BODIES, "no bodies requested"
    natal = request.natal
    if any(not _finite(v) for v in natal.all_longitudes()):
        return (
            TransitStatus.INVALID_INPUT,
            TransitReason.NON_FINITE_LONGITUDE,
            "a natal longitude is not finite",
        )
    if (
        natal.precision == BirthTimeStatus.APPROXIMATE
        and natal.moon_longitude is not None
        and natal.moon_longitude_low is not None
        and natal.moon_longitude_high is not None
        and not evaluate.value_in_range(
            natal.moon_longitude, natal.moon_longitude_low, natal.moon_longitude_high
        )
    ):
        return (
            TransitStatus.INVALID_INPUT,
            TransitReason.NATAL_RANGE_INCONSISTENT,
            "the nominal Moon longitude lies outside its own range",
        )
    if (
        request.at_utc is None
        and request.window_start_utc is None
        and request.window_end_utc is None
    ):
        return TransitStatus.INVALID_INPUT, TransitReason.NO_QUERY, "no instant and no window"
    if request.at_utc is not None and not _aware(request.at_utc):
        return TransitStatus.INVALID_INPUT, TransitReason.INVALID_INSTANT, "at_utc is naive"
    if request.window_start_utc is not None or request.window_end_utc is not None:
        start, end = request.window_start_utc, request.window_end_utc
        if start is None or end is None:
            return TransitStatus.INVALID_INPUT, TransitReason.INVALID_WINDOW, "half a window"
        if not _aware(start) or not _aware(end):
            return TransitStatus.INVALID_INPUT, TransitReason.INVALID_INSTANT, "naive window bound"
        if end <= start:
            return (
                TransitStatus.INVALID_INPUT,
                TransitReason.INVALID_WINDOW,
                "the window end must be after its start (half-open [start, end))",
            )
        if (end - start).total_seconds() / 86_400.0 > MAX_WINDOW_DAYS:
            return (
                TransitStatus.NOT_EVALUABLE,
                TransitReason.WINDOW_TOO_LARGE,
                "a window may not exceed 200 years",
            )
    return None


def _finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


# --------------------------------------------------------------------------
# Events
# --------------------------------------------------------------------------


def _to_event(
    raw: RawEvent, ctx: evaluate.NatalContext, config: TransitConfiguration
) -> TransitEvent:
    instant = jd_to_datetime(raw.julian_day_ut)
    from_value: str | None = None
    to_value: str | None = None
    backward: bool | None = None
    contacts: tuple[TransitContact, ...] = ()
    if raw.kind == EventKind.SIGN_INGRESS:
        assert raw.from_index is not None and raw.to_index is not None
        from_value = rashi_from_index(raw.from_index).value
        to_value = rashi_from_index(raw.to_index).value
        backward = (raw.to_index - raw.from_index) % 12 == 11
        if config.include_contacts and ctx.natal_signs is not None:
            contacts = evaluate.contacts_for(raw.body, raw.to_index, ctx.natal_signs)
    elif raw.kind == EventKind.NAKSHATRA_INGRESS:
        assert raw.from_index is not None and raw.to_index is not None
        from_value = NAKSHATRA_ORDER[raw.from_index].value
        to_value = NAKSHATRA_ORDER[raw.to_index].value
        backward = (raw.to_index - raw.from_index) % 27 == 26
    return TransitEvent(
        event_id=f"TRN:{raw.kind.value.upper()}:{raw.body.value}:{instant.isoformat()}",
        kind=raw.kind,
        body=raw.body,
        instant_utc=instant,
        julian_day_ut=raw.julian_day_ut,
        from_value=from_value,
        to_value=to_value,
        longitude=raw.position.longitude,
        speed_longitude=raw.position.speed_longitude,
        retrograde=raw.position.retrograde,
        backward_motion=backward,
        contacts_after=contacts,
        ephemeris_mode=raw.position.ephemeris_mode,
    )


# --------------------------------------------------------------------------
# Provenance and accuracy
# --------------------------------------------------------------------------


def _provenance(config: TransitConfiguration, *, window: bool) -> tuple[ProvenanceEntry, ...]:
    entries = [
        ProvenanceEntry(
            entry_id="reference",
            item=REF_MOON_SIGN_ID,
            evidence_label=EvidenceLabel.SOURCE_SUPPORTED,
            statement=(
                "houses are counted whole-sign from the natal Moon's sign (Phaladeepika XXVI "
                "sl. 1 and Brihat Samhita CIV sl. 4, page-image checked, translation level)"
            ),
        )
    ]
    for reading in FAVOURABLE_READINGS:
        entries.append(
            ProvenanceEntry(
                entry_id=f"favourable:{reading.reading_id}",
                item=reading.reading_id,
                evidence_label=reading.label,
                statement=f"favourable-house set: {reading.title}",
                references=reading.references,
            )
        )
    entries.append(
        ProvenanceEntry(
            entry_id="favourable_conflict",
            item="moon_from_moon",
            evidence_label=EvidenceLabel.UNRESOLVED_CONFLICT,
            statement=(
                "the readings disagree for the Moon from itself on houses 5, 6 and 9; the "
                "result is NOT_EVALUABLE(reading_ambiguous) with every reading kept; Rahu and "
                "Ketu rest on one source and are never consolidated"
            ),
        )
    )
    if config.include_vedha:
        entries.append(
            ProvenanceEntry(
                entry_id="vedha",
                item=VEDHA_PHALADEEPIKA_ID,
                evidence_label=EvidenceLabel.SOURCE_SUPPORTED,
                statement=(
                    "Vedha is a Phaladeepika-specific structural profile with a single "
                    "verse-level source; a structural occupancy fact, not a verdict; the Venus "
                    "sl. 8 wording anomaly is preserved"
                ),
                references=(VEDHA_REFERENCE,),
            )
        )
    if config.include_contacts:
        entries.append(
            ProvenanceEntry(
                entry_id="contacts",
                item=CONTACT_PROFILE_ID,
                evidence_label=EvidenceLabel.ENGINEERING_CONVENTION,
                statement="sign-based conjunction and Phase 5 graha drishti; no orb",
            )
        )
    if config.include_lagna_fact:
        entries.append(
            ProvenanceEntry(
                entry_id="lagna",
                item=REF_LAGNA_SIGN_ID,
                evidence_label=EvidenceLabel.ENGINEERING_CONVENTION,
                statement="house from the natal Lagna is a positional fact only, never classical",
            )
        )
    if window and config.event_kinds:
        entries.append(
            ProvenanceEntry(
                entry_id="events",
                item=EVENTS_PROFILE_ID,
                evidence_label=EvidenceLabel.ENGINEERING_CONVENTION,
                statement="no source defines transit events; instants are numerical solutions",
            )
        )
    if config.include_sade_sati:
        entries.append(
            ProvenanceEntry(
                entry_id="sade_sati",
                item=SADE_SATI_ID,
                evidence_label=EvidenceLabel.MODERN_TRADITION,
                statement=SADE_SATI_CLASSICAL_STATUS,
            )
        )
    entries.append(
        ProvenanceEntry(
            entry_id="boundary",
            item=BOUNDARY_PROFILE_ID,
            evidence_label=EvidenceLabel.ENGINEERING_CONVENTION,
            statement=BOUNDARY_CONVENTION,
        )
    )
    entries.append(
        ProvenanceEntry(
            entry_id="accuracy",
            item=ACCURACY_PROFILE_ID,
            evidence_label=EvidenceLabel.ENGINEERING_EVIDENCE,
            statement=HORIZONS_EVIDENCE,
            references=(
                SourceReference(
                    source_id="JPL Horizons",
                    locator="services/astro-engine/tests/fixtures/horizons_transit_reference.json",
                    verification_level="engineering evidence, 42 samples",
                ),
            ),
        )
    )
    return tuple(entries)


def _accuracy(config: TransitConfiguration, modes: set[EphemerisMode]) -> AccuracyDisclosure:
    calc = config.calculation
    return AccuracyDisclosure(
        ephemeris_modes=tuple(sorted(modes, key=lambda m: m.value)),
        zodiac=calc.zodiac.value,
        ayanamsa=calc.ayanamsa.value if calc.ayanamsa is not None else None,
        node_convention=calc.node_convention.value,
        search_tolerance_seconds=SEARCH_TOLERANCE_SECONDS,
        time_scale_note=_TIME_SCALE_NOTE,
        ayanamsa_sensitivity_note=_AYANAMSA_NOTE,
        engineering_evidence=HORIZONS_EVIDENCE,
    )


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------


def calculate_transit(
    request: TransitRequest,
    provider: PositionProvider,
    *,
    engine_version: str,
    swisseph_version: str | None = None,
) -> TransitFacts:
    problem = _validate(request)
    if problem is not None:
        status, reason, detail = problem
        return _failure(request, status, reason, engine_version, swisseph_version, detail)
    try:
        return _calculate(request, provider, engine_version, swisseph_version)
    except EventLimitExceededError:
        return _failure(
            request,
            TransitStatus.NOT_EVALUABLE,
            TransitReason.EVENT_LIMIT_EXCEEDED,
            engine_version,
            swisseph_version,
            "more than 50,000 events in the window",
        )
    except EphemerisDataUnavailableError:
        return _failure(
            request,
            TransitStatus.CONFIGURATION_ERROR,
            TransitReason.EPHEMERIS_UNAVAILABLE,
            engine_version,
            swisseph_version,
        )
    except EphemerisCalculationError as exc:
        return _failure(
            request,
            TransitStatus.NOT_EVALUABLE,
            TransitReason.EPHEMERIS_ERROR,
            engine_version,
            swisseph_version,
            str(exc),
        )
    except InconsistentTimelineError as exc:
        return _failure(
            request,
            TransitStatus.INTERNAL_ERROR,
            TransitReason.INTERNAL_ERROR,
            engine_version,
            swisseph_version,
            str(exc),
        )


def _calculate(
    request: TransitRequest,
    provider: PositionProvider,
    engine_version: str,
    swisseph_version: str | None,
) -> TransitFacts:
    config = request.config
    ctx = evaluate.resolve_natal(request.natal)
    modes: set[EphemerisMode] = set()

    snapshot = None
    if request.at_utc is not None:
        snapshot = evaluate.build_snapshot(
            provider, datetime_to_jd(request.at_utc), request.at_utc, config, ctx
        )
        modes.update(state.ephemeris_mode for state in snapshot.states)

    window = None
    sade_sati: SadeSatiFacts | None = None
    has_window = request.window_start_utc is not None and request.window_end_utc is not None
    if has_window:
        assert request.window_start_utc is not None and request.window_end_utc is not None
        start, end = request.window_start_utc, request.window_end_utc
        jd_start, jd_end = datetime_to_jd(start), datetime_to_jd(end)
        kinds = frozenset(config.event_kinds)
        raw = scan_window(provider, config.bodies, jd_start, jd_end, kinds) if kinds else []
        events = tuple(_to_event(item, ctx, config) for item in raw)
        start_snapshot = evaluate.build_snapshot(provider, jd_start, start, config, ctx)
        window = TransitWindow(
            start_utc=start,
            end_utc=end,
            start_snapshot=start_snapshot,
            events=events,
            event_count=len(events),
        )
        modes.update(state.ephemeris_mode for state in start_snapshot.states)
        modes.update(event.ephemeris_mode for event in events)
        if config.include_sade_sati:
            sade_sati = _sade_sati(provider, ctx, jd_start, jd_end, start, end)

    if not modes:
        probe_jd = (
            datetime_to_jd(request.at_utc)
            if request.at_utc is not None
            else datetime_to_jd(request.window_start_utc)  # type: ignore[arg-type]
        )
        modes.add(provider.position(probe_jd, CelestialBody.SUN).ephemeris_mode)

    warnings: list[str] = []
    if EphemerisMode.MOSHIER in modes:
        warnings.append("ephemeris_mode_moshier")
    all_vedha = list(snapshot.vedha) if snapshot else []
    if window is not None:
        all_vedha.extend(window.start_snapshot.vedha)
    if any(VENUS_VEDHA_ANOMALY_WARNING in fact.warnings for fact in all_vedha):
        warnings.append(VENUS_VEDHA_ANOMALY_WARNING)
    if config.calculation.node_convention == NodeConvention.TRUE:
        warnings.append("true_node_convention_selected")

    moon_available = ctx.moon_sign is not None
    natal = NatalSummary(
        precision=request.natal.precision,
        moon_sign=rashi_from_index(ctx.moon_sign) if ctx.moon_sign is not None else None,
        moon_sign_status=SectionStatus.AVAILABLE if moon_available else SectionStatus.NOT_EVALUABLE,
        moon_sign_reason=ctx.moon_reason,
        lagna_sign=rashi_from_index(ctx.lagna_sign) if ctx.lagna_sign is not None else None,
        natal_planet_count=len(ctx.natal_signs) if ctx.natal_signs else 0,
    )
    return TransitFacts(
        status=TransitStatus.SUCCESS,
        engine_version=engine_version,
        swisseph_version=swisseph_version,
        standards_version=TRANSIT_STANDARDS_VERSION,
        configuration=config,
        profile_ids=_profile_ids(config, window=has_window),
        natal=natal,
        accuracy=_accuracy(config, modes),
        snapshot=snapshot,
        window=window,
        sade_sati=sade_sati,
        warnings=tuple(warnings),
        provenance=_provenance(config, window=has_window),
    )


def _sade_sati(
    provider: PositionProvider,
    ctx: evaluate.NatalContext,
    jd_start: float,
    jd_end: float,
    start: dt.datetime,
    end: dt.datetime,
) -> SadeSatiFacts:
    if ctx.moon_sign is None:
        return SadeSatiFacts(
            classical_status=SADE_SATI_CLASSICAL_STATUS,
            status=SectionStatus.NOT_EVALUABLE,
            reason_code=ctx.moon_reason,
            window_start_utc=start,
            window_end_utc=end,
        )
    saturn = CelestialBody.SATURN
    initial = evaluate.sign_of(provider.position(jd_start, saturn).longitude)
    raw = scan_body(provider, saturn, jd_start, jd_end, frozenset({EventKind.SIGN_INGRESS}))
    ingresses = [
        SignIngress(e.julian_day_ut, e.from_index or 0, e.to_index or 0, e.position.retrograde)
        for e in raw
    ]
    # An ingress at the window start is located only to within the solver tolerance, so its
    # instant can fall a hair after the start although the state at the start is already the
    # new one. That state is what the timeline starts from: the event is already reflected in
    # it and is not replayed (it would otherwise create a spurious segment of the old sign).
    if (
        ingresses
        and ingresses[0].from_sign != initial
        and ingresses[0].to_sign == initial
        and ingresses[0].julian_day_ut - jd_start <= SEARCH_TOLERANCE_DAYS
    ):
        ingresses = ingresses[1:]
    segments, episodes = build_sade_sati(ctx.moon_sign, initial, ingresses, jd_to_datetime)
    return SadeSatiFacts(
        classical_status=SADE_SATI_CLASSICAL_STATUS,
        status=SectionStatus.AVAILABLE,
        natal_moon_sign=rashi_from_index(ctx.moon_sign),
        band_signs=tuple(rashi_from_index(ctx.moon_sign + offset) for offset in (-1, 0, 1)),
        window_start_utc=start,
        window_end_utc=end,
        segments=segments,
        episodes=episodes,
    )
