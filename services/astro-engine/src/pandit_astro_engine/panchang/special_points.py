"""Sunrise-dependent special points (Phase 10; `docs/ASTROLOGY_STANDARDS.md`
v1.23.0, PC-25 to PC-30).

    SpecialPointsRequest -> SpecialPointsService.calculate -> SpecialPointsFacts

Sun-based upagrahas (two BPHS readings), Gulika and Mandi (three readings,
never assumed identical), Bhava, Hora and Ghatika Lagnas, Varnada Lagna and
Pranapada (two Sun readings). Longitudes are sidereal (Lahiri); every value
carries the profile that produced it. Facts only: no effects are attached.
"""

from __future__ import annotations

import datetime as dt
from enum import Enum
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict

from pandit_astro_engine import ephemeris, timezones
from pandit_astro_engine._version import __version__
from pandit_astro_engine.config import Settings
from pandit_astro_engine.models import CelestialBody, LocalDateTimeInput, Location
from pandit_astro_engine.panchang.astro import Sky
from pandit_astro_engine.panchang.constants import GHATI_MINUTES, PALA_SECONDS, WEEKDAY_LORD
from pandit_astro_engine.panchang.models import Instant
from pandit_astro_engine.panchang.profiles import (
    PANCHANG_STANDARDS_VERSION,
    PANCHANG_SYSTEM_ID,
    EvidenceLabel,
    GulikaProfile,
    PranapadaSunReading,
    SunriseConvention,
    UpagrahaProfile,
)
from pandit_astro_engine.panchang.service import DayFrame, jd_of, sunday_zero_weekday, to_instant
from pandit_astro_engine.rashi import RASHI_MODALITY, Modality, Rashi, rashi_from_longitude

_UNSET = object()
_DHOOMA_OFFSET = 133.0 + 1.0 / 3.0  # 4 signs 13 deg 20 min
_NOTE_OFFSET = 53.0 + 1.0 / 3.0  # 53 deg 20 min (translator's note)
_UPAKETU_OFFSET = 16.0 + 2.0 / 3.0  # 16 deg 40 min
#: Phaladeepika Ch. 25 sl. 2: end of Mandi in ghatis of a 30-ghati day or
#: night, Sunday first.
MANDI_DAY_GHATIS = (26, 22, 18, 14, 10, 6, 2)
MANDI_NIGHT_GHATIS = (10, 6, 2, 26, 22, 18, 14)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PointStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"


class PointReason(str, Enum):
    SUNRISE_NOT_OCCURRING = "sunrise_not_occurring"


class SpecialPointsRequest(_Model):
    local_datetime: LocalDateTimeInput
    location: Location
    sunrise_convention: SunriseConvention = SunriseConvention.CRC_1955_CENTRE_REFRACTION_30
    allow_moshier_fallback: bool = True


class Point(_Model):
    name: str
    profile: str
    status: PointStatus
    longitude: float | None = None
    sign: Rashi | None = None
    moment: Instant | None = None
    reason: PointReason | None = None
    evidence_label: EvidenceLabel


class SpecialPointsFacts(_Model):
    system: str
    standards_version: str
    engine_version: str
    sunrise_convention: SunriseConvention
    ayanamsa: str
    instant: Instant
    status: PointStatus
    reason: PointReason | None = None
    hindu_day_sunrise: Instant | None = None
    sunset: Instant | None = None
    next_sunrise: Instant | None = None
    is_daytime: bool | None = None
    weekday_lord: CelestialBody | None = None
    ghatis_since_sunrise: float | None = None
    natal_lagna: float | None = None
    points: tuple[Point, ...] = ()
    warnings: tuple[str, ...] = ()


def _ok(
    name: str, profile: str, lon: float, label: EvidenceLabel, moment: Instant | None = None
) -> Point:
    lon %= 360.0
    return Point(
        name=name,
        profile=profile,
        status=PointStatus.SUCCESS,
        longitude=lon,
        sign=rashi_from_longitude(lon),
        moment=moment,
        evidence_label=label,
    )


