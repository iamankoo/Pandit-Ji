"""Western natal chart facts (Phase 9 WP-D; `docs/ASTROLOGY_STANDARDS.md`
v1.14.0, WD-01 to WD-20).

    WesternChartRequest -> WesternChartService -> WesternChartFacts

Tropical positions come from the Phase 4 ephemeris adapter with the
sidereal flag off (no ayanamsa); Placidus cusps come from the same adapter.
Nothing here imports Swiss Ephemeris, and no Vedic module is called: the
Western and Vedic pipelines share only the adapter, time resolution and
input models.

Invalid input (bad coordinates, unknown profile, missing node convention,
an unknown timezone or a strict-policy DST ambiguity) raises the existing
typed errors at request validation or time resolution. Conditions that a
valid request can still hit (unknown birth time, Placidus undefined) come
back as NOT_EVALUABLE with a reason code, never as a substitute result.
"""

from __future__ import annotations

from pandit_astro_engine import ephemeris, timezones
from pandit_astro_engine._version import __version__
from pandit_astro_engine.config import Settings
from pandit_astro_engine.errors import HouseSystemUnavailableError
from pandit_astro_engine.models import EphemerisMode, NodeConvention
from pandit_astro_engine.western import aspects as aspect_calc
from pandit_astro_engine.western.constants import (
    WESTERN_STANDARDS_VERSION,
    WESTERN_SYSTEM_ID,
    WesternBody,
)
from pandit_astro_engine.western.houses import house_of
from pandit_astro_engine.western.models import (
    ProfileIds,
    ProvenanceEntry,
    WesternAspects,
    WesternBodyPosition,
    WesternChartFacts,
    WesternChartRequest,
    WesternHouses,
    WesternReason,
    WesternStatus,
    WesternTimePrecision,
)
from pandit_astro_engine.western.profiles import (
    ASPECT_SET_PROFILES,
    BODY_PROFILES,
    HOUSE_PROFILES,
    MOTION_PROFILES,
    ORB_PROFILES,
    ZODIAC_TROPICAL,
    EvidenceLabel,
    SourceReference,
)
from pandit_astro_engine.western.zodiac import degree_in_sign, tropical_sign

_UNSET = object()

_CLASSICAL_SWE_KEY = {
    WesternBody.SUN: "sun",
    WesternBody.MOON: "moon",
    WesternBody.MERCURY: "mercury",
    WesternBody.VENUS: "venus",
    WesternBody.MARS: "mars",
    WesternBody.JUPITER: "jupiter",
    WesternBody.SATURN: "saturn",
}
_OUTER_SWE_KEY = {
    WesternBody.URANUS: "uranus",
    WesternBody.NEPTUNE: "neptune",
    WesternBody.PLUTO: "pluto",
}

_HORIZONS_EVIDENCE = SourceReference(
    source_id="SRC-JPL-HORIZONS",
    locator=(
        "Geocentric apparent ecliptic longitude of date (quantity 31); fixtures "
        "horizons_transit_reference.json and western_outer_planets_horizons.json"
    ),
    verification_level="ENGINEERING-EVIDENCE",
    note=(
        "Swiss Ephemeris Moshier mode agrees within 0.63 arcsec for Uranus, Neptune and Pluto "
        "on 12 samples, and within the Phase 8 figures for the seven classical bodies."
    ),
)


