"""Modern Shadbala profile `SHADBALA_RAMAN_GRAHA_BHAVA_BALAS` (Phase 9
closure; `docs/ASTROLOGY_STANDARDS.md` v1.21.0, SR-01 to SR-24).

    RamanShadbalaRequest -> RamanShadbalaService.calculate -> RamanShadbalaFacts

A separate methodology from the verse-literal BPHS profile
(`ShadbalaService`): its own request, service, component table and
provenance. It never returns a BPHS-profile value and the BPHS profile never
calls it. Positions, Lagna and vargas come from the Phase 5 Kundli (Vedic
default: Lahiri, whole-sign); the tropical longitude for Ayana Bala is the
Lahiri longitude plus the Lahiri ayanamsa; Cheshta Bala works in the frame of
Raman's own mean-motion tables (the Raman ayanamsa, read without being
applied to the chart). Components that a valid request can still not
evaluate come back NOT_EVALUABLE with a reason, and the total is produced
only when every component is evaluated.
"""

from __future__ import annotations

import datetime as dt

from pandit_astro_engine import ephemeris
from pandit_astro_engine._version import __version__
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.lordship import RASHI_LORD
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    Ayanamsa,
    CalculationConfig,
    CelestialBody,
    EphemerisMode,
    TimeResolution,
)
from pandit_astro_engine.rashi import Rashi, rashi_from_longitude
from pandit_astro_engine.service import AstronomicalCalculationService
from pandit_astro_engine.shadbala import components as calc
from pandit_astro_engine.shadbala import raman as rm
from pandit_astro_engine.shadbala.constants import (
    DIG_BALA_ZERO_POINT,
    GENDER,
    MOOLATRIKONA,
    SAPTAVARGA,
    SHADBALA_BODIES,
    SHADBALA_SYSTEM_ID,
    Angle,
)
from pandit_astro_engine.shadbala.models import (
    ComponentProvenance,
    ComponentResult,
    ComponentStatus,
    DayNight,
    PlanetShadbala,
    RamanCheshtaDetail,
    RamanDetails,
    RamanDrishtiCell,
    RamanShadbalaFacts,
    RamanShadbalaRequest,
    RamanWar,
    SaptavargaPlacement,
    ShadbalaReason,
    ShadbalaTimePrecision,
)
from pandit_astro_engine.shadbala.profiles import (
    KALA_PARTS,
    RAMAN_COMPONENTS,
    SIX_BALAS,
    STHANA_PARTS,
    Component,
    EvidenceLabel,
)
from pandit_astro_engine.shadbala.service import (
    LEAF_COMPONENTS,
    _apparent_solar_hours,
    _solar_frame,
    _weekday_of,
)
from pandit_astro_engine.vargas import calculate_varga_sign

RAMAN_STANDARDS_VERSION = "1.21.0"

#: Years for which the extrapolated mean-motion tables are used (engineering
#: bound; Raman's tables are built around 1900 with linear corrections).
CHESHTA_YEAR_RANGE = (1800, 2100)

_UNSET = object()
_KALA_BEFORE_AYANA = (
    Component.NATHONNATHA,
    Component.PAKSHA,
    Component.TRIBHAGA,
    Component.ABDA,
    Component.MASA,
    Component.VARA,
    Component.HORA,
)


def _ok(component: Component, virupas: float) -> ComponentResult:
    return ComponentResult(
        component=component,
        status=ComponentStatus.SUCCESS,
        virupas=virupas,
        evidence_label=RAMAN_COMPONENTS[component].label,
    )


def _ne(component: Component, reason: ShadbalaReason, detail: str | None = None) -> ComponentResult:
    return ComponentResult(
        component=component,
        status=ComponentStatus.NOT_EVALUABLE,
        reason=reason,
        detail=detail,
        evidence_label=RAMAN_COMPONENTS[component].label,
    )


def _na(component: Component, detail: str) -> ComponentResult:
    return ComponentResult(
        component=component,
        status=ComponentStatus.NOT_APPLICABLE,
        detail=detail,
        evidence_label=RAMAN_COMPONENTS[component].label,
    )