def upagrahas(sun: float) -> tuple[Point, ...]:
    out = []
    for profile, label in (
        (UpagrahaProfile.BPHS_VERSE, EvidenceLabel.SOURCE_SUPPORTED),
        (UpagrahaProfile.BPHS_TRANSLATOR_NOTE, EvidenceLabel.TRANSLATOR_NOTE),
    ):
        dhooma = (sun + _DHOOMA_OFFSET) % 360.0
        if profile is UpagrahaProfile.BPHS_VERSE:
            vyatipata = (360.0 - dhooma) % 360.0
        else:
            vyatipata = (dhooma + _NOTE_OFFSET) % 360.0
        parivesha = (vyatipata + 180.0) % 360.0
        if profile is UpagrahaProfile.BPHS_VERSE:
            indrachapa = (360.0 - parivesha) % 360.0
        else:
            indrachapa = (parivesha - _NOTE_OFFSET) % 360.0
        upaketu = (indrachapa + _UPAKETU_OFFSET) % 360.0
        for name, value in (
            ("dhooma", dhooma),
            ("vyatipata", vyatipata),
            ("parivesha", parivesha),
            ("indrachapa", indrachapa),
            ("upaketu", upaketu),
        ):
            out.append(_ok(name, profile.value, value, label))
    return tuple(out)


def varnada_sign(lagna_sign: int, hora_lagna_sign: int) -> int:
    """BPHS Ch. 5 v. 10-13 as translated: count Aries-to-sign for an odd
    sign, Pisces-backwards-to-sign for an even sign; add the counts when
    both are odd or both even, else take their difference; count the result
    from Aries (odd) or backwards from Pisces (even). A difference is taken
    only when the counts differ in parity, so the result is never zero."""

    def count(sign: int) -> int:
        return sign + 1 if sign % 2 == 0 else 12 - sign

    a, b = count(lagna_sign), count(hora_lagna_sign)
    n = a + b if a % 2 == b % 2 else abs(a - b)
    return (n - 1) % 12 if n % 2 == 1 else (12 - n) % 12


def pranapada(sun: float, palas: float) -> float:
    base = {Modality.MOVABLE: 0.0, Modality.FIXED: 240.0, Modality.DUAL: 120.0}[
        RASHI_MODALITY[rashi_from_longitude(sun)]
    ]
    return (sun + base + palas * 2.0) % 360.0


