"""Daily Panchang (Phase 10; `docs/ASTROLOGY_STANDARDS.md` v1.23.0, PC-01 to
PC-24).

    PanchangRequest -> PanchangService.daily -> DailyPanchang

The Hindu day of a civil date runs from that date's sunrise at the location
to the next sunrise (PC-06). Every element current during the day is listed
with exact start and end instants; the element current at sunrise names the
day. Month facts are given under both saura frames (PC-15). Choghadiya and
Gowri Panchangam are not implemented (no primary source read, PC-22).
"""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Callable
from zoneinfo import ZoneInfo

from pandit_astro_engine import ephemeris, timezones
from pandit_astro_engine._version import __version__
from pandit_astro_engine.config import Settings
from pandit_astro_engine.models import CelestialBody, Location
from pandit_astro_engine.nakshatra import NAKSHATRA_ORDER
from pandit_astro_engine.panchang import astro
from pandit_astro_engine.panchang.astro import Kinematics, Sky
from pandit_astro_engine.panchang.constants import (
    KARANA_SPAN_DEGREES,
    NAKSHATRA_SPAN_DEGREES,
    RAHU_KALAM_DAY_PART,
    TITHI_SPAN_DEGREES,
    WEEKDAY_LORD,
    WEEKDAY_ORDER,
    YAMAGANDA_DAY_PART,
    YOGA_SPAN_DEGREES,
    KaranaName,
    MonthName,
    Paksha,
    YogaName,
    hora_sequence,
    karana_name,
    saura_month_of_sign,
    tithi_name,
    tithi_number_in_paksha,
    tithi_paksha,
)
from pandit_astro_engine.panchang.models import (
    DailyPanchang,
    DayPart,
    DayPartKind,
    ElementKind,
    ElementSpan,
    EventStatus,
    Hora,
    Instant,
    Interval,
    LunarMonth,
    NotImplementedItem,
    PanchangReason,
    PanchangRequest,
    PanchangStatus,
    ProvenanceEntry,
    RiseSet,
    TithiInfo,
    Vara,
)
from pandit_astro_engine.panchang.profiles import (
    CRC_FIXED_AYANAMSA_DEGREES,
    DAY_PART_PROFILE_ID,
    HORA_PROFILE_ID,
    MOONRISE_SWISS_CONVENTION,
    PANCHANG_PROFILE_ID,
    PANCHANG_STANDARDS_VERSION,
    PANCHANG_SYSTEM_ID,
    PROVENANCE,
    SUNRISE_SWISS_CONVENTION,
    EvidenceLabel,
    SauraFrame,
    SunriseConvention,
)

_UNSET = object()
_NUDGE_DAYS = 1e-6  # 0.09 s: step past a found boundary before the next search
_NAKSHATRA_PANCHAKA_START = 300.0  # third quarter of Dhanishta

NOT_IMPLEMENTED: tuple[NotImplementedItem, ...] = (
    NotImplementedItem(item="choghadiya", reason="no primary source read (PC-22)"),
    NotImplementedItem(item="gowri_panchangam", reason="no primary source read (PC-22)"),
    NotImplementedItem(
        item="regional_solar_calendars",
        reason="Tamil, Bengali, Malayalam and Odia solar-month rules not implemented (PC-02)",
    ),
    NotImplementedItem(item="bhadra_residence", reason="no source read (PC-21)"),
    NotImplementedItem(
        item="vikrama_karttikadi_ashadhadi",
        reason="regional Vikrama year beginnings not implemented (PC-17)",
    ),
    NotImplementedItem(item="unequal_hora", reason="no source read (PC-18)"),
)


def to_instant(jd_ut: float, tz: ZoneInfo) -> Instant:
    y, m, d, h, mi, s = ephemeris.julian_day_to_utc_datetime_parts(jd_ut)
    whole = int(s)
    micro = min(999_999, round((s - whole) * 1_000_000))
    utc = dt.datetime(y, m, d, h, mi, whole, micro, tzinfo=dt.timezone.utc)
    return Instant(julian_day_ut=jd_ut, utc=utc, local=utc.astimezone(tz))


