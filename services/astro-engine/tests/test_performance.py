"""Performance benchmark (Phase 4 prompt §32/§54). Loose bounds only --
this is a smoke-level performance guard, not a strict SLA; see the Phase 4
completion report for the actual measured numbers from this run.
"""

from __future__ import annotations

import time

from pandit_astro_engine import ephemeris
from pandit_astro_engine import planets as planets_module
from pandit_astro_engine.models import CalculationConfig, CelestialBody


def test_single_full_calculation_latency(capsys) -> None:
    ephemeris.configure_ephemeris_path(None)
    config = CalculationConfig()
    jd = 2451545.0

    start = time.perf_counter()
    planets_module.calculate_all_bodies(jd, config, list(CelestialBody))
    elapsed = time.perf_counter() - start

    with capsys.disabled():
        print(f"\nSingle full (9-body) calculation: {elapsed * 1000:.3f} ms")
    assert elapsed < 1.0  # generous smoke bound; real number reported separately


def test_batch_throughput(capsys) -> None:
    ephemeris.configure_ephemeris_path(None)
    config = CalculationConfig()
    n = 1000
    jds = [2415021.0 + i * 73.0 for i in range(n)]

    start = time.perf_counter()
    for jd in jds:
        planets_module.calculate_all_bodies(jd, config, list(CelestialBody))
    elapsed = time.perf_counter() - start

    per_calc_ms = (elapsed / n) * 1000
    throughput = n / elapsed
    with capsys.disabled():
        print(
            f"\nBatch of {n} full (9-body) calculations: {elapsed:.3f}s total, "
            f"{per_calc_ms:.3f} ms/calculation, {throughput:.1f} calculations/sec"
        )
    assert elapsed < 30.0  # generous smoke bound