def _saptavarga(
    body: CelestialBody, lon: float, signs: dict[CelestialBody, Rashi]
) -> tuple[float, tuple[SaptavargaPlacement, ...]]:
    """Art. 30: Moolatrikona only in the Rasi (by the locked degree range);
    otherwise own sign or the compound relationship with the sign lord."""
    mt_sign, mt_from, mt_to = MOOLATRIKONA[body]
    own = {r for r, lord in RASHI_LORD.items() if lord == body}
    total = 0.0
    placements = []
    for varga in SAPTAVARGA:
        sign = calculate_varga_sign(varga, lon)
        if varga == 1 and sign == mt_sign and mt_from <= lon % 30.0 < mt_to:
            category = "moolatrikona"
        elif sign in own:
            category = "own"
        else:
            category = calc.compound_relationship(body, RASHI_LORD[sign], signs)
        value = rm.RAMAN_SAPTAVARGAJA[category]
        total += value
        placements.append(
            SaptavargaPlacement(varga=varga, sign=sign, category=category, virupas=value)
        )
    return total, tuple(placements)


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
    return ComponentResult(
        component=component,
        status=ComponentStatus.SUCCESS,
        virupas=sum(by[p].virupas or 0.0 for p in parts),
        evidence_label=EvidenceLabel.DERIVED_CALCULATION,
    )