def jd_of(moment: dt.datetime) -> float:
    utc = moment.astimezone(dt.timezone.utc)
    _et, ut = ephemeris.utc_to_julian_day(
        utc.year,
        utc.month,
        utc.day,
        utc.hour,
        utc.minute,
        utc.second + utc.microsecond / 1e6,
    )
    return ut


def local_midnight_jd(date: dt.date, tz: ZoneInfo) -> float:
    return jd_of(dt.datetime.combine(date, dt.time(0), tzinfo=tz))


def sunday_zero_weekday(date: dt.date) -> int:
    return (date.weekday() + 1) % 7


class DayFrame:
    """Sunrise, sunset and the next sunrise of one civil date."""

    def __init__(
        self,
        *,
        date: dt.date,
        location: Location,
        tz: ZoneInfo,
        convention: SunriseConvention,
    ) -> None:
        self.date = date
        self.location = location
        self.tz = tz
        swiss = SUNRISE_SWISS_CONVENTION[convention]
        jd0 = local_midnight_jd(date, tz)
        jd1 = local_midnight_jd(date + dt.timedelta(days=1), tz)
        self.sunrise = self._event("sun", "rise", jd0, jd1, swiss)
        self.next_sunrise = (
            self._event("sun", "rise", jd1, jd1 + 1.5, swiss) if self.sunrise is not None else None
        )
        self.sunset = (
            self._event("sun", "set", self.sunrise, self.next_sunrise, swiss)
            if self.sunrise is not None and self.next_sunrise is not None
            else None
        )
        self.circumpolar = self.sunrise is None

    def _event(self, body: str, event: str, start: float, end: float, swiss: str) -> float | None:
        occurred, jd = ephemeris.rise_or_set_with_convention(
            start,
            body=body,
            event=event,
            convention=swiss,
            longitude=self.location.longitude,
            latitude=self.location.latitude,
            altitude_meters=self.location.altitude_meters,
        )
        if not occurred or jd is None or jd >= end:
            return None
        return jd

    @property
    def complete(self) -> bool:
        return None not in (self.sunrise, self.sunset, self.next_sunrise)


def element_spans(
    kind: ElementKind,
    fn: Callable[[float], float],
    kin: Kinematics,
    span: float,
    names: Callable[[int], str],
    sunrise: float,
    next_sunrise: float,
    tz: ZoneInfo,
) -> tuple[ElementSpan, ...]:
    parts = int(round(360.0 / span))
    start = astro.previous_crossing(fn, kin, span, sunrise)
    end, next_part = astro.next_crossing(fn, kin, span, sunrise)
    index = (next_part - 1) % parts + 1
    out = []
    while True:
        out.append(
            ElementSpan(
                kind=kind,
                index=index,
                name=names(index),
                start=to_instant(start, tz),
                end=to_instant(end, tz),
                current_at_sunrise=start <= sunrise,
                current_at_next_sunrise=end > next_sunrise,
                kshaya=start > sunrise and end < next_sunrise,
            )
        )
        if end >= next_sunrise:
            return tuple(out)
        start = end
        end, next_part = astro.next_crossing(fn, kin, span, end + _NUDGE_DAYS)
        index = (next_part - 1) % parts + 1


