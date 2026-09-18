import pytest

from pandit_astro_engine.errors import (
    InvalidLatitudeError,
    InvalidLongitudeError,
    UnsupportedConfigurationError,
)
from pandit_astro_engine.models import Ayanamsa, CalculationConfig, Location, ZodiacType


def test_location_accepts_valid_range() -> None:
    loc = Location(latitude=-90, longitude=-180)
    assert loc.latitude == -90
    loc2 = Location(latitude=90, longitude=180)
    assert loc2.longitude == 180


@pytest.mark.parametrize("latitude", [90.0001, -90.0001, 200, -200])
def test_location_rejects_invalid_latitude(latitude: float) -> None:
    with pytest.raises(InvalidLatitudeError):
        Location(latitude=latitude, longitude=0)


@pytest.mark.parametrize("longitude", [180.0001, -180.0001, 400, -400])
def test_location_rejects_invalid_longitude(longitude: float) -> None:
    with pytest.raises(InvalidLongitudeError):
        Location(latitude=0, longitude=longitude)


def test_config_rejects_ayanamsa_with_tropical() -> None:
    with pytest.raises(UnsupportedConfigurationError):
        CalculationConfig(zodiac=ZodiacType.TROPICAL, ayanamsa=Ayanamsa.LAHIRI)


def test_config_rejects_missing_ayanamsa_with_sidereal() -> None:
    with pytest.raises(UnsupportedConfigurationError):
        CalculationConfig(zodiac=ZodiacType.SIDEREAL, ayanamsa=None)


def test_config_default_is_sidereal_lahiri_mean_node() -> None:
    config = CalculationConfig()
    assert config.zodiac == ZodiacType.SIDEREAL
    assert config.ayanamsa == Ayanamsa.LAHIRI
    assert config.node_convention.value == "mean"
