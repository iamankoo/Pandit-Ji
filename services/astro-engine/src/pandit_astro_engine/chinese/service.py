"""Chinese Four Pillars (BaZi) calendar facts (Phase 9 WP-H;
`docs/ASTROLOGY_STANDARDS.md` v1.18.0, CN-01 to CN-14).

    ChineseChartRequest -> ChineseChartService.calculate -> ChineseChartFacts

The Sun's apparent tropical longitude (Phase 4 adapter, no ayanamsa) fixes
the year and month pillars; the local date and time in the caller's chosen
time basis fix the day and hour pillars. Nothing Vedic is used: this module
shares only the adapter, time resolution and input models.
"""

from __future__ import annotations

import datetime as dt

from pandit_astro_engine import ephemeris, timezones
from pandit_astro_engine._version import __version__
from pandit_astro_engine.chinese import pillars as calc
from pandit_astro_engine.chinese.constants import (
    BRANCH_ANIMAL,
    BRANCH_CHARACTER,
    BRANCH_ELEMENT,
    BRANCH_POLARITY,
    CHINESE_STANDARDS_VERSION,
    CHINESE_SYSTEM_ID,
    FIRST_JIE_LONGITUDE,
    SOLAR_TERM_EPSILON_DEGREES,
    STEM_CHARACTER,
    STEM_ELEMENT,
    STEM_POLARITY,
    ChineseTimePrecision,
    DayBoundary,
    PillarReason,
    PillarStatus,
    TimeBasis,
)
from pandit_astro_engine.chinese.models import (
    ChineseChartFacts,
    ChineseChartRequest,
    Pillar,
    ProvenanceEntry,
    SolarTermBracket,
)
from pandit_astro_engine.chinese.profiles import PROVENANCE
from pandit_astro_engine.config import Settings
from pandit_astro_engine.models import EphemerisMode

_UNSET = object()
_MEAN_SOLAR_MOTION = 360.0 / 365.2422  # degrees per day, only a solver starting slope


def _sun(jd_ut: float, allow_moshier: bool) -> tuple[float, float, EphemerisMode]:
    raw = ephemeris.calculate_body(
        jd_ut, ephemeris.SWE_BODY_ID["sun"], sidereal=False, allow_moshier_fallback=allow_moshier
    )
    return raw.longitude, raw.speed_longitude, raw.mode


def _wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def solar_term_instant(target_longitude: float, near_jd_ut: float, allow_moshier: bool) -> float:
    """Julian Day (UT) at which the Sun's apparent longitude equals
    `target_longitude`, the solution nearest `near_jd_ut`. Newton iteration
    on the ephemeris longitude and speed; converged to 1e-9 day (0.1 ms)."""
    jd = near_jd_ut
    for _ in range(12):
        lon, speed, _mode = _sun(jd, allow_moshier)
        step = _wrap180(target_longitude - lon) / (speed if speed > 0 else _MEAN_SOLAR_MOTION)
        jd += step
        if abs(step) < 1e-9:
            break
    return jd


def _utc(jd_ut: float) -> dt.datetime:
    y, m, d, h, mi, s = ephemeris.julian_day_to_utc_datetime_parts(jd_ut)
    whole = int(s)
    micro = min(round((s - whole) * 1_000_000), 999_999)
    return dt.datetime(y, m, d, h, mi, whole, micro, tzinfo=dt.timezone.utc)


def _pillar(index: int) -> Pillar:
    stem, branch = calc.sexagenary(index)
    return Pillar(
        status=PillarStatus.SUCCESS,
        sexagenary_index=index,
        stem=stem,
        branch=branch,
        stem_character=STEM_CHARACTER[stem],
        branch_character=BRANCH_CHARACTER[branch],
        stem_element=STEM_ELEMENT[stem],
        stem_polarity=STEM_POLARITY[stem],
        branch_element=BRANCH_ELEMENT[branch],
        branch_polarity=BRANCH_POLARITY[branch],
        branch_animal=BRANCH_ANIMAL[branch],
    )


def _not_evaluable(reason: PillarReason) -> Pillar:
    return Pillar(status=PillarStatus.NOT_EVALUABLE, reason=reason)


