"""Phase 9 WP-D: Placidus houses and house placement
(`docs/ASTROLOGY_STANDARDS.md` WD-06 to WD-08).

The Placidus reference below is an independent implementation written for
these tests from the definition in the Swiss Ephemeris documentation
(section 6.2.1: cusp 11 has completed 2/3 and cusp 12 1/3 of its
semi-diurnal arc, cusps 2 and 3 likewise on the semi-nocturnal arc) with the
standard Ascendant and MC formulas. It takes only the ARMC and the true
obliquity from Swiss Ephemeris, so it checks the house division itself."""

from __future__ import annotations

import math
import random

import pytest

from pandit_astro_engine import ephemeris
from pandit_astro_engine.errors import (
    HouseSystemUnavailableError,
    InvalidLatitudeError,
    InvalidLongitudeError,
)
from pandit_astro_engine.models import LocalDateTimeInput, Location
from pandit_astro_engine.western import (
    WesternChartRequest,
    WesternChartService,
    WesternReason,
    WesternStatus,
    WesternTimePrecision,
)
from pandit_astro_engine.western.houses import house_of, validate_cusps

ARCSEC = 1.0 / 3600.0
_rad, _deg = math.radians, math.degrees


def _ra_to_lon(ra: float, eps: float) -> float:
    return _deg(math.atan2(math.sin(_rad(ra)), math.cos(_rad(ra)) * math.cos(_rad(eps)))) % 360.0


def _semi_diurnal_arc(lon: float, eps: float, phi: float) -> float:
    dec = math.asin(math.sin(_rad(eps)) * math.sin(_rad(lon)))
    return _deg(math.acos(-math.tan(_rad(phi)) * math.tan(dec)))


def _reference_cusp(armc: float, eps: float, phi: float, cusp: int) -> float:
    def target(sda: float) -> float:
        sna = 180.0 - sda
        return {
            11: armc + sda / 3.0,
            12: armc + 2.0 * sda / 3.0,
            2: armc + 180.0 - 2.0 * sna / 3.0,
            3: armc + 180.0 - sna / 3.0,
        }[cusp]

    ra = armc + {11: 30.0, 12: 60.0, 2: 120.0, 3: 150.0}[cusp]
    for _ in range(500):
        new = target(_semi_diurnal_arc(_ra_to_lon(ra, eps), eps, phi))
        if abs((new - ra + 180.0) % 360.0 - 180.0) < 1e-12:
            ra = new
            break
        ra = new
    return _ra_to_lon(ra, eps)


def _reference_placidus(armc: float, eps: float, phi: float) -> list[float]:
    mc = _ra_to_lon(armc, eps)
    asc = (
        _deg(
            math.atan2(
                math.cos(_rad(armc)),
                -(
                    math.sin(_rad(armc)) * math.cos(_rad(eps))
                    + math.tan(_rad(phi)) * math.sin(_rad(eps))
                ),
            )
        )
        % 360.0
    )
    c11, c12, c2, c3 = (_reference_cusp(armc, eps, phi, k) for k in (11, 12, 2, 3))
    opp = lambda x: (x + 180.0) % 360.0  # noqa: E731
    return [asc, c2, c3, opp(mc), opp(c11), opp(c12), opp(asc), opp(c2), opp(c3), mc, c11, c12]


