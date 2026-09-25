"""KP natal, Ruling Planets and horary facts (Phase 9 WP-E;
`docs/ASTROLOGY_STANDARDS.md` v1.15.0, KP-01 to KP-16).

    KpChartRequest         -> KpService.calculate_chart   -> KpChartFacts
    KpRulingPlanetsRequest -> KpService.ruling_planets    -> KpRulingPlanetsFacts
    KpHoraryRequest        -> KpService.calculate_horary  -> KpHoraryFacts

Positions and cusps come from the Phase 4 ephemeris adapter under a KP
ayanamsa that is applied only for the duration of the call and then undone
(`ephemeris.kp_sidereal_mode`), so no Vedic calculation can inherit it.
Nothing here imports Swiss Ephemeris, and no Vedic rule is applied: KP
shares only the adapter, time resolution, and the sign, Nakshatra and
Vimshottari identifiers that the KP Readers themselves use.

Invalid input raises the existing typed errors. Conditions a valid request
can still hit (unknown birth time, Placidus undefined at polar latitudes, no
sunrise for the sunrise day convention, an unsolvable horary Ascendant) come
back as NOT_EVALUABLE with a reason, never as a substitute result.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from fractions import Fraction
from zoneinfo import ZoneInfo

from pandit_astro_engine import ephemeris, timezones
from pandit_astro_engine._version import __version__
from pandit_astro_engine.config import Settings
from pandit_astro_engine.errors import HouseSystemUnavailableError
from pandit_astro_engine.kp import ruling_planets as rp
from pandit_astro_engine.kp.constants import (
    KP_STANDARDS_VERSION,
    KP_SYSTEM_ID,
    DayLordConvention,
    KpReason,
    KpStatus,
    KpTimePrecision,
)
from pandit_astro_engine.kp.models import (
    KpChartFacts,
    KpChartRequest,
    KpCusp,
    KpCusps,
    KpHoraryEntry,
    KpHoraryFacts,
    KpHoraryRequest,
    KpHouseSignificators,
    KpLordship,
    KpPlanet,
    KpPlanetSignification,
    KpProfileIds,
    KpRulingPlanet,
    KpRulingPlanets,
    KpRulingPlanetsFacts,
    KpRulingPlanetsRequest,
    KpSignificators,
    ProvenanceEntry,
)
from pandit_astro_engine.kp.profiles import (
    AYANAMSA_PROFILES,
    HORARY_NUMBER_249,
    HORARY_NUMBER_249_ID,
    HOUSES_PLACIDUS_SIDEREAL,
    RULING_PLANETS,
    RULING_PLANETS_ID,
    SIGNIFICATORS_FOUR_LEVEL,
    SIGNIFICATORS_FOUR_LEVEL_ID,
    SUBDIVISION,
    ProfileDef,
)
from pandit_astro_engine.kp.significators import (
    house_of,
    house_significators,
    planet_significations,
)
from pandit_astro_engine.kp.subdivision import kp_lords, kp_table_entry
from pandit_astro_engine.models import (
    CelestialBody,
    EphemerisMode,
    LocalDateTimeInput,
    Location,
    NodeConvention,
    TimeResolution,
)

_UNSET = object()

#: Tolerance on the solved horary Ascendant, degrees (about 0.0004 arcsec).
_HORARY_ASC_TOLERANCE_DEGREES = 1e-7

_CLASSICAL = (
    CelestialBody.SUN,
    CelestialBody.MOON,
    CelestialBody.MARS,
    CelestialBody.MERCURY,
    CelestialBody.JUPITER,
    CelestialBody.VENUS,
    CelestialBody.SATURN,
)


@dataclass(frozen=True)
class _Raw:
    longitude: float
    speed: float
    mode: EphemerisMode


@dataclass(frozen=True)
class _Moment:
    jd_ut: float
    utc: dt.datetime
    time_resolution: TimeResolution


def _resolve(local: LocalDateTimeInput) -> _Moment:
    utc, resolution = timezones.resolve_local_datetime(local)
    jd_et, jd_ut = ephemeris.utc_to_julian_day(
        utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second + utc.microsecond / 1e6
    )
    resolution = resolution.model_copy(update={"julian_day_ut": jd_ut, "julian_day_et": jd_et})
    return _Moment(jd_ut, utc, resolution)


def _positions(
    jd_ut: float, node_convention: NodeConvention, allow_moshier: bool
) -> dict[CelestialBody, _Raw]:
    """Sidereal positions under the KP mode already applied by the caller."""
    out: dict[CelestialBody, _Raw] = {}
    for body in _CLASSICAL:
        raw = ephemeris.calculate_body(
            jd_ut,
            ephemeris.SWE_BODY_ID[body.value],
            sidereal=True,
            allow_moshier_fallback=allow_moshier,
        )
        out[body] = _Raw(raw.longitude, raw.speed_longitude, raw.mode)
    node = ephemeris.calculate_body(
        jd_ut,
        ephemeris.SWE_NODE_ID[node_convention.value],
        sidereal=True,
        allow_moshier_fallback=allow_moshier,
    )
    out[CelestialBody.RAHU] = _Raw(node.longitude, node.speed_longitude, node.mode)
    out[CelestialBody.KETU] = _Raw(
        (node.longitude + 180.0) % 360.0, node.speed_longitude, node.mode
    )
    return out


def _lordship(longitude: float | Fraction) -> KpLordship:
    lords = kp_lords(longitude)
    return KpLordship(
        sign=lords.sign,
        sign_lord=lords.sign_lord,
        nakshatra=lords.nakshatra,
        star_lord=lords.star_lord,
        sub_lord=lords.sub_lord,
        sub_sub_lord=lords.sub_sub_lord,
        sub_start=float(lords.sub_start),
        sub_end=float(lords.sub_end),
        near_boundary=lords.near_boundary,
    )


def _planets(
    raw: dict[CelestialBody, _Raw],
    node_convention: NodeConvention,
    cusps: tuple[float, ...] | None,
    with_lordship: bool,
) -> tuple[KpPlanet, ...]:
    return tuple(
        KpPlanet(
            body=body,
            longitude=r.longitude,
            speed_longitude=r.speed,
            retrograde=r.speed < 0.0,
            node_convention=node_convention
            if body in (CelestialBody.RAHU, CelestialBody.KETU)
            else None,
            ephemeris_mode=r.mode,
            lordship=_lordship(r.longitude) if with_lordship else None,
            house=house_of(r.longitude, cusps) if cusps is not None else None,
        )
        for body, r in raw.items()
    )


def _cusps_model(
    cusps: tuple[float, ...], polar_limit: float, exact_first: Fraction | None = None
) -> KpCusps:
    """`exact_first` is the exact horary Ascendant, so a cusp placed exactly on
    a table boundary is classified by the exact value, not its float."""
    return KpCusps(
        status=KpStatus.SUCCESS,
        cusps=tuple(
            KpCusp(
                house=i + 1,
                longitude=c,
                lordship=_lordship(exact_first if i == 0 and exact_first is not None else c),
            )
            for i, c in enumerate(cusps)
        ),
        polar_limit_degrees=polar_limit,
    )


def _significators(cusps: tuple[float, ...], raw: dict[CelestialBody, _Raw]) -> KpSignificators:
    longitudes = {b: r.longitude for b, r in raw.items()}
    stars = {b: kp_lords(lon).star_lord for b, lon in longitudes.items()}
    houses = house_significators(cusps, longitudes, stars)
    return KpSignificators(
        status=KpStatus.SUCCESS,
        houses=tuple(
            KpHouseSignificators(
                house=h,
                level_a_in_star_of_occupants=levels["a"],
                level_b_occupants=levels["b"],
                level_c_in_star_of_lord=levels["c"],
                level_d_lord=levels["d"],
            )
            for h, levels in houses.items()
        ),
        planets=tuple(
            KpPlanetSignification(body=b, houses=hs)
            for b, hs in planet_significations(houses).items()
        ),
    )


def _weekday(
    moment: _Moment, local: LocalDateTimeInput, location: Location, convention: DayLordConvention
) -> int | None:
    """Sunday = 0. None when the sunrise convention has no sunrise."""
    civil = dt.date(local.year, local.month, local.day)
    sunday_zero = (civil.weekday() + 1) % 7
    if convention is DayLordConvention.LOCAL_CIVIL_DATE:
        return sunday_zero
    midnight = dt.datetime(civil.year, civil.month, civil.day, tzinfo=ZoneInfo(local.timezone))
    midnight_utc = midnight.astimezone(dt.timezone.utc)
    _et, jd_midnight = ephemeris.utc_to_julian_day(
        midnight_utc.year,
        midnight_utc.month,
        midnight_utc.day,
        midnight_utc.hour,
        midnight_utc.minute,
        float(midnight_utc.second),
    )
    occurred, sunrise = ephemeris.rise_or_set(
        jd_midnight,
        event="rise",
        longitude=location.longitude,
        latitude=location.latitude,
        altitude_meters=location.altitude_meters,
    )
    if not occurred or sunrise is None or sunrise - jd_midnight >= 1.0:
        return None
    return sunday_zero if moment.jd_ut >= sunrise else (sunday_zero - 1) % 7


def _ruling(
    moment: _Moment,
    local: LocalDateTimeInput,
    location: Location,
    convention: DayLordConvention,
    raw: dict[CelestialBody, _Raw],
) -> KpRulingPlanets:
    weekday = _weekday(moment, local, location, convention)
    if weekday is None:
        return KpRulingPlanets(status=KpStatus.NOT_EVALUABLE, reason=KpReason.SUNRISE_UNAVAILABLE)
    ascendant = ephemeris.calculate_ascendant(
        moment.jd_ut, latitude=location.latitude, longitude=location.longitude, sidereal=True
    )
    members = rp.ruling_planets(
        ascendant=ascendant,
        longitudes={b: r.longitude for b, r in raw.items()},
        retrograde={b: r.speed < 0.0 for b, r in raw.items()},
        weekday_sunday_zero=weekday,
    )
    return KpRulingPlanets(
        status=KpStatus.SUCCESS,
        weekday_sunday_zero=weekday,
        ascendant_longitude=ascendant,
        members=tuple(
            KpRulingPlanet(
                body=m.body,
                role=m.role,
                represents=m.represents,
                star_lord_of_body=m.star_lord_of_body,
                retrograde_star_flag=m.retrograde_star_flag,
            )
            for m in members
        ),
    )


def _prov(entry_id: str, item: str, profile: ProfileDef) -> ProvenanceEntry:
    return ProvenanceEntry(
        entry_id=entry_id,
        item=f"{item}: {profile.profile_id}",
        evidence_label=profile.label,
        statement=profile.title,
        references=profile.references,
    )


def _warnings(raw: dict[CelestialBody, _Raw], node_convention: NodeConvention) -> list[str]:
    warnings = []
    if any(r.mode is EphemerisMode.MOSHIER for r in raw.values()):
        warnings.append(
            "Moshier analytical ephemeris used (no Swiss Ephemeris data files configured)"
        )
    warnings.append(
        f"{node_convention.value} node used for Rahu; Ketu is Rahu plus 180 degrees "
        "(the KP Readers do not fix mean or true nodes)"
    )
    return warnings


class KpService:
    """Stateless facade, like the other astro-engine services."""

    def __init__(self, ephemeris_path: str | None = _UNSET) -> None:  # type: ignore[assignment]
        resolved = Settings().ephemeris_path if ephemeris_path is _UNSET else ephemeris_path
        ephemeris.configure_ephemeris_path(resolved)

    # -- natal ---------------------------------------------------------------

    def calculate_chart(self, request: KpChartRequest) -> KpChartFacts:
        ayanamsa = AYANAMSA_PROFILES[request.ayanamsa_profile_id]
        moment = _resolve(request.local_datetime)
        exact = request.time_precision is KpTimePrecision.EXACT
        polar_limit = 90.0 - ephemeris.true_obliquity_degrees(moment.jd_ut)

        with ephemeris.kp_sidereal_mode(ayanamsa.swe_variant):
            raw = _positions(moment.jd_ut, request.node_convention, request.allow_moshier_fallback)
            ayanamsa_degrees = ephemeris.get_ayanamsa_with_nutation_degrees(moment.jd_ut)
            cusps_model, cusp_values = self._natal_cusps(moment.jd_ut, request, exact, polar_limit)

        if cusp_values is not None:
            significators = _significators(cusp_values, raw)
        else:
            significators = KpSignificators(
                status=KpStatus.NOT_EVALUABLE, reason=cusps_model.reason
            )

        warnings = _warnings(raw, request.node_convention)
        if not exact:
            warnings.insert(
                0,
                "birth time unknown: positions are for the supplied clock time, a placeholder; "
                "cusps, star/sub lords and significators are not evaluated",
            )
        return KpChartFacts(
            system=KP_SYSTEM_ID,
            standards_version=KP_STANDARDS_VERSION,
            engine_version=__version__,
            swisseph_version=ephemeris.swisseph_version(),
            ephemeris_path=ephemeris.configured_ephemeris_path(),
            profiles=KpProfileIds(
                ayanamsa_profile_id=ayanamsa.profile_id,
                significator_profile_id=SIGNIFICATORS_FOUR_LEVEL_ID,
                node_convention=request.node_convention,
            ),
            time_precision=request.time_precision,
            time_resolution=moment.time_resolution,
            location=request.location,
            ayanamsa_degrees=ayanamsa_degrees,
            planets=_planets(raw, request.node_convention, cusp_values, exact),
            cusps=cusps_model,
            significators=significators,
            provenance=(
                _prov("prov.ayanamsa", "Ayanamsa", ayanamsa),
                _prov("prov.houses", "Houses", HOUSES_PLACIDUS_SIDEREAL),
                _prov("prov.subdivision", "Star/sub division", SUBDIVISION),
                _prov("prov.significators", "Significators", SIGNIFICATORS_FOUR_LEVEL),
            ),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _natal_cusps(
        jd_ut: float, request: KpChartRequest, exact: bool, polar_limit: float
    ) -> tuple[KpCusps, tuple[float, ...] | None]:
        if not exact:
            return KpCusps(status=KpStatus.NOT_EVALUABLE, reason=KpReason.BIRTH_TIME_UNKNOWN), None
        latitude = request.location.latitude
        if abs(latitude) >= polar_limit:
            return (
                KpCusps(
                    status=KpStatus.NOT_EVALUABLE,
                    reason=KpReason.PLACIDUS_POLAR_CIRCLE,
                    detail=f"|latitude| {abs(latitude)} >= 90 - true obliquity = {polar_limit}",
                    polar_limit_degrees=polar_limit,
                ),
                None,
            )
        try:
            houses = ephemeris.calculate_sidereal_placidus_houses(
                jd_ut, latitude=latitude, longitude=request.location.longitude
            )
        except HouseSystemUnavailableError as exc:
            return (
                KpCusps(
                    status=KpStatus.NOT_EVALUABLE,
                    reason=KpReason.PLACIDUS_NOT_COMPUTABLE,
                    detail=str(exc),
                    polar_limit_degrees=polar_limit,
                ),
                None,
            )
        return _cusps_model(houses.cusps, polar_limit), houses.cusps

    # -- Ruling Planets ------------------------------------------------------

    def ruling_planets(self, request: KpRulingPlanetsRequest) -> KpRulingPlanetsFacts:
        ayanamsa = AYANAMSA_PROFILES[request.ayanamsa_profile_id]
        moment = _resolve(request.local_datetime)
        with ephemeris.kp_sidereal_mode(ayanamsa.swe_variant):
            raw = _positions(moment.jd_ut, request.node_convention, request.allow_moshier_fallback)
            ruling = _ruling(
                moment,
                request.local_datetime,
                request.location,
                request.day_lord_convention,
                raw,
            )
        return KpRulingPlanetsFacts(
            system=KP_SYSTEM_ID,
            standards_version=KP_STANDARDS_VERSION,
            engine_version=__version__,
            profiles=KpProfileIds(
                ayanamsa_profile_id=ayanamsa.profile_id,
                ruling_planets_profile_id=RULING_PLANETS_ID,
                node_convention=request.node_convention,
                day_lord_convention=request.day_lord_convention,
            ),
            time_resolution=moment.time_resolution,
            location=request.location,
            ruling_planets=ruling,
            provenance=(
                _prov("prov.ayanamsa", "Ayanamsa", ayanamsa),
                _prov("prov.subdivision", "Star/sub division", SUBDIVISION),
                _prov("prov.ruling_planets", "Ruling planets", RULING_PLANETS),
            ),
            warnings=tuple(_warnings(raw, request.node_convention)),
        )

    # -- horary --------------------------------------------------------------

    def calculate_horary(self, request: KpHoraryRequest) -> KpHoraryFacts:
        ayanamsa = AYANAMSA_PROFILES[request.ayanamsa_profile_id]
        entry = kp_table_entry(request.horary_number)
        moment = _resolve(request.local_datetime)
        obliquity = ephemeris.true_obliquity_degrees(moment.jd_ut)
        polar_limit = 90.0 - obliquity

        with ephemeris.kp_sidereal_mode(ayanamsa.swe_variant):
            raw = _positions(moment.jd_ut, request.node_convention, request.allow_moshier_fallback)
            ayanamsa_degrees = ephemeris.get_ayanamsa_with_nutation_degrees(moment.jd_ut)
            ruling = _ruling(
                moment,
                request.local_datetime,
                request.location,
                request.day_lord_convention,
                raw,
            )
        cusps_model, cusp_values = _horary_cusps(
            entry.start, ayanamsa_degrees, request.location.latitude, obliquity, polar_limit
        )
        if cusp_values is not None:
            significators = _significators(cusp_values, raw)
        else:
            significators = KpSignificators(
                status=KpStatus.NOT_EVALUABLE, reason=cusps_model.reason
            )

        warnings = _warnings(raw, request.node_convention)
        warnings.append(
            "horary cusps: the Ascendant is fixed at the start of the numbered sub and the "
            "matching sidereal time is solved numerically (the Reader uses printed tables of "
            "houses); planets are for the moment of judgment"
        )
        return KpHoraryFacts(
            system=KP_SYSTEM_ID,
            standards_version=KP_STANDARDS_VERSION,
            engine_version=__version__,
            swisseph_version=ephemeris.swisseph_version(),
            ephemeris_path=ephemeris.configured_ephemeris_path(),
            profiles=KpProfileIds(
                ayanamsa_profile_id=ayanamsa.profile_id,
                significator_profile_id=SIGNIFICATORS_FOUR_LEVEL_ID,
                ruling_planets_profile_id=RULING_PLANETS_ID,
                horary_profile_id=HORARY_NUMBER_249_ID,
                node_convention=request.node_convention,
                day_lord_convention=request.day_lord_convention,
            ),
            time_resolution=moment.time_resolution,
            location=request.location,
            ayanamsa_degrees=ayanamsa_degrees,
            entry=KpHoraryEntry(
                number=entry.number,
                sign=entry.sign,
                sign_lord=entry.sign_lord,
                nakshatra=entry.nakshatra,
                star_lord=entry.star_lord,
                sub_lord=entry.sub_lord,
                start=float(entry.start),
                end=float(entry.end),
            ),
            planets=_planets(raw, request.node_convention, cusp_values, True),
            cusps=cusps_model,
            significators=significators,
            ruling_planets=ruling,
            provenance=(
                _prov("prov.ayanamsa", "Ayanamsa", ayanamsa),
                _prov("prov.horary", "Horary", HORARY_NUMBER_249),
                _prov("prov.houses", "Houses", HOUSES_PLACIDUS_SIDEREAL),
                _prov("prov.subdivision", "Star/sub division", SUBDIVISION),
                _prov("prov.significators", "Significators", SIGNIFICATORS_FOUR_LEVEL),
                _prov("prov.ruling_planets", "Ruling planets", RULING_PLANETS),
            ),
            warnings=tuple(warnings),
        )


def _wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def solve_armc_for_ascendant(
    tropical_ascendant: float, *, latitude: float, obliquity: float
) -> float | None:
    """The ARMC whose Placidus Ascendant at `latitude` is `tropical_ascendant`
    (degrees), by bracketing on a 1-degree grid then bisection; None when no
    bracket is found. Outside the polar circles the Ascendant increases
    monotonically with the ARMC, so the bracket is unique."""

    def residual(armc: float) -> float:
        houses = ephemeris.placidus_houses_from_armc(
            armc % 360.0, latitude=latitude, obliquity=obliquity
        )
        return _wrap180(houses.ascendant - tropical_ascendant)

    previous = residual(0.0)
    for step in range(1, 361):
        current = residual(float(step))
        if previous <= 0.0 <= current and current - previous < 180.0:
            low, high = float(step - 1), float(step)
            for _ in range(80):
                mid = (low + high) / 2.0
                if residual(mid) <= 0.0:
                    low = mid
                else:
                    high = mid
            return ((low + high) / 2.0) % 360.0
        previous = current
    return None


def _horary_cusps(
    exact_target: Fraction,
    ayanamsa_degrees: float,
    latitude: float,
    obliquity: float,
    polar_limit: float,
) -> tuple[KpCusps, tuple[float, ...] | None]:
    if abs(latitude) >= polar_limit:
        return (
            KpCusps(
                status=KpStatus.NOT_EVALUABLE,
                reason=KpReason.PLACIDUS_POLAR_CIRCLE,
                detail=f"|latitude| {abs(latitude)} >= 90 - true obliquity = {polar_limit}",
                polar_limit_degrees=polar_limit,
            ),
            None,
        )
    target_sidereal = float(exact_target) % 360.0
    tropical_target = (target_sidereal + ayanamsa_degrees) % 360.0
    try:
        armc = solve_armc_for_ascendant(tropical_target, latitude=latitude, obliquity=obliquity)
        houses = (
            ephemeris.placidus_houses_from_armc(armc, latitude=latitude, obliquity=obliquity)
            if armc is not None
            else None
        )
    except HouseSystemUnavailableError as exc:
        return (
            KpCusps(
                status=KpStatus.NOT_EVALUABLE,
                reason=KpReason.PLACIDUS_NOT_COMPUTABLE,
                detail=str(exc),
                polar_limit_degrees=polar_limit,
            ),
            None,
        )
    if houses is None or abs(_wrap180(houses.ascendant - tropical_target)) > (
        _HORARY_ASC_TOLERANCE_DEGREES
    ):
        return (
            KpCusps(
                status=KpStatus.NOT_EVALUABLE,
                reason=KpReason.HORARY_ASCENDANT_NOT_SOLVABLE,
                polar_limit_degrees=polar_limit,
            ),
            None,
        )
    sidereal = tuple((c - ayanamsa_degrees) % 360.0 for c in houses.cusps)
    # The first cusp is the fixed horary Ascendant itself, exactly.
    sidereal = (target_sidereal, *sidereal[1:])
    return _cusps_model(sidereal, polar_limit, exact_target % 360), sidereal