class WesternChartService:
    """Stateless facade, like the other astro-engine services."""

    def __init__(self, ephemeris_path: str | None = _UNSET) -> None:  # type: ignore[assignment]
        resolved = Settings().ephemeris_path if ephemeris_path is _UNSET else ephemeris_path
        ephemeris.configure_ephemeris_path(resolved)

    def calculate(self, request: WesternChartRequest) -> WesternChartFacts:
        body_profile = BODY_PROFILES[request.body_profile_id]
        aspect_set = ASPECT_SET_PROFILES[request.aspect_set_profile_id]
        orb_profile = ORB_PROFILES[request.orb_profile_id]
        house_profile = HOUSE_PROFILES[request.house_profile_id]
        motion_profile = MOTION_PROFILES[request.motion_profile_id]

        utc, time_resolution = timezones.resolve_local_datetime(request.local_datetime)
        jd_et, jd_ut = ephemeris.utc_to_julian_day(
            utc.year,
            utc.month,
            utc.day,
            utc.hour,
            utc.minute,
            utc.second + utc.microsecond / 1_000_000,
        )
        time_resolution = time_resolution.model_copy(
            update={"julian_day_ut": jd_ut, "julian_day_et": jd_et}
        )

        raw = {
            body: _raw_position(
                jd_ut, body, request.node_convention, request.allow_moshier_fallback
            )
            for body in body_profile.bodies
        }

        exact_time = request.time_precision is WesternTimePrecision.EXACT
        houses = _houses(jd_ut, request, exact_time)

        positions = tuple(
            WesternBodyPosition(
                body=body,
                longitude=lon,
                latitude=lat,
                speed_longitude=speed,
                retrograde=speed < 0.0,
                sign=tropical_sign(lon),
                degree_in_sign=degree_in_sign(lon),
                house=house_of(lon, houses.cusps) if houses.cusps is not None else None,
                ephemeris_mode=mode,
            )
            for body, (lon, lat, speed, mode) in raw.items()
        )

        if exact_time:
            inputs = [
                aspect_calc.AspectInput(body, raw[body][0], raw[body][2])
                for body in body_profile.aspect_bodies
            ]
            found, blocked = aspect_calc.evaluate_aspects(inputs, aspect_set, orb_profile)
            aspects = WesternAspects(
                status=WesternStatus.SUCCESS, aspects=found, not_evaluable_pairs=blocked
            )
        else:
            aspects = WesternAspects(
                status=WesternStatus.NOT_EVALUABLE, reason=WesternReason.BIRTH_TIME_UNKNOWN
            )

        warnings: list[str] = []
        if not exact_time:
            warnings.append(
                "birth time unknown: positions are for the supplied clock time, which is a "
                "placeholder; houses, angles, house placement and aspects are not evaluated"
            )
        if any(p.ephemeris_mode is EphemerisMode.MOSHIER for p in positions):
            warnings.append(
                "Moshier analytical ephemeris used (no Swiss Ephemeris data files configured)"
            )
        if WesternBody.SOUTH_NODE in body_profile.bodies:
            warnings.append(
                "the south node is derived as the north node plus 180 degrees; the nodes take "
                "no part in aspects"
            )

        provenance = (
            ProvenanceEntry(
                entry_id="prov.zodiac",
                item=f"Zodiac: {ZODIAC_TROPICAL.profile_id}",
                evidence_label=ZODIAC_TROPICAL.label,
                statement=ZODIAC_TROPICAL.title,
                references=ZODIAC_TROPICAL.references,
            ),
            ProvenanceEntry(
                entry_id="prov.bodies",
                item=f"Bodies: {body_profile.profile_id}",
                evidence_label=body_profile.label,
                statement=body_profile.title,
                references=body_profile.references,
            ),
            ProvenanceEntry(
                entry_id="prov.houses",
                item=f"Houses: {house_profile.profile_id}",
                evidence_label=house_profile.label,
                statement=(
                    f"{house_profile.title}. Placement uses ecliptic longitude only and "
                    "half-open arcs [cusp n, cusp n+1) (engineering convention)."
                ),
                references=house_profile.references,
            ),
            ProvenanceEntry(
                entry_id="prov.aspects",
                item=f"Aspect set: {aspect_set.profile_id}",
                evidence_label=aspect_set.label,
                statement=(
                    f"{aspect_set.title}; measured in degrees on the shorter arc, orb "
                    "boundary inclusive (engineering convention)."
                ),
                references=aspect_set.references,
            ),
            ProvenanceEntry(
                entry_id="prov.orbs",
                item=f"Orbs: {orb_profile.profile_id}",
                evidence_label=orb_profile.label,
                statement=orb_profile.title,
                references=orb_profile.references,
            ),
            ProvenanceEntry(
                entry_id="prov.motion",
                item=f"Applying/separating: {motion_profile.profile_id}",
                evidence_label=motion_profile.label,
                statement=motion_profile.title,
                references=motion_profile.references,
            ),
            ProvenanceEntry(
                entry_id="prov.accuracy",
                item="Ephemeris accuracy evidence",
                evidence_label=EvidenceLabel.ENGINEERING_EVIDENCE,
                statement="Independent comparison of tropical longitudes with JPL Horizons.",
                references=(_HORIZONS_EVIDENCE,),
            ),
        )

        return WesternChartFacts(
            system=WESTERN_SYSTEM_ID,
            standards_version=WESTERN_STANDARDS_VERSION,
            engine_version=__version__,
            swisseph_version=ephemeris.swisseph_version(),
            ephemeris_path=ephemeris.configured_ephemeris_path(),
            profiles=ProfileIds(
                body_profile_id=body_profile.profile_id,
                house_profile_id=house_profile.profile_id,
                aspect_set_profile_id=aspect_set.profile_id,
                orb_profile_id=orb_profile.profile_id,
                motion_profile_id=motion_profile.profile_id,
                node_convention=request.node_convention,
            ),
            time_precision=request.time_precision,
            time_resolution=time_resolution,
            location=request.location,
            bodies=positions,
            houses=houses,
            aspects=aspects,
            provenance=provenance,
            warnings=tuple(warnings),
        )