def _diff(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def test_placidus_matches_an_independent_implementation() -> None:
    rng = random.Random(2026)
    worst = 0.0
    for _ in range(250):
        jd = 2_415_020.0 + rng.random() * 73_000.0
        eps = ephemeris.true_obliquity_degrees(jd)
        limit = 90.0 - eps
        phi = rng.uniform(-limit + 0.5, limit - 0.5)
        raw = ephemeris.calculate_placidus_houses(
            jd, latitude=phi, longitude=rng.uniform(-180, 180)
        )
        reference = _reference_placidus(raw.armc, eps, phi)
        for got, want in zip(raw.cusps, reference, strict=True):
            worst = max(worst, _diff(got, want))
        assert _diff(raw.ascendant, raw.cusps[0]) == 0.0
        assert _diff(raw.midheaven, raw.cusps[9]) == 0.0
        validate_cusps(raw.cusps)
    assert worst < 0.01 * ARCSEC, worst


def test_polar_boundary_matches_swiss_ephemeris() -> None:
    jd = 2_451_545.0
    limit = 90.0 - ephemeris.true_obliquity_degrees(jd)
    ephemeris.calculate_placidus_houses(jd, latitude=limit - 1e-6, longitude=10.0)
    ephemeris.calculate_placidus_houses(jd, latitude=-(limit - 1e-6), longitude=10.0)
    for lat in (limit, limit + 1e-6, 70.0, -70.0, 89.9, 90.0, -90.0):
        with pytest.raises(HouseSystemUnavailableError):
            ephemeris.calculate_placidus_houses(jd, latitude=lat, longitude=10.0)


# ---------------------------------------------------------------- placement

_EQUAL = tuple(float(30 * i) for i in range(12))
_UNEVEN = (350.0, 20.0, 45.0, 80.0, 130.0, 160.0, 170.0, 200.0, 225.0, 260.0, 310.0, 340.0)


def test_placement_is_half_open_at_each_cusp() -> None:
    for i, cusp in enumerate(_UNEVEN):
        assert house_of(cusp, _UNEVEN) == i + 1
        assert house_of(math.nextafter(cusp, -1.0) % 360.0, _UNEVEN) == (i - 1) % 12 + 1


def test_placement_across_zero_degrees() -> None:
    assert house_of(355.0, _UNEVEN) == 1
    assert house_of(0.0, _UNEVEN) == 1
    assert house_of(19.999, _UNEVEN) == 1
    assert house_of(345.0, _UNEVEN) == 12
    assert house_of(0.0, _EQUAL) == 1
    assert house_of(359.99, _EQUAL) == 12


@pytest.mark.parametrize(
    "cusps",
    [
        _EQUAL[:11],
        tuple(reversed(_EQUAL)),
        (0.0, 0.0, *_EQUAL[2:]),
        (0.0, 60.0, 30.0, *_EQUAL[3:]),
    ],
)
def test_invalid_cusp_sets_are_rejected(cusps: tuple[float, ...]) -> None:
    with pytest.raises(ValueError):
        house_of(10.0, cusps)


# ---------------------------------------------------------------- service


def _request(lat: float, lon: float = 0.0, **kwargs: object) -> WesternChartRequest:
    return WesternChartRequest(
        local_datetime=LocalDateTimeInput(year=2000, month=1, day=1, hour=12, timezone="UTC"),
        location=Location(latitude=lat, longitude=lon),
        time_precision=kwargs.pop("time_precision", WesternTimePrecision.EXACT),  # type: ignore[arg-type]
        **kwargs,  # type: ignore[arg-type]
    )


@pytest.fixture(scope="module")
def service() -> WesternChartService:
    return WesternChartService(ephemeris_path=None)


@pytest.mark.parametrize("lat", [0.0, 28.6139, 51.5074, -33.8688, 64.1466, 66.0, -66.0])
def test_houses_are_evaluated_below_the_polar_circle(
    service: WesternChartService, lat: float
) -> None:
    facts = service.calculate(_request(lat))
    houses = facts.houses
    assert houses.status is WesternStatus.SUCCESS
    assert houses.cusps is not None and len(houses.cusps) == 12
    validate_cusps(houses.cusps)
    assert houses.ascendant == houses.cusps[0]
    assert houses.midheaven == houses.cusps[9]
    assert houses.polar_limit_degrees is not None and abs(lat) < houses.polar_limit_degrees
    for body in facts.bodies:
        assert body.house == house_of(body.longitude, houses.cusps)


@pytest.mark.parametrize("lat", [66.6, -66.6, 70.0, 78.2232, -80.0, 90.0, -90.0])
def test_houses_are_not_evaluable_inside_the_polar_circle(
    service: WesternChartService, lat: float
) -> None:
    facts = service.calculate(_request(lat))
    houses = facts.houses
    assert houses.status is WesternStatus.NOT_EVALUABLE
    assert houses.reason is WesternReason.PLACIDUS_POLAR_CIRCLE
    assert houses.cusps is None and houses.ascendant is None and houses.midheaven is None
    assert all(body.house is None for body in facts.bodies)
    # positions and aspects do not depend on the house system
    assert facts.aspects.status is WesternStatus.SUCCESS


def test_polar_limit_is_inclusive_in_the_service(service: WesternChartService) -> None:
    limit = service.calculate(_request(0.0)).houses.polar_limit_degrees
    assert limit is not None
    assert service.calculate(_request(limit)).houses.reason is WesternReason.PLACIDUS_POLAR_CIRCLE
    below = service.calculate(_request(math.nextafter(limit, 0.0)))
    assert below.houses.status is WesternStatus.SUCCESS


def test_a_swiss_ephemeris_failure_is_reported_not_substituted(
    service: WesternChartService, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise HouseSystemUnavailableError("swisseph.houses_ex: did not converge")

    monkeypatch.setattr(ephemeris, "calculate_placidus_houses", fail)
    houses = service.calculate(_request(40.0)).houses
    assert houses.status is WesternStatus.NOT_EVALUABLE
    assert houses.reason is WesternReason.PLACIDUS_NOT_COMPUTABLE
    assert houses.detail is not None and "did not converge" in houses.detail
    assert houses.cusps is None


def test_unknown_birth_time_leaves_houses_not_evaluable(service: WesternChartService) -> None:
    facts = service.calculate(_request(28.6, time_precision=WesternTimePrecision.UNKNOWN))
    assert facts.houses.status is WesternStatus.NOT_EVALUABLE
    assert facts.houses.reason is WesternReason.BIRTH_TIME_UNKNOWN
    assert facts.houses.polar_limit_degrees is None
    assert all(body.house is None for body in facts.bodies)


@pytest.mark.parametrize(
    ("lat", "lon", "error"),
    [
        (90.0001, 0.0, InvalidLatitudeError),
        (-91.0, 0.0, InvalidLatitudeError),
        (0.0, 180.5, InvalidLongitudeError),
        (0.0, -181.0, InvalidLongitudeError),
    ],
)
def test_invalid_coordinates_are_rejected(lat: float, lon: float, error: type[Exception]) -> None:
    with pytest.raises((error, ValueError)):
        _request(lat, lon)
