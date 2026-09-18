import pytest

from pandit_astro_engine import ephemeris
from pandit_astro_engine import planets as planets_module
from pandit_astro_engine.models import CalculationConfig, CelestialBody, NodeConvention


@pytest.fixture(autouse=True)
def _no_ephemeris_path() -> None:
    ephemeris.configure_ephemeris_path(None)


# 2000-01-01 12:00 UT
_JD_UT = 2451545.0


def test_all_nine_bodies_present() -> None:
    config = CalculationConfig()
    states, _mode = planets_module.calculate_all_bodies(_JD_UT, config, list(CelestialBody))
    assert set(states.keys()) == set(CelestialBody)


def test_rahu_ketu_are_180_degrees_apart() -> None:
    config = CalculationConfig()
    states, _mode = planets_module.calculate_all_bodies(_JD_UT, config, list(CelestialBody))
    diff = (states[CelestialBody.KETU].longitude - states[CelestialBody.RAHU].longitude) % 360
    assert diff == pytest.approx(180.0, abs=1e-6)


def test_ketu_latitude_is_negated_rahu_latitude() -> None:
    config = CalculationConfig()
    states, _mode = planets_module.calculate_all_bodies(_JD_UT, config, list(CelestialBody))
    expected = -states[CelestialBody.RAHU].latitude
    assert states[CelestialBody.KETU].latitude == pytest.approx(expected)


def test_node_convention_changes_rahu_position() -> None:
    mean_config = CalculationConfig(node_convention=NodeConvention.MEAN)
    true_config = CalculationConfig(node_convention=NodeConvention.TRUE)
    mean_states, _ = planets_module.calculate_all_bodies(
        _JD_UT, mean_config, [CelestialBody.RAHU, CelestialBody.KETU]
    )
    true_states, _ = planets_module.calculate_all_bodies(
        _JD_UT, true_config, [CelestialBody.RAHU, CelestialBody.KETU]
    )
    # Mean and True node positions differ (materially, per docs/ASTROLOGY_STANDARDS.md);
    # they should not silently collapse to the same value.
    assert mean_states[CelestialBody.RAHU].longitude != true_states[CelestialBody.RAHU].longitude
    assert mean_states[CelestialBody.RAHU].node_convention == NodeConvention.MEAN
    assert true_states[CelestialBody.RAHU].node_convention == NodeConvention.TRUE


def test_mean_node_is_always_retrograde() -> None:
    # Mean node speed is definitionally always negative (continuous regression).
    config = CalculationConfig(node_convention=NodeConvention.MEAN)
    states, _ = planets_module.calculate_all_bodies(_JD_UT, config, [CelestialBody.RAHU])
    assert states[CelestialBody.RAHU].retrograde is True
    assert states[CelestialBody.RAHU].speed_longitude < 0


def test_longitude_normalized_to_0_360() -> None:
    config = CalculationConfig()
    states, _ = planets_module.calculate_all_bodies(_JD_UT, config, list(CelestialBody))
    for body, state in states.items():
        assert 0.0 <= state.longitude < 360.0, f"{body} longitude out of range: {state.longitude}"


def test_combustion_present_for_planets_absent_for_sun_and_nodes() -> None:
    config = CalculationConfig()
    states, _ = planets_module.calculate_all_bodies(_JD_UT, config, list(CelestialBody))
    assert states[CelestialBody.SUN].combustion is None
    assert states[CelestialBody.RAHU].combustion is None
    assert states[CelestialBody.KETU].combustion is None
    for body in (
        CelestialBody.MOON,
        CelestialBody.MARS,
        CelestialBody.MERCURY,
        CelestialBody.JUPITER,
        CelestialBody.VENUS,
        CelestialBody.SATURN,
    ):
        assert states[body].combustion is not None


def test_degree_components_reconstruct_longitude() -> None:
    config = CalculationConfig()
    states, _ = planets_module.calculate_all_bodies(_JD_UT, config, [CelestialBody.SUN])
    sun = states[CelestialBody.SUN]
    reconstructed = (
        sun.degree_components.degrees
        + sun.degree_components.minutes / 60
        + sun.degree_components.seconds / 3600
    )
    assert reconstructed == pytest.approx(sun.longitude, abs=1e-6)


def test_ketu_computed_without_rahu_in_request() -> None:
    # Regression: requesting Ketu alone must still compute it (derived from
    # Rahu internally) rather than silently omitting it.
    config = CalculationConfig()
    states, _mode = planets_module.calculate_all_bodies(_JD_UT, config, [CelestialBody.KETU])
    assert CelestialBody.KETU in states
    assert CelestialBody.RAHU not in states  # not requested, so not in the output


def test_combustion_computed_without_sun_in_request() -> None:
    # Regression: requesting a combustion-eligible planet alone must still
    # evaluate combustion (Sun's position computed internally as a
    # dependency) rather than silently leaving combustion unset.
    config = CalculationConfig()
    states, _mode = planets_module.calculate_all_bodies(_JD_UT, config, [CelestialBody.MERCURY])
    assert states[CelestialBody.MERCURY].combustion is not None
    assert CelestialBody.SUN not in states  # not requested, so not in the output


def test_aggregate_mode_reports_weakest_mode_when_bodies_mix() -> None:
    # Mean/True node calculations report a different underlying ephemeris
    # mode flag than planet calculations even under identical configuration
    # (see planets._aggregate_mode's docstring) -- the aggregate must never
    # arbitrarily pick one; it must disclose the lower-precision mode present.
    config = CalculationConfig()
    states, mode = planets_module.calculate_all_bodies(
        _JD_UT, config, [CelestialBody.SUN, CelestialBody.RAHU]
    )
    body_modes = {body: state.ephemeris_mode for body, state in states.items()}
    assert mode in body_modes.values()
    from pandit_astro_engine.models import EphemerisMode

    if EphemerisMode.MOSHIER in body_modes.values():
        assert mode == EphemerisMode.MOSHIER


def test_determinism_same_input_same_output() -> None:
    config = CalculationConfig()
    states1, mode1 = planets_module.calculate_all_bodies(_JD_UT, config, list(CelestialBody))
    states2, mode2 = planets_module.calculate_all_bodies(_JD_UT, config, list(CelestialBody))
    assert mode1 == mode2
    for body in CelestialBody:
        assert states1[body].model_dump() == states2[body].model_dump()