class RamanShadbalaService:
    """Stateless facade for the Raman profile."""

    def __init__(self, ephemeris_path: str | None = _UNSET) -> None:  # type: ignore[assignment]
        astro = (
            AstronomicalCalculationService()
            if ephemeris_path is _UNSET
            else AstronomicalCalculationService(ephemeris_path=ephemeris_path)
        )
        self._kundli = KundliCalculationService(astro)

    def calculate(self, request: RamanShadbalaRequest) -> RamanShadbalaFacts:
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
        resolution = kundli.astronomical.metadata.time_resolution
        jd = resolution.julian_day_ut
        lon = {p.body: p.longitude for p in kundli.planets}
        signs = {b: rashi_from_longitude(v) for b, v in lon.items()}
        warnings: list[str] = []
        if kundli.astronomical.metadata.ephemeris_mode is EphemerisMode.MOSHIER:
            warnings.append(
                "Moshier analytical ephemeris used (no Swiss Ephemeris data files configured)"
            )
        warnings.append(
            "modern profile (B. V. Raman, Graha and Bhava Balas); not the BPHS verse profile"
        )

        if request.time_precision is ShadbalaTimePrecision.UNKNOWN:
            warnings.insert(
                0, "birth time unknown: every component except Naisargika Bala is not evaluated"
            )
            planets = tuple(
                _assemble(
                    body,
                    [
                        _ok(c, calc.naisargika_bala(body))
                        if c is Component.NAISARGIKA
                        else _ne(c, ShadbalaReason.BIRTH_TIME_UNKNOWN)
                        for c in LEAF_COMPONENTS
                    ],
                    (),
                )
                for body in SHADBALA_BODIES
            )
            return self._facts(request, resolution, planets, RamanDetails(), warnings, None)

        ephemeris.set_sidereal_mode(Ayanamsa.LAHIRI)
        lahiri_ayanamsa = ephemeris.get_ayanamsa_with_nutation_degrees(jd)
        _asc, mc = ephemeris.calculate_sidereal_angles(
            jd, latitude=request.location.latitude, longitude=request.location.longitude
        )
        raman_ayanamsa = ephemeris.reference_ayanamsa_with_nutation_degrees("raman", jd)
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

        details = RamanDetails(
            krantis=tuple(
                (b, rm.raman_kranti((lon[b] + lahiri_ayanamsa) % 360.0)) for b in SHADBALA_BODIES
            )
        )
        lords: dict[str, CelestialBody | None] = {"abda": None, "masa": None, "vara": None}
        hora: CelestialBody | None = None
        if frame is not None:
            weekday = _weekday_of(frame.last_sunrise, request.local_datetime.timezone)
            hindu_date = _local_date(frame.last_sunrise, request.local_datetime.timezone)
            ahargana = rm.condensed_ahargana(hindu_date)
            if rm.ahargana_weekday(ahargana) != weekday:  # pragma: no cover - defensive
                raise RuntimeError("condensed ahargana weekday disagrees with the calendar")
            hours = (jd - frame.last_sunrise) * 24.0
            hora = rm.hora_lord(weekday, hours) if hours < 24.0 else None
            lords = {
                "abda": rm.abda_lord(ahargana),
                "masa": rm.masa_lord(ahargana),
                "vara": rm.WEEKDAY_LORD_SUNDAY_FIRST[weekday],
            }
            details = details.model_copy(
                update={
                    "hindu_date": hindu_date,
                    "condensed_ahargana": ahargana,
                    "abda_lord": lords["abda"],
                    "masa_lord": lords["masa"],
                    "vara_lord": lords["vara"],
                    "hora_lord": hora,
                    "hours_since_sunrise": hours,
                }
            )
        else:
            warnings.append(
                "no sunrise/sunset near the birth instant: Tribhaga, Abda, Masa, Vara and Hora "
                "are not evaluated"
            )

        # Cheshta (Mars to Saturn) in the frame of Raman's tables.
        year = request.local_datetime.year
        interval = rm.cheshta_interval(jd)
        cheshta: dict[CelestialBody, ComponentResult] = {}
        cheshta_detail = []
        for body in rm.WAR_PLANETS:
            if not CHESHTA_YEAR_RANGE[0] <= year <= CHESHTA_YEAR_RANGE[1]:
                cheshta[body] = _ne(Component.CHESHTA, ShadbalaReason.CHESHTA_TABLES_OUT_OF_RANGE)
                continue
            mean, sighrocca = rm.mean_and_sighrocca(body, interval, year - 1900)
            true_raman = (lon[body] + lahiri_ayanamsa - raman_ayanamsa) % 360.0
            kendra = rm.reduced_cheshta_kendra(sighrocca, mean, true_raman)
            cheshta[body] = _ok(Component.CHESHTA, kendra / 3.0)
            cheshta_detail.append(
                RamanCheshtaDetail(
                    body=body,
                    mean_longitude=mean,
                    sighrocca=sighrocca,
                    true_longitude_raman_frame=true_raman,
                    reduced_kendra=kendra,
                )
            )

        # Natures for Paksha (Mercury) and Drik.
        natures = {b: calc.natural_nature(b, lon, signs) for b in SHADBALA_BODIES}
        seven = {b: lon[b] for b in SHADBALA_BODIES}
        drishti_cells: list[RamanDrishtiCell] = []

        partial: dict[CelestialBody, dict[Component, ComponentResult]] = {}
        placements: dict[CelestialBody, tuple[SaptavargaPlacement, ...]] = {}
        for body in SHADBALA_BODIES:
            p = lon[body]
            res: dict[Component, ComponentResult] = {}
            res[Component.UCHCHA] = _ok(Component.UCHCHA, calc.uchcha_bala(body, p))
            sapta, placements[body] = _saptavarga(body, p, signs)
            res[Component.SAPTAVARGAJA] = _ok(Component.SAPTAVARGAJA, sapta)
            d9 = calculate_varga_sign(9, p)
            res[Component.OJAYUGMA] = _ok(
                Component.OJAYUGMA, calc.ojayugma_bala(body, signs[body], d9)
            )
            res[Component.KENDRADI] = _ok(
                Component.KENDRADI, calc.kendradi_bala(rashi_from_longitude(lagna), signs[body])
            )
            res[Component.DREKKANA] = _ok(
                Component.DREKKANA,
                rm.raman_drekkana_bala(GENDER[body].value, p % 30.0, request.drekkana_reading),
            )
            res[Component.DIG] = _ok(
                Component.DIG, calc.dig_bala(p, angles[DIG_BALA_ZERO_POINT[body]])
            )
            res[Component.NATHONNATHA] = _ok(
                Component.NATHONNATHA, calc.nathonnatha_bala(body, unnata)
            )
            res[Component.PAKSHA] = _raman_paksha(body, lon, natures, request)
            if frame is None:
                for comp in (Component.TRIBHAGA, Component.ABDA, Component.MASA, Component.VARA):
                    res[comp] = _ne(comp, ShadbalaReason.SUNRISE_UNAVAILABLE)
            else:
                res[Component.TRIBHAGA] = _ok(
                    Component.TRIBHAGA, calc.tribhaga_bala(body, frame.is_day, frame.third)
                )
                res[Component.ABDA] = _ok(Component.ABDA, 15.0 if lords["abda"] is body else 0.0)
                res[Component.MASA] = _ok(Component.MASA, 30.0 if lords["masa"] is body else 0.0)
                res[Component.VARA] = _ok(Component.VARA, 45.0 if lords["vara"] is body else 0.0)
            res[Component.HORA] = (
                _ok(Component.HORA, 60.0 if hora is body else 0.0)
                if hora is not None
                else _ne(Component.HORA, ShadbalaReason.SUNRISE_UNAVAILABLE)
            )
            kranti = rm.raman_kranti((p + lahiri_ayanamsa) % 360.0)
            res[Component.AYANA] = _ok(Component.AYANA, rm.raman_ayana_bala(body, kranti))
            if body in cheshta:
                res[Component.CHESHTA] = cheshta[body]
            else:
                res[Component.CHESHTA] = _na(
                    Component.CHESHTA, "Raman gives Cheshta Bala for Mars to Saturn only (Art. 79)"
                )
            res[Component.NAISARGIKA] = _ok(Component.NAISARGIKA, calc.naisargika_bala(body))
            pinda, cells = rm.dristi_pinda(body, seven, natures)
            drishti_cells.extend(
                RamanDrishtiCell(aspected=body, aspecting=a, signed_value=v)
                for a, v in cells.items()
            )
            res[Component.DRIK] = (
                _ok(Component.DRIK, pinda / 4.0)
                if pinda is not None
                else _ne(Component.DRIK, ShadbalaReason.DRIK_NATURE_UNDETERMINED)
            )
            partial[body] = res

        wars = _wars(seven, partial)
        for body in SHADBALA_BODIES:
            res = partial[body]
            if body not in rm.WAR_PLANETS:
                res[Component.YUDDHA] = _na(
                    Component.YUDDHA, "the Sun and Moon take no part (Art. 76)"
                )
                continue
            war = next((w for w in wars if body in w.planets), None)
            if war is None:
                res[Component.YUDDHA] = _ok(Component.YUDDHA, 0.0)
            elif war.yuddha_virupas is None:
                res[Component.YUDDHA] = _ne(
                    Component.YUDDHA, war.reason or ShadbalaReason.PLANETARY_WAR_UNRESOLVED
                )
            else:
                sign = 1.0 if war.winner is body else -1.0
                res[Component.YUDDHA] = _ok(Component.YUDDHA, sign * war.yuddha_virupas)

        planets = tuple(
            _assemble(body, [partial[body][c] for c in LEAF_COMPONENTS], placements[body])
            for body in SHADBALA_BODIES
        )
        details = details.model_copy(
            update={
                "cheshta_interval_days": interval,
                "cheshta": tuple(cheshta_detail),
                "drishti": tuple(drishti_cells),
                "wars": tuple(wars),
            }
        )
        day_night = (
            DayNight(
                status=ComponentStatus.SUCCESS,
                is_day=frame.is_day,
                period_start_julian_day_ut=frame.start,
                period_end_julian_day_ut=frame.end,
                third=frame.third,
                vara_weekday_sunday_zero=rm.WEEKDAY_LORD_SUNDAY_FIRST.index(lords["vara"])
                if lords["vara"] is not None
                else None,
            )
            if frame is not None
            else DayNight(status=ComponentStatus.NOT_EVALUABLE)
        )
        facts = self._facts(request, resolution, planets, details, warnings, day_night)
        return facts.model_copy(
            update={
                "lagna_longitude": lagna,
                "midheaven_longitude": mc,
                "apparent_solar_hours": solar_hours,
                "unnata_ghatis": unnata,
            }
        )

    @staticmethod
    def _facts(
        request: RamanShadbalaRequest,
        resolution: TimeResolution,
        planets: tuple[PlanetShadbala, ...],
        details: RamanDetails,
        warnings: list[str],
        day_night: DayNight | None,
    ) -> RamanShadbalaFacts:
        return RamanShadbalaFacts(
            system=SHADBALA_SYSTEM_ID,
            standards_version=RAMAN_STANDARDS_VERSION,
            engine_version=__version__,
            drekkana_reading=request.drekkana_reading,
            moon_paksha_reading=request.moon_paksha_reading,
            time_precision=request.time_precision,
            time_resolution=resolution,
            location=request.location,
            ayanamsa=Ayanamsa.LAHIRI.value,
            cheshta_frame_ayanamsa="raman",
            node_convention=request.node_convention,
            lagna_longitude=None,
            midheaven_longitude=None,
            apparent_solar_hours=None,
            unnata_ghatis=None,
            day_night=day_night or DayNight(status=ComponentStatus.NOT_EVALUABLE),
            planets=planets,
            totals_in_rupas=tuple(
                (
                    p.body,
                    (p.component(Component.SHADBALA_TOTAL).virupas or 0.0) / 60.0
                    if p.component(Component.SHADBALA_TOTAL).status is ComponentStatus.SUCCESS
                    else None,
                )
                for p in planets
            ),
            details=details,
            provenance=tuple(
                ComponentProvenance(
                    component=d.component,
                    evidence_label=d.label,
                    statement=d.title,
                    reference=d.reference,
                )
                for d in RAMAN_COMPONENTS.values()
            ),
            warnings=tuple(warnings),
        )