def _raw_position(
    jd_ut: float,
    body: WesternBody,
    node_convention: NodeConvention | None,
    allow_moshier_fallback: bool,
) -> tuple[float, float, float, EphemerisMode]:
    if body in (WesternBody.NORTH_NODE, WesternBody.SOUTH_NODE):
        assert node_convention is not None  # enforced by request validation
        raw = ephemeris.calculate_body(
            jd_ut,
            ephemeris.SWE_NODE_ID[node_convention.value],
            sidereal=False,
            allow_moshier_fallback=allow_moshier_fallback,
        )
        if body is WesternBody.SOUTH_NODE:
            return (raw.longitude + 180.0) % 360.0, -raw.latitude, raw.speed_longitude, raw.mode
        return raw.longitude, raw.latitude, raw.speed_longitude, raw.mode
    swe_id = (
        ephemeris.SWE_BODY_ID[_CLASSICAL_SWE_KEY[body]]
        if body in _CLASSICAL_SWE_KEY
        else ephemeris.SWE_WESTERN_OUTER_BODY_ID[_OUTER_SWE_KEY[body]]
    )
    raw = ephemeris.calculate_body(
        jd_ut, swe_id, sidereal=False, allow_moshier_fallback=allow_moshier_fallback
    )
    return raw.longitude, raw.latitude, raw.speed_longitude, raw.mode


def _houses(jd_ut: float, request: WesternChartRequest, exact_time: bool) -> WesternHouses:
    if not exact_time:
        return WesternHouses(
            status=WesternStatus.NOT_EVALUABLE, reason=WesternReason.BIRTH_TIME_UNKNOWN
        )
    polar_limit = 90.0 - ephemeris.true_obliquity_degrees(jd_ut)
    latitude = request.location.latitude
    if abs(latitude) >= polar_limit:
        return WesternHouses(
            status=WesternStatus.NOT_EVALUABLE,
            reason=WesternReason.PLACIDUS_POLAR_CIRCLE,
            detail=f"|latitude| {abs(latitude)} >= 90 - true obliquity = {polar_limit}",
            polar_limit_degrees=polar_limit,
        )
    try:
        raw = ephemeris.calculate_placidus_houses(
            jd_ut, latitude=latitude, longitude=request.location.longitude
        )
    except HouseSystemUnavailableError as exc:
        return WesternHouses(
            status=WesternStatus.NOT_EVALUABLE,
            reason=WesternReason.PLACIDUS_NOT_COMPUTABLE,
            detail=str(exc),
            polar_limit_degrees=polar_limit,
        )
    return WesternHouses(
        status=WesternStatus.SUCCESS,
        cusps=raw.cusps,
        ascendant=raw.ascendant,
        midheaven=raw.midheaven,
        ascendant_sign=tropical_sign(raw.ascendant),
        midheaven_sign=tropical_sign(raw.midheaven),
        polar_limit_degrees=polar_limit,
    )