class SpecialPointsService:
    """Stateless facade for the special points."""

    def __init__(self, ephemeris_path: str | None = _UNSET) -> None:  # type: ignore[assignment]
        resolved = Settings().ephemeris_path if ephemeris_path is _UNSET else ephemeris_path
        ephemeris.configure_ephemeris_path(resolved)

    def calculate(self, request: SpecialPointsRequest) -> SpecialPointsFacts:
        tz = timezones.resolve_timezone(request.local_datetime.timezone)
        utc, _resolution = timezones.resolve_local_datetime(request.local_datetime)
        jd = jd_of(utc)
        sky = Sky(allow_moshier_fallback=request.allow_moshier_fallback)
        local_date = utc.astimezone(tz).date()
        frame = self._frame(local_date, request, tz)
        if frame is not None and frame.sunrise is not None and jd < frame.sunrise:
            frame = self._frame(local_date - dt.timedelta(days=1), request, tz)
        base = dict(
            system=PANCHANG_SYSTEM_ID,
            standards_version=PANCHANG_STANDARDS_VERSION,
            engine_version=__version__,
            sunrise_convention=request.sunrise_convention,
            ayanamsa="lahiri",
            instant=to_instant(jd, tz),
        )
        if frame is None or not frame.complete:
            return SpecialPointsFacts(
                **base,  # type: ignore[arg-type]
                status=PointStatus.NOT_EVALUABLE,
                reason=PointReason.SUNRISE_NOT_OCCURRING,
            )
        sr, ss, nsr = frame.sunrise, frame.sunset, frame.next_sunrise
        assert sr is not None and ss is not None and nsr is not None
        weekday = sunday_zero_weekday(frame.date)
        is_day = sr <= jd < ss
        loc = request.location
        sun_now = sky.sun_sidereal(jd)
        sun_rise = sky.sun_sidereal(sr)
        minutes = (jd - sr) * 1440.0
        ghatis = minutes / GHATI_MINUTES
        palas = minutes * 60.0 / PALA_SECONDS
        lagna = sky.ascendant_sidereal(jd, latitude=loc.latitude, longitude=loc.longitude)

        points = list(upagrahas(sun_now))
        points.extend(self._gulika(sky, request, tz, weekday, is_day, sr, ss, nsr))
        bhava = sun_rise + 30.0 * ghatis / 5.0
        hora = sun_rise + 30.0 * ghatis / 2.5
        ghatika = sun_rise + 30.0 * ghatis
        label = EvidenceLabel.SOURCE_SUPPORTED
        points.append(_ok("bhava_lagna", "bphs_ch5", bhava, label))
        points.append(_ok("hora_lagna", "bphs_ch5", hora, label))
        points.append(_ok("ghatika_lagna", "bphs_ch5", ghatika, label))
        varnada = varnada_sign(int(lagna // 30.0) % 12, int((hora % 360.0) // 30.0) % 12)
        points.append(
            Point(
                name="varnada_lagna",
                profile="bphs_ch5_v10_13",
                status=PointStatus.SUCCESS,
                sign=tuple(Rashi)[varnada],
                evidence_label=label,
            )
        )
        points.append(
            _ok(
                "pranapada",
                PranapadaSunReading.SUN_AT_GIVEN_TIME.value,
                pranapada(sun_now, palas),
                EvidenceLabel.INFERENCE,
            )
        )
        points.append(
            _ok(
                "pranapada",
                PranapadaSunReading.SUN_AT_SUNRISE.value,
                pranapada(sun_rise, palas),
                EvidenceLabel.INFERENCE,
            )
        )
        return SpecialPointsFacts(
            **base,  # type: ignore[arg-type]
            status=PointStatus.SUCCESS,
            hindu_day_sunrise=to_instant(sr, tz),
            sunset=to_instant(ss, tz),
            next_sunrise=to_instant(nsr, tz),
            is_daytime=is_day,
            weekday_lord=WEEKDAY_LORD[weekday],
            ghatis_since_sunrise=ghatis,
            natal_lagna=lagna,
            points=tuple(points),
        )

    @staticmethod
    def _frame(date: dt.date, request: SpecialPointsRequest, tz: ZoneInfo) -> DayFrame | None:
        frame = DayFrame(
            date=date,
            location=request.location,
            tz=tz,
            convention=request.sunrise_convention,
        )
        return frame if frame.sunrise is not None else None

    @staticmethod
    def _gulika(
        sky: Sky,
        request: SpecialPointsRequest,
        tz: ZoneInfo,
        weekday: int,
        is_day: bool,
        sr: float,
        ss: float,
        nsr: float,
    ) -> list[Point]:
        loc = request.location
        if is_day:
            base, length = sr, ss - sr
            lords = [WEEKDAY_LORD[(weekday + i) % 7] for i in range(8)]
            mandi_ghatis = MANDI_DAY_GHATIS[weekday]
        else:
            base, length = ss, nsr - ss
            lords = [WEEKDAY_LORD[(weekday + 4 + i) % 7] for i in range(8)]
            mandi_ghatis = MANDI_NIGHT_GHATIS[weekday]
        k = lords.index(CelestialBody.SATURN)
        moments = (
            (GulikaProfile.GULIKA_PORTION_START_BPHS_TRANSLATION, base + k * length / 8.0,
             EvidenceLabel.TRANSLATOR_NOTE),
            (GulikaProfile.GULIKA_PORTION_END, base + (k + 1) * length / 8.0,
             EvidenceLabel.TRANSLATOR_NOTE),
            (GulikaProfile.MANDI_PHALADEEPIKA_GHATI_TABLE, base + mandi_ghatis / 30.0 * length,
             EvidenceLabel.SOURCE_SUPPORTED),
        )  # fmt: skip
        out = []
        for profile, moment, label in moments:
            asc = sky.ascendant_sidereal(moment, latitude=loc.latitude, longitude=loc.longitude)
            name = "mandi" if profile is GulikaProfile.MANDI_PHALADEEPIKA_GHATI_TABLE else "gulika"
            out.append(_ok(name, profile.value, asc, label, to_instant(moment, tz)))
        return out
