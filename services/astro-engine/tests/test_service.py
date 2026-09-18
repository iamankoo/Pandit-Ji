import pytest

from pandit_astro_engine import AstronomicalCalculationRequest, AstronomicalCalculationService
from pandit_astro_engine.errors import AmbiguousLocalTimeError
from pandit_astro_engine.models import (
    CalculationConfig,
    CelestialBody,
    EphemerisMode,
    LocalDateTimeInput,
    Location,
    NodeConvention,
    ZodiacType,
)


@pytest.fixture
def service() -> AstronomicalCalculationService:
    return AstronomicalCalculationService(ephemeris_path=None)


def _request(**overrides: object) -> AstronomicalCalculationRequest:
    defaults = dict(
        local_datetime=LocalDateTimeInput(
            year=2000, month=1, day=1, hour=6, minute=30, timezone="Asia/Kolkata"
        ),
        location=Location(latitude=28.6139, longitude=77.2090, altitude_meters=216),
    )
    defaults.update(overrides)
    return AstronomicalCalculationRequest(**defaults)  # type: ignore[arg-type]


def test_end_to_end_returns_all_bodies(service: AstronomicalCalculationService) -> None:
    result = service.calculate(_request())
    assert result.planets.sun.body == CelestialBody.SUN
    assert result.planets.ketu.body == CelestialBody.KETU
    assert result.metadata.ephemeris_mode == EphemerisMode.MOSHIER  # no ephemeris path configured
    assert result.metadata.swisseph_version


def test_determinism_full_result(service: AstronomicalCalculationService) -> None:
    request = _request()
    result1 = service.calculate(request)
    result2 = service.calculate(request)
    assert result1.model_dump() == result2.model_dump()


def test_metadata_captures_full_configuration(service: AstronomicalCalculationService) -> None:
    result = service.calculate(_request())
    metadata = result.metadata
    assert metadata.calculation_config.zodiac == ZodiacType.SIDEREAL
    assert metadata.calculation_config.ayanamsa is not None
    assert metadata.calculation_config.node_convention == NodeConvention.MEAN
    assert metadata.time_resolution.timezone == "Asia/Kolkata"
    assert metadata.time_resolution.julian_day_ut > 0
    assert metadata.time_resolution.julian_day_et > 0
    assert metadata.location.latitude == 28.6139


def test_sidereal_vs_tropical_differ_by_ayanamsa(service: AstronomicalCalculationService) -> None:
    sidereal_result = service.calculate(_request())
    tropical_result = service.calculate(
        _request(config=CalculationConfig(zodiac=ZodiacType.TROPICAL, ayanamsa=None))
    )
    diff = tropical_result.planets.sun.longitude - sidereal_result.planets.sun.longitude
    # Lahiri ayanamsa around year 2000 is documented as ~23.85 degrees.
    assert diff == pytest.approx(23.85, abs=0.05)


def test_ambiguous_time_propagates_as_typed_error(service: AstronomicalCalculationService) -> None:
    with pytest.raises(AmbiguousLocalTimeError):
        service.calculate(
            _request(
                local_datetime=LocalDateTimeInput(
                    year=2024,
                    month=11,
                    day=3,
                    hour=1,
                    minute=30,
                    timezone="America/New_York",
                ),
                location=Location(latitude=40.7128, longitude=-74.0060),
            )
        )


def test_partial_body_selection(service: AstronomicalCalculationService) -> None:
    # bodies is accepted on the request even though the current Planets
    # output model always requires all nine -- selecting a subset is
    # exercised at the planets.calculate_all_bodies layer directly
    # (test_planets.py); this confirms the full default path still works.
    result = service.calculate(_request(bodies=list(CelestialBody)))
    assert result.planets.moon.longitude != result.planets.sun.longitude