def saura_sign(sky: Sky, frame: SauraFrame, jd: float) -> int:
    if frame is SauraFrame.LAHIRI_VARIABLE:
        return int(sky.sun_sidereal(jd) // 30.0) % 12
    return int(((sky.sun(jd) - CRC_FIXED_AYANAMSA_DEGREES) % 360.0) // 30.0) % 12


def new_moons_back(sky: Sky, jd: float, count: int) -> list[float]:
    """The new moon at or before `jd` and the `count - 1` before it (latest
    first)."""
    out = [astro.previous_crossing(sky.elongation, astro.ELONGATION, 360.0, jd)]
    while len(out) < count:
        out.append(astro.previous_crossing(sky.elongation, astro.ELONGATION, 360.0, out[-1] - 1.0))
    return out


def lunar_month(
    sky: Sky,
    frame: SauraFrame,
    new_moons: list[float],
    next_new_moon: float,
    paksha: Paksha,
    tz: ZoneInfo,
) -> LunarMonth:
    """`new_moons[0]` begins the current amanta month; the rest go back in
    time (at least 14 for the year search)."""
    signs = [saura_sign(sky, frame, nm) for nm in new_moons]
    s_next = saura_sign(sky, frame, next_new_moon)
    # month i (0 = current) is named after the saura sign at its new moon;
    # it is adhika when the following new moon falls in the same saura month.
    following = [s_next, *signs[:-1]]
    names = [saura_month_of_sign(s) for s in signs]
    adhika = [signs[i] == following[i] for i in range(len(signs))]
    suppressed = saura_month_of_sign(signs[1] + 1) if (signs[0] - signs[1]) % 12 == 2 else None
    if paksha is Paksha.SHUKLA or adhika[0]:
        purnimanta, purnimanta_adhika = names[0], adhika[0]
    else:
        purnimanta, purnimanta_adhika = saura_month_of_sign(s_next), False
    saka: int | None = None
    vikrama: int | None = None
    reason: PanchangReason | None = None
    for i, name in enumerate(names[:-1]):
        if name is MonthName.CHAITRA:
            if adhika[i] or (names[i + 1] is MonthName.CHAITRA and adhika[i + 1]):
                reason = PanchangReason.YEAR_START_ADHIKA_CHAITRA
            else:
                start_local = to_instant(new_moons[i], tz).local.date()
                saka = start_local.year - 78
                vikrama = saka + 135
            break
    return LunarMonth(
        saura_frame=frame,
        amanta_month=names[0],
        amanta_adhika=adhika[0],
        purnimanta_month=purnimanta,
        purnimanta_adhika=purnimanta_adhika,
        paksha=paksha,
        suppressed_month_before=suppressed,
        month_start_new_moon=to_instant(new_moons[0], tz),
        month_end_new_moon=to_instant(next_new_moon, tz),
        saka_year_expired=saka,
        vikrama_year_chaitradi_expired=vikrama,
        year_reason=reason,
    )


def day_parts(
    weekday: int, sunrise: float, sunset: float, next_sunrise: float, tz: ZoneInfo
) -> tuple[DayPart, ...]:
    day_len = (sunset - sunrise) / 8.0
    night_len = (next_sunrise - sunset) / 8.0

    def part(kind: DayPartKind, period: str, k: int, label: EvidenceLabel) -> DayPart:
        base, length = (sunrise, day_len) if period == "day" else (sunset, night_len)
        return DayPart(
            kind=kind,
            period=period,
            part=k,
            start=to_instant(base + (k - 1) * length, tz),
            end=to_instant(base + k * length, tz),
            evidence_label=label,
        )

    day_lords = [WEEKDAY_LORD[(weekday + i) % 7] for i in range(8)]
    night_lords = [WEEKDAY_LORD[(weekday + 4 + i) % 7] for i in range(8)]
    gulika_day = day_lords.index(CelestialBody.SATURN) + 1
    gulika_night = night_lords.index(CelestialBody.SATURN) + 1
    return (
        part(DayPartKind.RAHU_KALAM, "day", RAHU_KALAM_DAY_PART[weekday],
             EvidenceLabel.TRANSLATOR_NOTE),
        part(DayPartKind.YAMAGANDA, "day", YAMAGANDA_DAY_PART[weekday],
             EvidenceLabel.SOURCE_SUPPORTED),
        part(DayPartKind.GULIKA_KALAM, "day", gulika_day, EvidenceLabel.SOURCE_SUPPORTED),
        part(DayPartKind.GULIKA_KALAM, "night", gulika_night, EvidenceLabel.TRANSLATOR_NOTE),
    )  # fmt: skip


def horas(weekday: int, sunrise: float, next_sunrise: float, tz: ZoneInfo) -> tuple[Hora, ...]:
    hour = 1.0 / 24.0
    count = math.ceil((next_sunrise - sunrise) / hour - 1e-9)
    lords = hora_sequence(WEEKDAY_LORD[weekday], count)
    out = []
    for i, lord in enumerate(lords):
        start = sunrise + i * hour
        end = min(start + hour, next_sunrise)
        out.append(
            Hora(
                number=i + 1,
                lord=lord,
                start=to_instant(start, tz),
                end=to_instant(end, tz),
                truncated_by_next_sunrise=end < start + hour - 1e-9,
            )
        )
    return tuple(out)


def nakshatra_panchaka(
    sky: Sky, sunrise: float, next_sunrise: float, tz: ZoneInfo
) -> tuple[Interval, ...]:
    """The Moon from 300 degrees (Dhanishta, third quarter) to 360 degrees
    sidereal, clipped to the day (PC-21)."""

    def shifted(jd: float) -> float:
        return (sky.moon_sidereal(jd) - _NAKSHATRA_PANCHAKA_START) % 360.0

    inside = shifted(sunrise) < 60.0
    if inside:
        start = astro.previous_crossing(shifted, astro.MOON, 360.0, sunrise)
    else:
        start, _ = astro.next_crossing(shifted, astro.MOON, 360.0, sunrise)
        if start >= next_sunrise:
            return ()
    end, _ = astro.next_crossing(sky.moon_sidereal, astro.MOON, 360.0, max(start, sunrise))
    return (
        Interval(
            start=to_instant(start, tz),
            end=to_instant(end, tz),
            starts_before_day=start < sunrise,
            ends_after_day=end > next_sunrise,
        ),
    )


def _provenance() -> tuple[ProvenanceEntry, ...]:
    return tuple(
        ProvenanceEntry(
            entry_id=p.entry_id,
            item=p.item,
            evidence_label=p.label,
            statement=p.statement,
            references=p.references,
        )
        for p in PROVENANCE
    )


class PanchangService:
    """Stateless facade for the daily Panchang."""

    def __init__(self, ephemeris_path: str | None = _UNSET) -> None:  # type: ignore[assignment]
        resolved = Settings().ephemeris_path if ephemeris_path is _UNSET else ephemeris_path
        ephemeris.configure_ephemeris_path(resolved)

    def daily(self, request: PanchangRequest) -> DailyPanchang:
        tz = timezones.resolve_timezone(request.timezone)
        sky = Sky(allow_moshier_fallback=request.allow_moshier_fallback)
        frame = DayFrame(
            date=request.date,
            location=request.location,
            tz=tz,
            convention=request.sunrise_convention,
        )
        base = dict(
            system=PANCHANG_SYSTEM_ID,
            standards_version=PANCHANG_STANDARDS_VERSION,
            engine_version=__version__,
            profile_id=PANCHANG_PROFILE_ID,
            regional_convention=request.regional_convention,
            sunrise_convention=request.sunrise_convention,
            hora_profile_id=HORA_PROFILE_ID,
            day_part_profile_id=DAY_PART_PROFILE_ID,
            date=request.date,
            location=request.location,
            timezone=request.timezone,
            ayanamsa="lahiri",
            saura_frame=request.saura_frame,
            not_implemented=NOT_IMPLEMENTED,
            provenance=_provenance(),
        )
        if not frame.complete:
            reason = (
                PanchangReason.SUNRISE_NOT_OCCURRING
                if frame.sunrise is None or frame.next_sunrise is None
                else PanchangReason.SUNSET_NOT_OCCURRING
            )
            return DailyPanchang(
                **base,  # type: ignore[arg-type]
                status=PanchangStatus.NOT_EVALUABLE,
                reason=reason,
                sunrise=self._rise_set(frame.sunrise, tz, circumpolar=True),
                sunset=self._rise_set(frame.sunset, tz, circumpolar=True),
                next_sunrise=self._rise_set(frame.next_sunrise, tz, circumpolar=True),
                moonrise=RiseSet(status=EventStatus.NO_EVENT_IN_DAY),
                moonset=RiseSet(status=EventStatus.NO_EVENT_IN_DAY),
                warnings=("no sunrise-to-sunrise day at this location and date",),
            )
        sr, ss, nsr = frame.sunrise, frame.sunset, frame.next_sunrise
        assert sr is not None and ss is not None and nsr is not None
        weekday = sunday_zero_weekday(request.date)
        mode = ephemeris.calculate_body(
            sr,
            ephemeris.SWE_BODY_ID["sun"],
            sidereal=False,
            allow_moshier_fallback=request.allow_moshier_fallback,
        ).mode

        tithis = element_spans(
            ElementKind.TITHI, sky.elongation, astro.ELONGATION, TITHI_SPAN_DEGREES,
            lambda i: tithi_name(i).value, sr, nsr, tz,
        )  # fmt: skip
        nakshatras = element_spans(
            ElementKind.NAKSHATRA, sky.moon_sidereal, astro.MOON, NAKSHATRA_SPAN_DEGREES,
            lambda i: NAKSHATRA_ORDER[i - 1].value, sr, nsr, tz,
        )  # fmt: skip
        yogas = element_spans(
            ElementKind.YOGA, sky.yoga_sum, astro.YOGA, YOGA_SPAN_DEGREES,
            lambda i: tuple(YogaName)[i - 1].value, sr, nsr, tz,
        )  # fmt: skip
        karanas = element_spans(
            ElementKind.KARANA, sky.elongation, astro.ELONGATION, KARANA_SPAN_DEGREES,
            lambda i: karana_name(i).value, sr, nsr, tz,
        )  # fmt: skip
        t0 = tithis[0].index
        paksha = tithi_paksha(t0)
        new_moons = new_moons_back(sky, sr, 15)
        next_nm, _ = astro.next_crossing(sky.elongation, astro.ELONGATION, 360.0, sr)
        months = tuple(lunar_month(sky, f, new_moons, next_nm, paksha, tz) for f in SauraFrame)
        bhadra = tuple(
            Interval(
                start=k.start,
                end=k.end,
                starts_before_day=k.current_at_sunrise and k.start.julian_day_ut < sr,
                ends_after_day=k.current_at_next_sunrise,
            )
            for k in karanas
            if k.name == KaranaName.VISHTI.value
        )
        return DailyPanchang(
            **base,  # type: ignore[arg-type]
            status=PanchangStatus.SUCCESS,
            ephemeris_mode=mode,
            sunrise=self._rise_set(sr, tz, circumpolar=False),
            sunset=self._rise_set(ss, tz, circumpolar=False),
            next_sunrise=self._rise_set(nsr, tz, circumpolar=False),
            moonrise=self._moon(request, "rise", sr, nsr, tz),
            moonset=self._moon(request, "set", sr, nsr, tz),
            vara=Vara(weekday=WEEKDAY_ORDER[weekday], lord=WEEKDAY_LORD[weekday]),
            tithi_at_sunrise=TithiInfo(
                index=t0,
                name=tithi_name(t0),
                paksha=paksha,
                number_in_paksha=tithi_number_in_paksha(t0),
            ),
            tithis=tithis,
            nakshatras=nakshatras,
            yogas=yogas,
            karanas=karanas,
            lunar_month=next(m for m in months if m.saura_frame is request.saura_frame),
            lunar_months=months,
            day_parts=day_parts(weekday, sr, ss, nsr, tz),
            horas=horas(weekday, sr, nsr, tz),
            nakshatra_panchaka=nakshatra_panchaka(sky, sr, nsr, tz),
            bhadra=bhadra,
            warnings=(
                ("Moshier analytical ephemeris used (no Swiss Ephemeris data files configured)",)
                if mode.value == "moshier"
                else ()
            ),
        )

    @staticmethod
    def _rise_set(jd: float | None, tz: ZoneInfo, *, circumpolar: bool) -> RiseSet:
        if jd is None:
            return RiseSet(
                status=EventStatus.CIRCUMPOLAR_NO_EVENT
                if circumpolar
                else EventStatus.NO_EVENT_IN_DAY
            )
        return RiseSet(status=EventStatus.OCCURRED, instant=to_instant(jd, tz))

    @staticmethod
    def _moon(
        request: PanchangRequest, event: str, sunrise: float, next_sunrise: float, tz: ZoneInfo
    ) -> RiseSet:
        occurred, jd = ephemeris.rise_or_set_with_convention(
            sunrise,
            body="moon",
            event=event,
            convention=MOONRISE_SWISS_CONVENTION,
            longitude=request.location.longitude,
            latitude=request.location.latitude,
            altitude_meters=request.location.altitude_meters,
        )
        if not occurred or jd is None:
            return RiseSet(status=EventStatus.CIRCUMPOLAR_NO_EVENT)
        if jd >= next_sunrise:
            return RiseSet(status=EventStatus.NO_EVENT_IN_DAY)
        return RiseSet(status=EventStatus.OCCURRED, instant=to_instant(jd, tz))


__all__ = ["PanchangService", "DayFrame", "to_instant", "jd_of"]