class ChineseChartService:
    """Stateless facade, like the other astro-engine services."""

    def __init__(self, ephemeris_path: str | None = _UNSET) -> None:  # type: ignore[assignment]
        resolved = Settings().ephemeris_path if ephemeris_path is _UNSET else ephemeris_path
        ephemeris.configure_ephemeris_path(resolved)

    def calculate(self, request: ChineseChartRequest) -> ChineseChartFacts:
        allow = request.allow_moshier_fallback
        utc, resolution = timezones.resolve_local_datetime(request.local_datetime)
        jd_et, jd_ut = ephemeris.utc_to_julian_day(
            utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second + utc.microsecond / 1e6
        )
        resolution = resolution.model_copy(update={"julian_day_ut": jd_ut, "julian_day_et": jd_et})
        sun_lon, _speed, mode = _sun(jd_ut, allow)

        sector = calc.month_sector(sun_lon)
        previous_target = (FIRST_JIE_LONGITUDE + 30.0 * sector) % 360.0
        next_target = (previous_target + 30.0) % 360.0
        since = ((sun_lon - previous_target) % 360.0) / _MEAN_SOLAR_MOTION
        until = ((next_target - sun_lon) % 360.0) / _MEAN_SOLAR_MOTION
        previous_jd = solar_term_instant(previous_target, jd_ut - since, allow)
        next_jd = solar_term_instant(next_target, jd_ut + until, allow)
        near = min(
            abs(_wrap180(sun_lon - previous_target)), abs(_wrap180(sun_lon - next_target))
        ) < (SOLAR_TERM_EPSILON_DEGREES)

        lichun_jd = solar_term_instant(
            FIRST_JIE_LONGITUDE,
            jd_ut - ((sun_lon - FIRST_JIE_LONGITUDE) % 360.0) / _MEAN_SOLAR_MOTION,
            allow,
        )
        lichun_year = _utc(lichun_jd).year

        exact = request.time_precision is ChineseTimePrecision.EXACT
        warnings: list[str] = []
        if mode is EphemerisMode.MOSHIER:
            warnings.append(
                "Moshier analytical ephemeris used (no Swiss Ephemeris data files configured)"
            )

        year_index = calc.year_index(lichun_year)
        year = _pillar(year_index)
        month = _pillar(calc.month_index(calc.sexagenary(year_index)[0], sector))

        local = self._basis_datetime(request, utc, jd_ut)
        if exact:
            day, hour = self._day_and_hour(local, request.day_boundary)
        else:
            warnings.append(
                "birth time unknown: the hour pillar is not evaluated; the year and month pillars "
                "are evaluated only if no solar term falls on the birth date"
            )
            hour = _not_evaluable(PillarReason.BIRTH_TIME_UNKNOWN)
            if (
                request.time_basis is TimeBasis.CLOCK_TIME
                and request.day_boundary is DayBoundary.MIDNIGHT
            ):
                date = dt.date(
                    request.local_datetime.year,
                    request.local_datetime.month,
                    request.local_datetime.day,
                )
                day = _pillar(calc.day_index(date))
            else:
                day = _not_evaluable(PillarReason.BIRTH_TIME_UNKNOWN)
            if self._term_on_date(request, previous_jd, next_jd):
                year = _not_evaluable(PillarReason.SOLAR_TERM_ON_BIRTH_DATE)
                month = _not_evaluable(PillarReason.SOLAR_TERM_ON_BIRTH_DATE)
        if near:
            warnings.append("the birth instant is within about 9 seconds of a solar term")

        return ChineseChartFacts(
            system=CHINESE_SYSTEM_ID,
            standards_version=CHINESE_STANDARDS_VERSION,
            engine_version=__version__,
            time_precision=request.time_precision,
            time_basis=request.time_basis,
            day_boundary=request.day_boundary,
            time_resolution=resolution,
            location=request.location,
            ephemeris_mode=mode,
            sun_apparent_longitude=sun_lon,
            near_solar_term=near,
            solar_term_bracket=SolarTermBracket(
                previous_longitude=previous_target,
                previous_utc=_utc(previous_jd),
                next_longitude=next_target,
                next_utc=_utc(next_jd),
            ),
            lichun_year=lichun_year,
            basis_local_datetime=local if exact else None,
            year=year,
            month=month,
            day=day,
            hour=hour,
            provenance=tuple(
                ProvenanceEntry(
                    entry_id=p.entry_id,
                    item=p.item,
                    evidence_label=p.label,
                    statement=p.statement,
                    references=p.references,
                )
                for p in PROVENANCE
            ),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _basis_datetime(
        request: ChineseChartRequest, utc: dt.datetime, jd_ut: float
    ) -> dt.datetime:
        if request.time_basis is TimeBasis.CLOCK_TIME:
            ldt = request.local_datetime
            whole = int(ldt.second)
            return dt.datetime(
                ldt.year,
                ldt.month,
                ldt.day,
                ldt.hour,
                ldt.minute,
                whole,
                round((ldt.second - whole) * 1_000_000),
            )
        offset_hours = request.location.longitude / 15.0
        if request.time_basis is TimeBasis.LOCAL_APPARENT_SOLAR_TIME:
            offset_hours += ephemeris.equation_of_time_days(jd_ut) * 24.0
        return (utc + dt.timedelta(hours=offset_hours)).replace(tzinfo=None)

    @staticmethod
    def _day_and_hour(local: dt.datetime, boundary: DayBoundary) -> tuple[Pillar, Pillar]:
        hours = local.hour + local.minute / 60.0 + (local.second + local.microsecond / 1e6) / 3600
        branch = calc.hour_branch(hours)
        late_zi = hours >= 23.0
        date = local.date()
        if boundary is DayBoundary.ZI_HOUR_2300 and late_zi:
            date = date + dt.timedelta(days=1)
        day_idx = calc.day_index(date)
        day = _pillar(day_idx)
        if boundary is DayBoundary.MIDNIGHT and late_zi:
            return day, _not_evaluable(PillarReason.LATE_ZI_HOUR_STEM_UNRESOLVED)
        hour = _pillar(calc.hour_index(calc.sexagenary(day_idx)[0], branch))
        return day, hour

    @staticmethod
    def _term_on_date(request: ChineseChartRequest, previous_jd: float, next_jd: float) -> bool:
        """Whether a jie term falls within the local civil date given."""
        ldt = request.local_datetime
        tz = timezones.resolve_timezone(ldt.timezone)
        start = dt.datetime(ldt.year, ldt.month, ldt.day, tzinfo=tz).astimezone(dt.timezone.utc)
        end = start + dt.timedelta(days=1)
        return any(start <= _utc(jd) < end for jd in (previous_jd, next_jd))
