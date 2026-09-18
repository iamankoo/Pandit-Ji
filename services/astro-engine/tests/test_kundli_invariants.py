"""Property/invariant and determinism tests for the Kundli engine, at scale
-- Phase 5 (Birth Chart / Kundli Engine). Mirrors the discipline in
test_consistency.py (Phase 4): validates internal consistency/determinism,
not independent astronomical accuracy (see test_kundli.py's golden case for
that)."""

from __future__ import annotations

import random

from pandit_astro_engine import ephemeris
from pandit_astro_engine.aspects import aspect_offsets
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.lordship import sign_lord
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CelestialBody,
    LocalDateTimeInput,
    Location,
)
from pandit_astro_engine.rashi import Rashi

N_CASES = 300

#: Vargas whose derivation formula is "count forward N signs from the D1
#: sign" (sign-relative) -- these preserve the Rahu/Ketu 180-degree
#: opposition through the transformation, since both bodies get the same
#: offset applied to signs that are themselves already 180 degrees apart.
#: The remaining vargas (D2, D16, D20, D24, D27, D30, D40, D45) use a fixed,
#: modality/parity-based *absolute* starting sign per docs/ASTROLOGY_STANDARDS.md
#: -- that is the correct classical convention for those vargas, but it means
#: opposite D1 signs can collapse onto the same varga sign. This is a real
#: property of the locked formulas, not a bug, and must not be asserted as a
#: universal invariant.
_SIGN_RELATIVE_VARGAS = (1, 3, 4, 7, 9, 10, 12, 60)


def _random_requests(count: int, seed: int = 7) -> list[AstronomicalCalculationRequest]:
    rng = random.Random(seed)
    requests = []
    for _ in range(count):
        jd = rng.uniform(2415021.0, 2488070.0)  # ~1900-01-01 .. 2100-01-01
        year, month, day, hour, minute, second = ephemeris.julian_day_to_utc_datetime_parts(jd)
        requests.append(
            AstronomicalCalculationRequest(
                local_datetime=LocalDateTimeInput(
                    year=year,
                    month=month,
                    day=day,
                    hour=hour,
                    minute=minute,
                    second=second,
                    timezone="UTC",
                ),
                location=Location(
                    latitude=rng.uniform(-60.0, 60.0), longitude=rng.uniform(-179.0, 179.0)
                ),
                include_solar_events=False,
            )
        )
    return requests


def test_every_chart_has_all_twelve_rashis_exactly_once() -> None:
    service = KundliCalculationService()
    for request in _random_requests(N_CASES):
        kundli = service.calculate(request)
        for chart in [*kundli.charts.values(), kundli.chandra_chart]:
            if chart is None:
                continue
            house_numbers = sorted(house.house for house in chart.houses)
            assert house_numbers == list(range(1, 13))
            assert {house.rashi for house in chart.houses} == set(Rashi)


def test_house_lord_always_matches_sign_lord_table() -> None:
    service = KundliCalculationService()
    for request in _random_requests(N_CASES):
        kundli = service.calculate(request)
        for chart in [*kundli.charts.values(), kundli.chandra_chart]:
            if chart is None:
                continue
            for house in chart.houses:
                assert house.lord == sign_lord(house.rashi)
            for placement in chart.planets:
                assert placement.house_lord == sign_lord(placement.rashi)


def test_planet_house_matches_the_chart_house_list() -> None:
    service = KundliCalculationService()
    for request in _random_requests(N_CASES):
        kundli = service.calculate(request)
        house_rashi_by_number = {house.house: house.rashi for house in kundli.houses}
        for planet in kundli.planets:
            assert house_rashi_by_number[planet.house] is planet.rashi


def test_aspect_count_matches_offset_table() -> None:
    service = KundliCalculationService()
    for request in _random_requests(N_CASES):
        kundli = service.calculate(request)
        for planet in kundli.planets:
            assert len(planet.aspected_houses) == len(aspect_offsets(planet.body))
            assert all(1 <= house <= 12 for house in planet.aspected_houses)


def test_rahu_ketu_180_degrees_preserved_through_sign_relative_vargas() -> None:
    from pandit_astro_engine.rashi import rashi_index

    service = KundliCalculationService()
    for request in _random_requests(N_CASES):
        kundli = service.calculate(request)
        rahu = next(p for p in kundli.planets if p.body == CelestialBody.RAHU)
        ketu = next(p for p in kundli.planets if p.body == CelestialBody.KETU)
        for varga in _SIGN_RELATIVE_VARGAS:
            chart = kundli.charts[varga]
            rahu_rashi = next(p.rashi for p in chart.planets if p.body == CelestialBody.RAHU)
            ketu_rashi = next(p.rashi for p in chart.planets if p.body == CelestialBody.KETU)
            assert (rashi_index(ketu_rashi) - rashi_index(rahu_rashi)) % 12 == 6
        # And the underlying D1 fact this all rests on:
        assert (rashi_index(ketu.rashi) - rashi_index(rahu.rashi)) % 12 == 6


def test_determinism_across_repeated_calculation() -> None:
    service = KundliCalculationService()
    for request in _random_requests(50, seed=99):
        first = service.calculate(request)
        second = service.calculate(request)
        assert first.model_dump() == second.model_dump()


def test_dignity_only_evaluated_for_seven_classical_grahas() -> None:
    service = KundliCalculationService()
    for request in _random_requests(N_CASES):
        kundli = service.calculate(request)
        for planet in kundli.planets:
            if planet.body in (CelestialBody.RAHU, CelestialBody.KETU):
                assert planet.dignity is None
            else:
                assert planet.dignity is not None
