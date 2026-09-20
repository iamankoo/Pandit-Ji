"""Vimshottari Dasha calculation -- Phase 7 (Dasha & Timing Engine).

Pure, deterministic arithmetic: a Moon sidereal longitude and a UTC birth
instant in, a nested Mahadasha / Antardasha / Pratyantar timeline out. No
ephemeris call, no clock, no I/O, no interpretation.

Exactness. All durations are exact `Fraction`s of microseconds measured as an
offset from the birth instant. A boundary is serialized to the UTC instant
`birth + floor(offset)` microseconds. Every shared boundary is computed once
and serialized once, so periods tile their parent with no gap and no overlap;
the only quantization is that flooring, at most one microsecond per boundary.
Intervals are half-open, [start, end): a shared boundary belongs to the later
period (Pandit Ji engineering convention).
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from fractions import Fraction

from pandit_astro_engine._version import __version__
from pandit_astro_engine.dashas.constants import (
    DASHA_STANDARDS_VERSION,
    LEVEL_ID_PREFIX,
    LEVEL_ORDER,
    MAX_DEPTH,
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_TOTAL_YEARS,
    VIMSHOTTARI_YEARS,
    DashaLevel,
)
from pandit_astro_engine.dashas.models import (
    BirthTimeStatus,
    DashaFacts,
    DashaReason,
    DashaRequest,
    DashaStatus,
    PeriodNode,
    PeriodProfileIds,
    PrecisionAssessment,
    ProvenanceEntry,
    Rational,
    StartingState,
    ValidationResult,
)
from pandit_astro_engine.dashas.profiles import (
    SUBPERIOD_PROFILE_DESCRIPTION,
    SUBPERIOD_PROFILE_ID,
    SUBPERIOD_REFERENCES,
    BalanceProfile,
    EvidenceLabel,
    ProfileAvailability,
    SourceReference,
    YearLengthProfile,
    get_balance_profile,
    get_year_length_profile,
)
from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import (
    NAKSHATRA_ORDER,
    NAKSHATRA_SPAN_DEGREES,
    nakshatra_position,
)

MICROSECONDS_PER_DAY = 86_400 * 1_000_000
MAX_HORIZON_YEARS = 240

_ENGINEERING = EvidenceLabel.ENGINEERING_CONVENTION


# --------------------------------------------------------------------------
# Small exact-arithmetic helpers
# --------------------------------------------------------------------------


def year_microseconds(profile: YearLengthProfile) -> Fraction:
    """Exact microseconds in one profile year."""
    return profile.days() * MICROSECONDS_PER_DAY


def _floor(value: Fraction) -> int:
    return value.numerator // value.denominator


def normalize_longitude(longitude: float) -> Fraction:
    """The Phase 5 normalization (floating-point modulo 360), then exact."""
    return Fraction(longitude % 360.0) % 360


def nakshatra_fractions(longitude: float) -> tuple[int, Fraction]:
    """(Nakshatra index 0..26, elapsed fraction of that Nakshatra) computed
    exactly from the normalized float. An exact boundary is elapsed 0 of the
    upper Nakshatra."""
    scaled = normalize_longitude(longitude) * 27 / 360
    index = _floor(scaled)
    return index, scaled - index


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def validate_request(request: DashaRequest) -> ValidationResult:
    """Structural and profile validation. Never guesses a missing value."""
    config = request.config
    if request.moon_longitude_degrees is None:
        return _invalid(DashaStatus.INVALID_INPUT, DashaReason.MOON_LONGITUDE_MISSING)
    if not math.isfinite(request.moon_longitude_degrees):
        return _invalid(DashaStatus.INVALID_INPUT, DashaReason.NON_FINITE_LONGITUDE)
    if request.birth_utc.tzinfo is None or request.birth_utc.utcoffset() is None:
        return _invalid(DashaStatus.INVALID_INPUT, DashaReason.NAIVE_DATETIME)
    if not 1 <= config.depth <= MAX_DEPTH:
        return _invalid(
            DashaStatus.INVALID_INPUT,
            DashaReason.UNSUPPORTED_HIERARCHY_DEPTH,
            f"depth must be 1..{MAX_DEPTH} (Sookshma and Prana are out of scope)",
        )
    if not 1 <= config.horizon_years <= MAX_HORIZON_YEARS:
        return _invalid(
            DashaStatus.INVALID_INPUT,
            DashaReason.INVALID_HORIZON,
            f"horizon_years must be 1..{MAX_HORIZON_YEARS}",
        )
    balance = get_balance_profile(config.balance_profile_id)
    if balance is None:
        return _invalid(DashaStatus.UNSUPPORTED_PROFILE, DashaReason.UNKNOWN_BALANCE_PROFILE)
    if balance.availability is not ProfileAvailability.ACTIVE:
        return _invalid(
            DashaStatus.UNSUPPORTED_PROFILE,
            DashaReason.PROFILE_INACTIVE,
            f"{balance.profile_id}: {balance.unavailable_reason}",
        )
    year = get_year_length_profile(config.year_length_profile_id)
    if year is None:
        return _invalid(DashaStatus.UNSUPPORTED_PROFILE, DashaReason.UNKNOWN_YEAR_LENGTH_PROFILE)
    if year.availability is not ProfileAvailability.ACTIVE:
        return _invalid(
            DashaStatus.UNSUPPORTED_PROFILE,
            DashaReason.PROFILE_INACTIVE,
            f"{year.profile_id}: {year.unavailable_reason}",
        )
    return ValidationResult(valid=True)


def _invalid(
    status: DashaStatus, reason: DashaReason, detail: str | None = None
) -> ValidationResult:
    return ValidationResult(valid=False, status=status, reason_code=reason, detail=detail)


# --------------------------------------------------------------------------
# Period generation
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Ctx:
    birth: dt.datetime
    profile_ids: PeriodProfileIds
    status: DashaStatus
    provenance_ids: tuple[str, ...]
    depth: int


def _to_utc(ctx: _Ctx, offset: Fraction) -> dt.datetime:
    return ctx.birth + dt.timedelta(microseconds=_floor(offset))


def _sequence_from(lord: CelestialBody) -> tuple[CelestialBody, ...]:
    start = VIMSHOTTARI_SEQUENCE.index(lord)
    return VIMSHOTTARI_SEQUENCE[start:] + VIMSHOTTARI_SEQUENCE[:start]


def _emit(
    ctx: _Ctx,
    level: DashaLevel,
    lord: CelestialBody,
    index: int,
    parent: PeriodNode | None,
    nominal_start: Fraction,
    nominal_end: Fraction,
    out: list[PeriodNode],
) -> None:
    """Emit one period (clamped to the birth instant) and recurse."""
    clamped_start = max(nominal_start, Fraction(0))
    if nominal_end <= 0:
        return  # ended at or before birth: not part of the life timeline
    parent_id = parent.period_id if parent else "vim"
    period_id = f"{parent_id}/{LEVEL_ID_PREFIX[level]}{index}:{lord.value}"
    start_utc = _to_utc(ctx, clamped_start)
    end_utc = _to_utc(ctx, nominal_end)
    node = PeriodNode(
        period_id=period_id,
        level=level,
        lord=lord,
        parent_id=parent.period_id if parent else None,
        sequence_index=index,
        path=(*(parent.path if parent else ()), lord.value),
        start_utc=start_utc,
        end_utc=end_utc,
        nominal_start_utc=_to_utc(ctx, nominal_start),
        truncated_at_birth=nominal_start < 0,
        duration_microseconds=(end_utc - start_utc) // dt.timedelta(microseconds=1),
        profile_ids=ctx.profile_ids,
        standards_version=DASHA_STANDARDS_VERSION,
        engine_version=__version__,
        calculation_status=ctx.status,
        provenance_ids=ctx.provenance_ids,
    )
    out.append(node)

    depth_reached = LEVEL_ORDER.index(level) + 1
    if depth_reached >= ctx.depth:
        return
    child_level = LEVEL_ORDER[depth_reached]
    cursor = nominal_start
    nominal_duration = nominal_end - nominal_start
    for child_index, child_lord in enumerate(_sequence_from(lord)):
        child_end = cursor + nominal_duration * VIMSHOTTARI_YEARS[child_lord] / (
            VIMSHOTTARI_TOTAL_YEARS
        )
        if child_index == len(VIMSHOTTARI_SEQUENCE) - 1:
            child_end = nominal_end  # derived from the parent endpoint: no drift
        _emit(ctx, child_level, child_lord, child_index, node, cursor, child_end, out)
        cursor = child_end


def _mahadasha_spans(
    first_lord: CelestialBody, elapsed: Fraction, year_us: Fraction, horizon_years: int
) -> list[tuple[CelestialBody, Fraction, Fraction]]:
    """Mahadasha (lord, nominal start, nominal end) offsets from birth. The
    first is the full Mahadasha of the birth Nakshatra lord, starting before
    birth by the elapsed portion."""
    horizon = horizon_years * year_us
    sequence = _sequence_from(first_lord)
    offset = -elapsed * VIMSHOTTARI_YEARS[first_lord] * year_us
    spans: list[tuple[CelestialBody, Fraction, Fraction]] = []
    index = 0
    while True:
        lord = sequence[index % 9]
        end = offset + VIMSHOTTARI_YEARS[lord] * year_us
        spans.append((lord, offset, end))
        offset = end
        index += 1
        if end >= horizon:
            return spans


def generate_periods(
    *,
    birth: dt.datetime,
    first_lord: CelestialBody,
    elapsed_fraction: Fraction,
    year_us: Fraction,
    depth: int,
    horizon_years: int,
    profile_ids: PeriodProfileIds,
    status: DashaStatus,
    provenance_ids: tuple[str, ...],
) -> tuple[PeriodNode, ...]:
    ctx = _Ctx(birth, profile_ids, status, provenance_ids, depth)
    out: list[PeriodNode] = []
    for index, (lord, start, end) in enumerate(
        _mahadasha_spans(first_lord, elapsed_fraction, year_us, horizon_years)
    ):
        _emit(ctx, DashaLevel.MAHADASHA, lord, index, None, start, end, out)
    return tuple(out)


# --------------------------------------------------------------------------
# Precision
# --------------------------------------------------------------------------


def _unwrapped_pair(low: float, high: float) -> tuple[float, float]:
    """Moon is always prograde: if the interval wraps through 360, unwrap it."""
    return (low, high if high >= low else high + 360.0)


def assess_precision(request: DashaRequest) -> tuple[PrecisionAssessment, ValidationResult]:
    """Evaluate the birth-time interval against classification boundaries.
    Returns the assessment plus a validation result (invalid or not evaluable
    cases carry their status and reason)."""
    status = request.birth_time.status
    seconds = request.birth_time.uncertainty_seconds
    if status is BirthTimeStatus.EXACT:
        return PrecisionAssessment(birth_time_status=status), ValidationResult(valid=True)
    if status is BirthTimeStatus.NOT_EVALUABLE:
        return (
            PrecisionAssessment(birth_time_status=status),
            _invalid(DashaStatus.NOT_EVALUABLE, DashaReason.BIRTH_TIME_UNKNOWN),
        )

    base = PrecisionAssessment(birth_time_status=status, uncertainty_seconds=seconds)
    if seconds is None or request.uncertainty_range is None:
        return base, _invalid(DashaStatus.NOT_EVALUABLE, DashaReason.UNCERTAINTY_INTERVAL_MISSING)
    if not math.isfinite(seconds) or seconds <= 0:
        return base, _invalid(DashaStatus.INVALID_INPUT, DashaReason.INVALID_UNCERTAINTY)
    rng = request.uncertainty_range
    if not (
        math.isfinite(rng.moon_longitude_at_earliest)
        and math.isfinite(rng.moon_longitude_at_latest)
    ):
        return base, _invalid(DashaStatus.INVALID_INPUT, DashaReason.NON_FINITE_LONGITUDE)

    low, high = _unwrapped_pair(rng.moon_longitude_at_earliest, rng.moon_longitude_at_latest)
    if high - low > 180.0:
        return base, _invalid(DashaStatus.INVALID_INPUT, DashaReason.MOON_RANGE_INCONSISTENT)
    assert request.moon_longitude_degrees is not None
    nominal = request.moon_longitude_degrees
    if not _within_arc(nominal, low, high):
        return base, _invalid(DashaStatus.INVALID_INPUT, DashaReason.MOON_RANGE_INCONSISTENT)

    low_index, low_elapsed = nakshatra_fractions(low)
    high_index, high_elapsed = nakshatra_fractions(high)
    low_pos = nakshatra_position(low)
    high_pos = nakshatra_position(high)
    nakshatra_crossed = low_index != high_index or (high - low) >= NAKSHATRA_SPAN_DEGREES
    lord_stable = (not nakshatra_crossed) and low_pos.lord == high_pos.lord
    pada_crossed = nakshatra_crossed or low_pos.pada != high_pos.pada

    assessment = PrecisionAssessment(
        birth_time_status=status,
        uncertainty_seconds=seconds,
        starting_lord_stable=lord_stable,
        nakshatra_boundary_within_interval=nakshatra_crossed,
        pada_boundary_within_interval=pada_crossed,
        moon_longitude_low=low,
        moon_longitude_high=high,
    )
    if not lord_stable:
        return assessment, _invalid(DashaStatus.NOT_EVALUABLE, DashaReason.STARTING_LORD_AMBIGUOUS)
    return assessment, ValidationResult(valid=True)


def _within_arc(value: float, low: float, high: float) -> bool:
    """True when `value` (mod 360) lies in [low, high] (an unwrapped arc)."""
    for turn in (-360.0, 0.0, 360.0):
        if low <= value + turn <= high:
            return True
    return False


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------


def build_provenance(
    balance: BalanceProfile, year: YearLengthProfile
) -> tuple[ProvenanceEntry, ...]:
    return (
        ProvenanceEntry(
            entry_id="prov.sequence_and_years",
            item="Vimshottari lord sequence and Mahadasha years (120-year cycle)",
            evidence_label=EvidenceLabel.SOURCE_SUPPORTED,
            statement=(
                "Sun 6, Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17, Ketu 7, "
                "Venus 20, counted from Krittika; total 120. Supported at translation level."
            ),
            references=(
                _ref(
                    "SRC-BPHS-SANTHANAM-1984",
                    "Ch. 46 v. 12-15 (Kapoor)",
                    "IMAGE_CHECKED_TRANSLATION",
                ),
                _ref("SRC-PHALADEEPIKA-SASTRI", "Adhyaya XIX sl. 2", "OCR_TRANSLATION"),
            ),
        ),
        ProvenanceEntry(
            entry_id="prov.balance",
            item=f"Balance at birth: {balance.profile_id}",
            evidence_label=balance.evidence_label,
            statement=(
                f"{balance.method}. This is an explicit profile choice; the balance method is a "
                "documented source conflict (time-based BPHS Ch. 46 v. 16 versus longitude-based "
                "standard) and this result does not resolve it."
            ),
            references=balance.references,
        ),
        ProvenanceEntry(
            entry_id="prov.year_length",
            item=f"Year length: {year.profile_id}",
            evidence_label=year.evidence_label,
            statement=(
                "Fixed-duration year in exact microseconds; no calendar-year or leap-year "
                "arithmetic. No verse read states the year length used for Vimshottari."
            ),
            references=year.references,
        ),
        ProvenanceEntry(
            entry_id="prov.subperiods",
            item=f"Sub-periods: {SUBPERIOD_PROFILE_ID}",
            evidence_label=_ENGINEERING,
            statement=SUBPERIOD_PROFILE_DESCRIPTION,
            references=SUBPERIOD_REFERENCES,
        ),
        ProvenanceEntry(
            entry_id="prov.boundaries",
            item="Boundary convention",
            evidence_label=_ENGINEERING,
            statement=(
                "Half-open intervals [start, end); a shared boundary belongs to the later "
                "period. Nakshatra classification follows standards v1.4.1. No classical source "
                "read states an inclusivity rule."
            ),
        ),
        ProvenanceEntry(
            entry_id="prov.timeline",
            item="Period boundaries",
            evidence_label=EvidenceLabel.DERIVED_CALCULATION,
            statement=(
                "Exact rational arithmetic in UTC microseconds from the birth instant; each "
                "boundary is floored to a whole microsecond once."
            ),
        ),
    )


def _ref(source_id: str, locator: str, level: str) -> SourceReference:
    return SourceReference(source_id=source_id, locator=locator, verification_level=level)


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------


def _failure(
    request: DashaRequest,
    result: ValidationResult,
    precision: PrecisionAssessment | None = None,
) -> DashaFacts:
    assert result.reason_code is not None
    return DashaFacts(
        status=result.status,
        reason_code=result.reason_code,
        detail=result.detail,
        engine_version=__version__,
        profile_ids=PeriodProfileIds(
            balance_profile_id=request.config.balance_profile_id,
            year_length_profile_id=request.config.year_length_profile_id,
            subperiod_profile_id=SUBPERIOD_PROFILE_ID,
        ),
        precision=precision or PrecisionAssessment(birth_time_status=request.birth_time.status),
    )


def _starting_state(
    longitude: float, lord_years_year_us: Fraction
) -> tuple[StartingState, int, Fraction]:
    position = nakshatra_position(longitude)
    index, elapsed = nakshatra_fractions(longitude)
    if NAKSHATRA_ORDER[index] is not position.nakshatra:
        raise RuntimeError("Nakshatra classification disagrees between exact and public paths")
    remaining = 1 - elapsed
    years = VIMSHOTTARI_YEARS[position.lord]
    remaining_us = remaining * years * lord_years_year_us
    state = StartingState(
        raw_moon_longitude=longitude,
        normalized_longitude=longitude % 360.0,
        nakshatra=position.nakshatra,
        pada=position.pada,
        lord=position.lord,
        near_boundary=position.near_boundary,
        elapsed_fraction=Rational.of(elapsed),
        remaining_fraction=Rational.of(remaining),
        lord_full_years=years,
        remaining_duration_microseconds_exact=Rational.of(remaining_us),
        remaining_duration_microseconds=_floor(remaining_us),
    )
    return state, index, elapsed


def calculate_vimshottari(request: DashaRequest) -> DashaFacts:
    """Build the Vimshottari timeline, or a structured non-success result."""
    verdict = validate_request(request)
    if not verdict.valid:
        return _failure(request, verdict)

    assert request.moon_longitude_degrees is not None
    balance = get_balance_profile(request.config.balance_profile_id)
    year = get_year_length_profile(request.config.year_length_profile_id)
    assert balance is not None and year is not None

    precision, precision_verdict = assess_precision(request)
    if not precision_verdict.valid:
        return _failure(request, precision_verdict, precision)

    birth = request.birth_utc.astimezone(dt.timezone.utc)
    year_us = year_microseconds(year)
    starting, _, elapsed = _starting_state(request.moon_longitude_degrees, year_us)

    approximate = precision.birth_time_status is BirthTimeStatus.APPROXIMATE
    status = DashaStatus.APPROXIMATE if approximate else DashaStatus.SUCCESS
    profile_ids = PeriodProfileIds(
        balance_profile_id=balance.profile_id,
        year_length_profile_id=year.profile_id,
        subperiod_profile_id=SUBPERIOD_PROFILE_ID,
    )
    provenance = build_provenance(balance, year)

    warnings: list[str] = []
    if starting.near_boundary:
        warnings.append("near_nakshatra_or_pada_boundary")
    if approximate:
        warnings.append("birth_time_approximate")
        if precision.pada_boundary_within_interval:
            warnings.append("pada_boundary_within_birth_time_interval")
        precision = _with_envelope(request, precision, birth, year_us)

    try:
        periods = generate_periods(
            birth=birth,
            first_lord=starting.lord,
            elapsed_fraction=elapsed,
            year_us=year_us,
            depth=request.config.depth,
            horizon_years=request.config.horizon_years,
            profile_ids=profile_ids,
            status=status,
            provenance_ids=tuple(entry.entry_id for entry in provenance),
        )
    except OverflowError:
        return _failure(
            request, _invalid(DashaStatus.INVALID_INPUT, DashaReason.TIMELINE_OUT_OF_RANGE)
        )

    return DashaFacts(
        status=status,
        engine_version=__version__,
        profile_ids=profile_ids,
        precision=precision,
        birth_utc=birth,
        starting=starting,
        depth=request.config.depth,
        horizon_years=request.config.horizon_years,
        timeline_start_utc=periods[0].start_utc,
        timeline_end_utc=_last_mahadasha_end(periods),
        periods=periods,
        warnings=tuple(warnings),
        provenance=provenance,
    )


def _last_mahadasha_end(periods: tuple[PeriodNode, ...]) -> dt.datetime:
    return max(p.end_utc for p in periods if p.level is DashaLevel.MAHADASHA)


def _with_envelope(
    request: DashaRequest,
    precision: PrecisionAssessment,
    birth: dt.datetime,
    year_us: Fraction,
) -> PrecisionAssessment:
    """First-Mahadasha end range and balance range across the interval. The
    end is evaluated at the two endpoints and the nominal instant only."""
    assert request.uncertainty_range is not None and request.birth_time.uncertainty_seconds
    assert request.moon_longitude_degrees is not None
    half = dt.timedelta(seconds=request.birth_time.uncertainty_seconds)
    samples = (
        (birth - half, request.uncertainty_range.moon_longitude_at_earliest),
        (birth, request.moon_longitude_degrees),
        (birth + half, request.uncertainty_range.moon_longitude_at_latest),
    )
    ends: list[dt.datetime] = []
    remainings: list[Fraction] = []
    for instant, longitude in samples:
        _, elapsed = nakshatra_fractions(longitude)
        remaining = 1 - elapsed
        lord = nakshatra_position(longitude).lord
        remainings.append(remaining)
        ends.append(
            instant
            + dt.timedelta(microseconds=_floor(remaining * VIMSHOTTARI_YEARS[lord] * year_us))
        )
    return precision.model_copy(
        update={
            "balance_fraction_min": Rational.of(min(remainings)),
            "balance_fraction_max": Rational.of(max(remainings)),
            "first_mahadasha_end_earliest_utc": min(ends),
            "first_mahadasha_end_latest_utc": max(ends),
            "envelope_method": "interval_endpoints_and_nominal_instant",
        }
    )
