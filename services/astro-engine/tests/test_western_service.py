"""Phase 9 WP-D: the Western chart service -- profiles, bodies, nodes,
provenance, determinism, independent reference longitudes and separation
from the Vedic modules (`docs/ASTROLOGY_STANDARDS.md` WD-01 to WD-20)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pandit_astro_engine import ephemeris
from pandit_astro_engine.errors import AmbiguousLocalTimeError, InvalidTimezoneError
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CalculationConfig,
    CelestialBody,
    DisambiguationPolicy,
    EphemerisMode,
    LocalDateTimeInput,
    Location,
    NodeConvention,
)
from pandit_astro_engine.service import AstronomicalCalculationService
from pandit_astro_engine.western import (
    ASPECTS_PTOLEMAIC_5_ID,
    BODIES_CLASSICAL_7_ID,
    BODIES_MODERN_10_ID,
    BODIES_MODERN_10_NODES_ID,
    HOUSES_PLACIDUS_ID,
    MOTION_INSTANTANEOUS_ID,
    ORB_FIXED_V1_ID,
    ORB_LILLY_MOIETY_ID,
    WESTERN_STANDARDS_VERSION,
    ZODIAC_TROPICAL_ID,
    WesternBody,
    WesternChartFacts,
    WesternChartRequest,
    WesternChartService,
    WesternReason,
    WesternStatus,
    WesternTimePrecision,
)
from pandit_astro_engine.western import profiles as western_profiles
from pandit_astro_engine.western.service import _raw_position
from pandit_astro_engine.western.zodiac import tropical_sign

FIXTURES = Path(__file__).parent / "fixtures"
PACKAGE = Path(__file__).parents[1] / "src" / "pandit_astro_engine" / "western"
B = WesternBody

_LONDON_1990 = LocalDateTimeInput(
    year=1990, month=6, day=15, hour=14, minute=30, timezone="Europe/London"
)
_LONDON = Location(latitude=51.5074, longitude=-0.1278)


def _request(**kwargs: object) -> WesternChartRequest:
    base: dict[str, object] = {
        "local_datetime": _LONDON_1990,
        "location": _LONDON,
        "time_precision": WesternTimePrecision.EXACT,
    }
    base.update(kwargs)
    return WesternChartRequest(**base)  # type: ignore[arg-type]


@pytest.fixture(scope="module")
def service() -> WesternChartService:
    return WesternChartService(ephemeris_path=None)


@pytest.fixture(scope="module")
def default_facts(service: WesternChartService) -> WesternChartFacts:
    return service.calculate(_request())


# ---------------------------------------------------------------- profiles


def test_defaults_are_recorded_in_the_result(default_facts: WesternChartFacts) -> None:
    p = default_facts.profiles
    assert p.zodiac_profile_id == ZODIAC_TROPICAL_ID
    assert p.body_profile_id == BODIES_MODERN_10_ID
    assert p.house_profile_id == HOUSES_PLACIDUS_ID
    assert p.aspect_set_profile_id == ASPECTS_PTOLEMAIC_5_ID
    assert p.orb_profile_id == ORB_FIXED_V1_ID
    assert p.motion_profile_id == MOTION_INSTANTANEOUS_ID
    assert p.node_convention is None
    assert default_facts.system == "western_tropical"
    assert default_facts.standards_version == WESTERN_STANDARDS_VERSION == "1.14.0"


def test_profile_ids_are_unique_and_stable() -> None:
    ids = [
        western_profiles.ZODIAC_TROPICAL_ID,
        *western_profiles.BODY_PROFILES,
        *western_profiles.HOUSE_PROFILES,
        *western_profiles.ASPECT_SET_PROFILES,
        *western_profiles.ORB_PROFILES,
        *western_profiles.MOTION_PROFILES,
    ]
    assert len(ids) == len(set(ids))
    assert sorted(ids) == sorted(
        [
            "WESTERN_ZODIAC_TROPICAL_OF_DATE",
            "WESTERN_BODIES_CLASSICAL_7",
            "WESTERN_BODIES_MODERN_10",
            "WESTERN_BODIES_MODERN_10_NODES",
            "WESTERN_HOUSES_PLACIDUS_SWISSEPH",
            "WESTERN_ASPECTS_PTOLEMAIC_5",
            "WESTERN_ORB_FIXED_V1",
            "WESTERN_ORB_LILLY_1647_MOIETY",
            "WESTERN_MOTION_INSTANTANEOUS_V1",
        ]
    )
    for pid in ids:
        assert pid.startswith("WESTERN_")


@pytest.mark.parametrize(
    "field",
    [
        "body_profile_id",
        "house_profile_id",
        "aspect_set_profile_id",
        "orb_profile_id",
        "motion_profile_id",
    ],
)
def test_unknown_profile_ids_are_rejected(field: str) -> None:
    with pytest.raises(ValidationError, match="unknown"):
        _request(**{field: "WESTERN_NOT_A_PROFILE"})


@pytest.mark.parametrize("house_id", ["koch", "WESTERN_HOUSES_WHOLE_SIGN", "WESTERN_HOUSES_EQUAL"])
def test_house_systems_other_than_placidus_are_not_offered(house_id: str) -> None:
    with pytest.raises(ValidationError):
        _request(house_profile_id=house_id)


def test_time_precision_is_required() -> None:
    with pytest.raises(ValidationError):
        WesternChartRequest(local_datetime=_LONDON_1990, location=_LONDON)  # type: ignore[call-arg]


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        _request(zodiac="sidereal")


# ---------------------------------------------------------------- bodies


def test_body_profiles_have_the_documented_members(service: WesternChartService) -> None:
    classical = service.calculate(_request(body_profile_id=BODIES_CLASSICAL_7_ID))
    assert [b.body for b in classical.bodies] == [
        B.SUN,
        B.MOON,
        B.MERCURY,
        B.VENUS,
        B.MARS,
        B.JUPITER,
        B.SATURN,
    ]
    modern = service.calculate(_request())
    assert [b.body for b in modern.bodies][-3:] == [B.URANUS, B.NEPTUNE, B.PLUTO]
    assert len(modern.bodies) == 10


def test_node_convention_is_required_only_with_the_node_profile() -> None:
    with pytest.raises(ValidationError, match="node_convention"):
        _request(body_profile_id=BODIES_MODERN_10_NODES_ID)
    with pytest.raises(ValidationError, match="node_convention"):
        _request(node_convention=NodeConvention.MEAN)
    _request(body_profile_id=BODIES_MODERN_10_NODES_ID, node_convention=NodeConvention.TRUE)


@pytest.mark.parametrize("convention", list(NodeConvention))
def test_nodes_are_positions_only_and_opposite(
    service: WesternChartService, convention: NodeConvention
) -> None:
    facts = service.calculate(
        _request(body_profile_id=BODIES_MODERN_10_NODES_ID, node_convention=convention)
    )
    assert facts.profiles.node_convention is convention
    by_body = {b.body: b for b in facts.bodies}
    north, south = by_body[B.NORTH_NODE], by_body[B.SOUTH_NODE]
    assert (north.longitude + 180.0) % 360.0 == pytest.approx(south.longitude, abs=1e-12)
    assert south.latitude == -north.latitude
    assert south.speed_longitude == north.speed_longitude
    for aspect in facts.aspects.aspects:
        assert B.NORTH_NODE not in (aspect.body_a, aspect.body_b)
        assert B.SOUTH_NODE not in (aspect.body_a, aspect.body_b)
    assert any("south node" in w for w in facts.warnings)


def test_mean_and_true_nodes_differ_and_are_never_mixed(service: WesternChartService) -> None:
    mean = service.calculate(
        _request(body_profile_id=BODIES_MODERN_10_NODES_ID, node_convention=NodeConvention.MEAN)
    )
    true = service.calculate(
        _request(body_profile_id=BODIES_MODERN_10_NODES_ID, node_convention=NodeConvention.TRUE)
    )
    mean_node = next(b for b in mean.bodies if b.body is B.NORTH_NODE)
    true_node = next(b for b in true.bodies if b.body is B.NORTH_NODE)
    assert mean_node.longitude != true_node.longitude
    assert abs(mean_node.longitude - true_node.longitude) < 2.0
    assert mean_node.retrograde  # the mean node always moves backwards


def test_retrograde_follows_the_speed_sign(default_facts: WesternChartFacts) -> None:
    for body in default_facts.bodies:
        assert body.retrograde is (body.speed_longitude < 0.0)
    by_body = {b.body: b for b in default_facts.bodies}
    assert not by_body[B.SUN].retrograde and not by_body[B.MOON].retrograde
    assert by_body[B.SATURN].retrograde  # Saturn was retrograde in mid-June 1990


def test_sign_fields_agree_with_longitude(default_facts: WesternChartFacts) -> None:
    for body in default_facts.bodies:
        assert body.sign is tropical_sign(body.longitude)
        assert 0.0 <= body.degree_in_sign < 30.0
        assert body.ephemeris_mode is EphemerisMode.MOSHIER


# ---------------------------------------------------------------- aspects


def test_lilly_profile_marks_outer_planet_pairs_not_evaluable(service: WesternChartService) -> None:
    facts = service.calculate(_request(orb_profile_id=ORB_LILLY_MOIETY_ID))
    blocked = facts.aspects.not_evaluable_pairs
    # 7 classical x 3 outer + 3 outer-outer pairs
    assert len(blocked) == 24
    assert all(p.reason is WesternReason.ORB_NOT_DEFINED_FOR_BODY for p in blocked)
    outer = {B.URANUS, B.NEPTUNE, B.PLUTO}
    for aspect in facts.aspects.aspects:
        assert not {aspect.body_a, aspect.body_b} & outer
    classical = service.calculate(
        _request(orb_profile_id=ORB_LILLY_MOIETY_ID, body_profile_id=BODIES_CLASSICAL_7_ID)
    )
    assert classical.aspects.not_evaluable_pairs == ()


def test_unknown_birth_time_does_not_evaluate_aspects(service: WesternChartService) -> None:
    facts = service.calculate(_request(time_precision=WesternTimePrecision.UNKNOWN))
    assert facts.aspects.status is WesternStatus.NOT_EVALUABLE
    assert facts.aspects.reason is WesternReason.BIRTH_TIME_UNKNOWN
    assert facts.aspects.aspects == ()
    assert len(facts.bodies) == 10  # positions at the supplied instant are still reported
    assert any("birth time unknown" in w for w in facts.warnings)


def test_known_aspects_of_the_london_chart(default_facts: WesternChartFacts) -> None:
    """Regression values computed by this module (Moshier), cross-checked by hand:
    Moon 346.19 and Jupiter 105.90 are 119.71 apart, a trine 0.29 from exact."""
    found = {(a.body_a, a.body_b): a for a in default_facts.aspects.aspects}
    trine = found[(B.MOON, B.JUPITER)]
    assert trine.aspect.value == "trine"
    assert trine.deviation == pytest.approx(0.291, abs=0.001)
    assert (B.SUN, B.MOON) in found and found[(B.SUN, B.MOON)].aspect.value == "square"


# ---------------------------------------------------------------- determinism and provenance


def test_results_are_deterministic_and_round_trip(service: WesternChartService) -> None:
    first = service.calculate(_request())
    second = service.calculate(_request())
    assert first.model_dump_json() == second.model_dump_json()
    restored = WesternChartFacts.model_validate_json(first.model_dump_json())
    assert restored == first


def test_provenance_covers_every_profile(default_facts: WesternChartFacts) -> None:
    entries = {p.entry_id: p for p in default_facts.provenance}
    assert set(entries) == {
        "prov.zodiac",
        "prov.bodies",
        "prov.houses",
        "prov.aspects",
        "prov.orbs",
        "prov.motion",
        "prov.accuracy",
    }
    assert entries["prov.orbs"].evidence_label.value == "engineering_convention"
    assert entries["prov.bodies"].evidence_label.value == "modern_tradition"
    assert entries["prov.houses"].references
    assert entries["prov.accuracy"].evidence_label.value == "engineering_evidence"


def test_time_resolution_uses_utc_and_the_input_timezone(default_facts: WesternChartFacts) -> None:
    tr = default_facts.time_resolution
    assert tr.timezone == "Europe/London"
    assert tr.utc_offset_seconds == 3600 and tr.dst_active
    assert tr.utc_datetime.hour == 13 and tr.utc_datetime.minute == 30
    assert tr.julian_day_ut > 0.0


def test_timezone_errors_are_raised_not_guessed(service: WesternChartService) -> None:
    ambiguous = LocalDateTimeInput(
        year=2023, month=10, day=29, hour=1, minute=30, timezone="Europe/London"
    )
    with pytest.raises(AmbiguousLocalTimeError):
        service.calculate(_request(local_datetime=ambiguous))
    later = ambiguous.model_copy(update={"disambiguation": DisambiguationPolicy.LATER})
    assert service.calculate(_request(local_datetime=later)).time_resolution.was_ambiguous
    with pytest.raises(InvalidTimezoneError):
        service.calculate(
            _request(
                local_datetime=LocalDateTimeInput(
                    year=2000, month=1, day=1, timezone="Mars/Olympus"
                )
            )
        )


# ---------------------------------------------------------------- independent reference


def _samples(name: str) -> list[dict[str, object]]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["samples"]  # type: ignore[no-any-return]


def _arcsec(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0) * 3600.0


def test_outer_planets_match_jpl_horizons() -> None:
    document = json.loads(
        (FIXTURES / "western_outer_planets_horizons.json").read_text(encoding="utf-8")
    )
    assert document["retrieved_on"] == "2026-09-24"
    assert document["sample_count"] == len(document["samples"]) == 12
    for sample in document["samples"]:
        lon, *_ = _raw_position(float(sample["julian_day_ut"]), B(sample["body"]), None, True)
        assert _arcsec(lon, float(sample["ecliptic_longitude_of_date_deg"])) < 1.0, sample


def test_classical_tropical_longitudes_match_jpl_horizons() -> None:
    names = {"sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"}
    for sample in _samples("horizons_transit_reference.json"):
        if sample["body"] not in names:
            continue
        lon, *_ = _raw_position(float(sample["julian_day_ut"]), B(sample["body"]), None, True)  # type: ignore[arg-type]
        tolerance = 6.0 if sample["body"] == "moon" else 1.0
        assert _arcsec(lon, float(sample["ecliptic_longitude_of_date_deg"])) < tolerance, sample  # type: ignore[arg-type]


# ---------------------------------------------------------------- separation from Vedic


def test_tropical_equals_sidereal_plus_ayanamsa(default_facts: WesternChartFacts) -> None:
    vedic = AstronomicalCalculationService(ephemeris_path=None).calculate(
        AstronomicalCalculationRequest(
            local_datetime=_LONDON_1990,
            location=_LONDON,
            config=CalculationConfig(),
            include_solar_events=False,
        )
    )
    ayanamsa = ephemeris.get_ayanamsa_degrees(vedic.metadata.time_resolution.julian_day_ut)
    assert 23.0 < ayanamsa < 24.5
    western = {b.body.value: b.longitude for b in default_facts.bodies}
    for name in ("sun", "moon", "mars", "saturn"):
        sidereal = getattr(vedic.planets, name).longitude
        # within the 15.6-arcsec frame difference already documented for Phase 8
        assert _arcsec(western[name], sidereal + ayanamsa) < 20.0


def test_the_vedic_body_set_is_unchanged() -> None:
    assert [b.value for b in CelestialBody] == [
        "sun",
        "moon",
        "mars",
        "mercury",
        "jupiter",
        "venus",
        "saturn",
        "rahu",
        "ketu",
    ]
    assert set(ephemeris.SWE_BODY_ID) == {
        "sun",
        "moon",
        "mars",
        "mercury",
        "jupiter",
        "venus",
        "saturn",
    }


_VEDIC_MODULES = {
    "pandit_astro_engine.aspects",
    "pandit_astro_engine.rashi",
    "pandit_astro_engine.nakshatra",
    "pandit_astro_engine.dignity",
    "pandit_astro_engine.lordship",
    "pandit_astro_engine.vargas",
    "pandit_astro_engine.kundli",
    "pandit_astro_engine.combustion",
    "pandit_astro_engine.planets",
    "pandit_astro_engine.dashas",
    "pandit_astro_engine.transits",
    "pandit_astro_engine.ashtakavarga",
    "pandit_astro_engine.jaimini",
    "pandit_astro_engine.partial_degree_drishti",
}


@pytest.mark.parametrize("path", sorted(PACKAGE.glob("*.py")), ids=lambda p: p.name)
def test_western_code_imports_no_vedic_module_or_swisseph(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert "swisseph" not in imported
    for name in imported:
        for vedic in _VEDIC_MODULES:
            assert not (name == vedic or name.startswith(vedic + ".")), (path.name, name)
