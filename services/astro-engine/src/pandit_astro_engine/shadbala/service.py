"""Shadbala facts (Phase 9 WP-F; `docs/ASTROLOGY_STANDARDS.md` v1.16.0,
SB-01 to SB-20).

    ShadbalaRequest -> ShadbalaService.calculate -> ShadbalaFacts

Positions, Lagna and varga signs come from the Phase 5 Kundli under the
Vedic default profile (sidereal, Lahiri, whole-sign houses); the sidereal MC,
sunrise/sunset and the equation of time come from the Phase 4 adapter. No
new astronomy is introduced, and no component is filled from a translator's
note, a modern method or a default when BPHS Ch. 27 as read does not fix it.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from pandit_astro_engine import ephemeris
from pandit_astro_engine._version import __version__
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    Ayanamsa,
    CalculationConfig,
    CelestialBody,
    EphemerisMode,
    Location,
    TimeResolution,
)
from pandit_astro_engine.rashi import Rashi, rashi_from_longitude
from pandit_astro_engine.service import AstronomicalCalculationService
from pandit_astro_engine.shadbala import components as calc
from pandit_astro_engine.shadbala.constants import (
    DIG_BALA_ZERO_POINT,
    SAPTAVARGA,
    SHADBALA_BODIES,
    SHADBALA_STANDARDS_VERSION,
    SHADBALA_SYSTEM_ID,
    Angle,
)
from pandit_astro_engine.shadbala.models import (
    ComponentProvenance,
    ComponentResult,
    ComponentStatus,
    DayNight,
    PlanetShadbala,
    SaptavargaPlacement,
    ShadbalaFacts,
    ShadbalaReason,
    ShadbalaRequest,
    ShadbalaTimePrecision,
)
from pandit_astro_engine.shadbala.profiles import (
    COMPONENTS,
    KALA_PARTS,
    SIX_BALAS,
    STHANA_PARTS,
    Component,
    EvidenceLabel,
)
from pandit_astro_engine.vargas import calculate_varga_sign

_UNSET = object()

#: Leaf components summed into the labelled partial subtotal.
LEAF_COMPONENTS: tuple[Component, ...] = (
    *STHANA_PARTS,
    Component.DIG,
    *KALA_PARTS,
    Component.CHESHTA,
    Component.NAISARGIKA,
    Component.DRIK,
)

_STARRY = (
    CelestialBody.MARS,
    CelestialBody.MERCURY,
    CelestialBody.JUPITER,
    CelestialBody.VENUS,
    CelestialBody.SATURN,
)


def _ok(component: Component, virupas: float) -> ComponentResult:
    return ComponentResult(
        component=component,
        status=ComponentStatus.SUCCESS,
        virupas=virupas,
        evidence_label=COMPONENTS[component].label,
    )


def _ne(component: Component, reason: ShadbalaReason, detail: str | None = None) -> ComponentResult:
    return ComponentResult(
        component=component,
        status=ComponentStatus.NOT_EVALUABLE,
        reason=reason,
        detail=detail,
        evidence_label=COMPONENTS[component].label,
    )


@dataclass(frozen=True)
class _SolarFrame:
    is_day: bool
    start: float
    end: float
    third: int
    last_sunrise: float


def _straddle(jd: float, event: str, location: Location) -> tuple[float, float] | None:
    """(last event <= jd, next event > jd) for 'rise' or 'set'; None if the
    event does not occur near jd (polar day or night)."""
    start = jd - 2.0
    previous: float | None = None
    for _ in range(8):
        occurred, when = ephemeris.rise_or_set(
            start,
            event=event,
            longitude=location.longitude,
            latitude=location.latitude,
            altitude_meters=location.altitude_meters,
        )
        if not occurred or when is None:
            return None
        if when > jd:
            return (previous, when) if previous is not None else None
        previous = when
        start = when + 0.001
    return None  # pragma: no cover - defensive


def _solar_frame(jd: float, location: Location) -> _SolarFrame | None:
    rises = _straddle(jd, "rise", location)
    sets = _straddle(jd, "set", location)
    if rises is None or sets is None:
        return None
    last_rise, next_rise = rises
    last_set, next_set = sets
    is_day = last_rise > last_set
    start, end = (last_rise, next_set) if is_day else (last_set, next_rise)
    if not start <= jd < end:  # pragma: no cover - defensive
        return None
    third = min(int(3.0 * (jd - start) / (end - start)) + 1, 3)
    return _SolarFrame(is_day, start, end, third, last_rise)


def _weekday_of(jd_ut: float, timezone: str) -> int:
    year, month, day, hour, minute, second = ephemeris.julian_day_to_utc_datetime_parts(jd_ut)
    utc = dt.datetime(year, month, day, hour, minute, int(second), tzinfo=dt.timezone.utc)
    local = utc.astimezone(ZoneInfo(timezone))
    return (local.weekday() + 1) % 7


def _apparent_solar_hours(jd_ut: float, longitude: float) -> float:
    ut_hours = ((jd_ut + 0.5) % 1.0) * 24.0
    return (ut_hours + longitude / 15.0 + ephemeris.equation_of_time_days(jd_ut) * 24.0) % 24.0


class ShadbalaService:
    """Stateless facade, like the other astro-engine services."""

    def __init__(self, ephemeris_path: str | None = _UNSET) -> None:  # type: ignore[assignment]
        astro = (
            AstronomicalCalculationService()
            if ephemeris_path is _UNSET
            else AstronomicalCalculationService(ephemeris_path=ephemeris_path)
        )
        self._kundli = KundliCalculationService(astro)

    def calculate(self, request: ShadbalaRequest) -> ShadbalaFacts:
        config = CalculationConfig(
            node_convention=request.node_convention,
            allow_moshier_fallback=request.allow_moshier_fallback,
        )
        kundli = self._kundli.calculate(
            AstronomicalCalculationRequest(
                local_datetime=request.local_datetime,
                location=request.location,
                config=config,
                include_solar_events=False,
            )
        )
        jd = kundli.astronomical.metadata.time_resolution.julian_day_ut
        longitudes = {p.body: p.longitude for p in kundli.planets}
        signs = {b: rashi_from_longitude(lon) for b, lon in longitudes.items()}
        exact = request.time_precision is ShadbalaTimePrecision.EXACT

        warnings: list[str] = []
        if kundli.astronomical.metadata.ephemeris_mode is EphemerisMode.MOSHIER:
            warnings.append(
                "Moshier analytical ephemeris used (no Swiss Ephemeris data files configured)"
            )
        warnings.append(
            "no Shadbala Pinda is produced: Abda, Masa, Hora, Ayana, Yuddha, Drik and the "
            "Cheshta Bala of the Sun and of Mars to Saturn are not evaluable under BPHS Ch. 27 "
            "as read; evaluated_subtotal_virupas is a partial sum only"
        )

        if not exact:
            warnings.insert(
                0,
                "birth time unknown: every component except Naisargika Bala is not evaluated",
            )
            planets = tuple(self._unknown_time(body) for body in SHADBALA_BODIES)
            return self._facts(
                request, kundli.astronomical.metadata.time_resolution, planets, warnings
            )

        ephemeris.set_sidereal_mode(Ayanamsa.LAHIRI)
        _asc, mc = ephemeris.calculate_sidereal_angles(
            jd, latitude=request.location.latitude, longitude=request.location.longitude
        )
        lagna = kundli.lagna_longitude
        angles = {
            Angle.ASCENDANT: lagna,
            Angle.DESCENDANT: (lagna + 180.0) % 360.0,
            Angle.MERIDIAN: mc,
            Angle.NADIR: (mc + 180.0) % 360.0,
        }
        solar_hours = _apparent_solar_hours(jd, request.location.longitude)
        unnata = calc.unnata_ghatis(solar_hours)
        frame = _solar_frame(jd, request.location)
        weekday = (
            _weekday_of(frame.last_sunrise, request.local_datetime.timezone)
            if frame is not None
            else None
        )
        if frame is None:
            warnings.append(
                "no sunrise/sunset near the birth instant: Tribhaga and Vara not evaluated"
            )

        planets = tuple(
            self._planet(
                body, longitudes, signs, rashi_from_longitude(lagna), angles, unnata, frame, weekday
            )
            for body in SHADBALA_BODIES
        )
        facts = self._facts(
            request, kundli.astronomical.metadata.time_resolution, planets, warnings
        )
        return facts.model_copy(
            update={
                "lagna_longitude": lagna,
                "midheaven_longitude": mc,
                "apparent_solar_hours": solar_hours,
                "unnata_ghatis": unnata,
                "day_night": DayNight(
                    status=ComponentStatus.SUCCESS,
                    is_day=frame.is_day,
                    period_start_julian_day_ut=frame.start,
                    period_end_julian_day_ut=frame.end,
                    third=frame.third,
                    vara_weekday_sunday_zero=weekday,
                )
                if frame is not None
                else DayNight(status=ComponentStatus.NOT_EVALUABLE),
            }
        )

    # -- assembly -----------------------------------------------------------

    @staticmethod
    def _facts(
        request: ShadbalaRequest,
        time_resolution: TimeResolution,
        planets: tuple[PlanetShadbala, ...],
        warnings: list[str],
    ) -> ShadbalaFacts:
        return ShadbalaFacts(
            system=SHADBALA_SYSTEM_ID,
            standards_version=SHADBALA_STANDARDS_VERSION,
            engine_version=__version__,
            time_precision=request.time_precision,
            time_resolution=time_resolution,
            location=request.location,
            ayanamsa=Ayanamsa.LAHIRI.value,
            node_convention=request.node_convention,
            lagna_longitude=None,
            midheaven_longitude=None,
            apparent_solar_hours=None,
            unnata_ghatis=None,
            day_night=DayNight(status=ComponentStatus.NOT_EVALUABLE),
            planets=planets,
            provenance=tuple(
                ComponentProvenance(
                    component=d.component,
                    evidence_label=d.label,
                    statement=d.title,
                    reference=d.reference,
                )
                for d in COMPONENTS.values()
            ),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _unknown_time(body: CelestialBody) -> PlanetShadbala:
        results = [
            _ok(c, calc.naisargika_bala(body))
            if c is Component.NAISARGIKA
            else _ne(c, ShadbalaReason.BIRTH_TIME_UNKNOWN)
            for c in LEAF_COMPONENTS
        ]
        return _assemble(body, results, ())

    @staticmethod
    def _planet(
        body: CelestialBody,
        longitudes: dict[CelestialBody, float],
        signs: dict[CelestialBody, Rashi],
        lagna_sign: Rashi,
        angles: dict[Angle, float],
        unnata: float,
        frame: _SolarFrame | None,
        weekday: int | None,
    ) -> PlanetShadbala:
        lon = longitudes[body]
        degree = lon % 30.0
        results: list[ComponentResult] = []

        # Sthana Bala
        results.append(_ok(Component.UCHCHA, calc.uchcha_bala(body, lon)))
        placements: list[SaptavargaPlacement] = []
        sapta_total = 0.0
        blocked = False
        for varga in SAPTAVARGA:
            sign = calculate_varga_sign(varga, lon)
            category = calc.saptavarga_category(body, varga, sign, degree, signs)
            virupas = calc.saptavarga_virupas(category) if category is not None else None
            placements.append(
                SaptavargaPlacement(varga=varga, sign=sign, category=category, virupas=virupas)
            )
            if virupas is None:
                blocked = True
            else:
                sapta_total += virupas
        if blocked:
            results.append(
                _ne(
                    Component.SAPTAVARGAJA,
                    ShadbalaReason.D1_MOOLATRIKONA_SIGN_VERSUS_DEGREE,
                    "the Rasi chart places the planet in its Moolatrikona sign outside the "
                    "Ch. 3 v. 51-54 degree range",
                )
            )
        else:
            results.append(_ok(Component.SAPTAVARGAJA, sapta_total))
        d9 = calculate_varga_sign(9, lon)
        results.append(_ok(Component.OJAYUGMA, calc.ojayugma_bala(body, signs[body], d9)))
        results.append(_ok(Component.KENDRADI, calc.kendradi_bala(lagna_sign, signs[body])))
        results.append(_ok(Component.DREKKANA, calc.drekkana_bala(body, degree)))

        # Dig Bala
        results.append(_ok(Component.DIG, calc.dig_bala(lon, angles[DIG_BALA_ZERO_POINT[body]])))

        # Kala Bala
        results.append(_ok(Component.NATHONNATHA, calc.nathonnatha_bala(body, unnata)))
        paksha = _paksha(body, longitudes, signs)
        results.append(paksha)
        if frame is None:
            results.append(_ne(Component.TRIBHAGA, ShadbalaReason.SUNRISE_UNAVAILABLE))
        else:
            results.append(
                _ok(Component.TRIBHAGA, calc.tribhaga_bala(body, frame.is_day, frame.third))
            )
        results.append(_ne(Component.ABDA, ShadbalaReason.YEAR_MONTH_LORD_METHOD_UNVERIFIED))
        results.append(_ne(Component.MASA, ShadbalaReason.YEAR_MONTH_LORD_METHOD_UNVERIFIED))
        if weekday is None:
            results.append(_ne(Component.VARA, ShadbalaReason.SUNRISE_UNAVAILABLE))
        else:
            results.append(_ok(Component.VARA, calc.vara_bala(body, weekday)))
        results.append(_ne(Component.HORA, ShadbalaReason.HORA_METHOD_NOT_LOCKED))
        results.append(_ne(Component.AYANA, ShadbalaReason.AYANA_METHOD_CONFLICT))
        if body in _STARRY:
            results.append(_ne(Component.YUDDHA, ShadbalaReason.PLANETARY_WAR_UNDEFINED))
        else:
            results.append(
                ComponentResult(
                    component=Component.YUDDHA,
                    status=ComponentStatus.NOT_APPLICABLE,
                    detail="planetary war is between planets from Mars to Saturn (v. 20)",
                    evidence_label=COMPONENTS[Component.YUDDHA].label,
                )
            )

        # Cheshta Bala (v. 18: the Moon's is her Paksha Bala; the Sun's his Ayana Bala)
        if body is CelestialBody.MOON:
            if paksha.status is ComponentStatus.SUCCESS and paksha.virupas is not None:
                results.append(_ok(Component.CHESHTA, paksha.virupas))
            else:
                results.append(
                    _ne(Component.CHESHTA, paksha.reason or ShadbalaReason.MOON_PHASE_BOUNDARY)
                )
        elif body is CelestialBody.SUN:
            results.append(
                _ne(Component.CHESHTA, ShadbalaReason.AYANA_METHOD_CONFLICT, "Sun: Ayana Bala")
            )
        else:
            results.append(_ne(Component.CHESHTA, ShadbalaReason.CHESHTA_METHOD_CONFLICT))

        results.append(_ok(Component.NAISARGIKA, calc.naisargika_bala(body)))
        results.append(_ne(Component.DRIK, ShadbalaReason.DRIK_FORMULA_AMBIGUOUS))
        return _assemble(body, results, tuple(placements))


def _paksha(
    body: CelestialBody,
    longitudes: dict[CelestialBody, float],
    signs: dict[CelestialBody, Rashi],
) -> ComponentResult:
    nature = calc.natural_nature(body, longitudes, signs)
    if nature is None:
        reason = (
            ShadbalaReason.MOON_PHASE_BOUNDARY
            if calc.moon_nature(longitudes[CelestialBody.MOON], longitudes[CelestialBody.SUN])
            is None
            else ShadbalaReason.MERCURY_MIXED_ASSOCIATION
        )
        return _ne(Component.PAKSHA, reason)
    return _ok(
        Component.PAKSHA,
        calc.paksha_bala(nature, longitudes[CelestialBody.MOON], longitudes[CelestialBody.SUN]),
    )


def _total(
    component: Component, parts: tuple[Component, ...], by: dict[Component, ComponentResult]
) -> ComponentResult:
    missing = [p.value for p in parts if by[p].status is ComponentStatus.NOT_EVALUABLE]
    if missing:
        return ComponentResult(
            component=component,
            status=ComponentStatus.NOT_EVALUABLE,
            reason=ShadbalaReason.COMPONENT_NOT_EVALUABLE,
            detail="missing: " + ", ".join(missing),
            evidence_label=EvidenceLabel.DERIVED_CALCULATION,
        )
    value = sum(by[p].virupas or 0.0 for p in parts)
    return ComponentResult(
        component=component,
        status=ComponentStatus.SUCCESS,
        virupas=value,
        evidence_label=EvidenceLabel.DERIVED_CALCULATION,
    )


def _assemble(
    body: CelestialBody,
    leaves: list[ComponentResult],
    placements: tuple[SaptavargaPlacement, ...],
) -> PlanetShadbala:
    by = {r.component: r for r in leaves}
    sthana = _total(Component.STHANA_TOTAL, STHANA_PARTS, by)
    kala = _total(Component.KALA_TOTAL, KALA_PARTS, by)
    by[Component.STHANA_TOTAL] = sthana
    by[Component.KALA_TOTAL] = kala
    total = _total(Component.SHADBALA_TOTAL, SIX_BALAS, by)
    evaluated = tuple(r.component for r in leaves if r.status is ComponentStatus.SUCCESS)
    not_evaluated = tuple(r.component for r in leaves if r.status is ComponentStatus.NOT_EVALUABLE)
    return PlanetShadbala(
        body=body,
        components=(*leaves, sthana, kala, total),
        saptavarga=placements,
        evaluated_subtotal_virupas=sum(r.virupas or 0.0 for r in leaves if r.virupas is not None),
        evaluated_components=evaluated,
        not_evaluated_components=not_evaluated,
    )