def _local_date(jd_ut: float, timezone: str) -> dt.date:
    from zoneinfo import ZoneInfo

    y, m, d, h, mi, s = ephemeris.julian_day_to_utc_datetime_parts(jd_ut)
    utc = dt.datetime(y, m, d, h, mi, int(s), tzinfo=dt.timezone.utc)
    return utc.astimezone(ZoneInfo(timezone)).date()


def _raman_paksha(
    body: CelestialBody,
    lon: dict[CelestialBody, float],
    natures: dict[CelestialBody, str | None],
    request: RamanShadbalaRequest,
) -> ComponentResult:
    moon, sun = lon[CelestialBody.MOON], lon[CelestialBody.SUN]
    if body is CelestialBody.MOON:
        benefic = rm.raman_moon_is_benefic(calc.elongation(moon, sun), request.moon_paksha_reading)
        value = calc.paksha_bala("benefic" if benefic else "malefic", moon, sun)
        return _ok(Component.PAKSHA, 2.0 * value)
    nature = natures[body]
    if nature is None:
        return _ne(Component.PAKSHA, ShadbalaReason.MERCURY_MIXED_ASSOCIATION)
    return _ok(Component.PAKSHA, calc.paksha_bala(nature, moon, sun))


def _pre_war_aggregate(res: dict[Component, ComponentResult]) -> float | None:
    parts = (*STHANA_PARTS, Component.DIG, *_KALA_BEFORE_AYANA)
    if any(res[c].status is not ComponentStatus.SUCCESS for c in parts):
        return None
    return sum(res[c].virupas or 0.0 for c in parts)


def _wars(
    lon: dict[CelestialBody, float], partial: dict[CelestialBody, dict[Component, ComponentResult]]
) -> list[RamanWar]:
    """Art. 76: planets from Mars to Saturn less than one degree apart."""
    pairs = []
    war_planets = rm.WAR_PLANETS
    for i, a in enumerate(war_planets):
        for b in war_planets[i + 1 :]:
            sep = abs((lon[a] - lon[b] + 180.0) % 360.0 - 180.0)
            if sep < rm.WAR_LIMIT_DEGREES:
                pairs.append((a, b, sep))
    counts: dict[CelestialBody, int] = {}
    for a, b, _ in pairs:
        counts[a] = counts.get(a, 0) + 1
        counts[b] = counts.get(b, 0) + 1
    wars = []
    for a, b, sep in pairs:
        unresolved = RamanWar(
            planets=(a, b), separation_degrees=sep, reason=ShadbalaReason.PLANETARY_WAR_UNRESOLVED
        )
        if counts[a] > 1 or counts[b] > 1 or lon[a] == lon[b] or abs(lon[a] - lon[b]) > 180.0:
            wars.append(unresolved)  # several wars, a tie, or a war across 0 Aries
            continue
        agg_a, agg_b = _pre_war_aggregate(partial[a]), _pre_war_aggregate(partial[b])
        if agg_a is None or agg_b is None:
            wars.append(unresolved)
            continue
        winner = a if lon[a] < lon[b] else b
        value = abs(agg_a - agg_b) / abs(rm.BIMBA_ARCSEC[a] - rm.BIMBA_ARCSEC[b])
        wars.append(
            RamanWar(planets=(a, b), separation_degrees=sep, winner=winner, yuddha_virupas=value)
        )
    return wars


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
    return PlanetShadbala(
        body=body,
        components=(*leaves, sthana, kala, total),
        saptavarga=placements,
        evaluated_subtotal_virupas=sum(r.virupas or 0.0 for r in leaves if r.virupas is not None),
        evaluated_components=tuple(
            r.component for r in leaves if r.status is ComponentStatus.SUCCESS
        ),
        not_evaluated_components=tuple(
            r.component for r in leaves if r.status is ComponentStatus.NOT_EVALUABLE
        ),
    )
