# astro-engine

Deterministic astronomical calculation engine (`Phases.md` Phase 4). Canonical service name — do not rename to `astrology-engine`.

**Responsible for**: planetary positions (longitude/latitude/speed/degrees), retrograde, combustion, sunrise/sunset, and deterministic timezone conversion — see `docs/ARCHITECTURE.md` §"Astrology Engine Architecture" and `docs/ASTROLOGY_STANDARDS.md` for the standards this implements.

**Not responsible for**: chart/Kundli domain concepts (ascendant, houses, nakshatra/pada assignment, divisional charts, dignity, lords — Phase 5), rule evaluation, interpretation, or narration. No HTTP, no database, no dependency on `agent`/`rule-engine`/`knowledge`/`verification`.

## Purpose

Given a birth/query instant (local date+time+timezone) and a location (latitude/longitude), compute the geocentric ecliptic positions of the Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, and the lunar nodes (Rahu/Ketu), plus derived retrograde and combustion status, plus sunrise/sunset — deterministically and reproducibly, via Swiss Ephemeris.

## Architecture

```
AstronomicalCalculationRequest
        v
AstronomicalCalculationService  (service.py -- the only public entrypoint)
        v
timezones.py (local -> UTC, DST-aware)   ephemeris.py (Swiss Ephemeris adapter -- the ONLY module that imports `swisseph`)
        v                                        v
planets.py (per-body orchestration) ----> combustion.py (derived layer, pure arithmetic, no ephemeris calls)
        v
solar_events.py (sunrise/sunset via the same adapter)
        v
CalculationResult (models.py)
```

`ephemeris.py` is the sole Swiss Ephemeris boundary (Phase 4 prompt §38): every other module reaches the library through it, never directly. This keeps upgrades, licensing, configuration, and error handling in one place, and makes every other module trivially testable without a real ephemeris call.

## Input / output contract

```python
from pandit_astro_engine import AstronomicalCalculationRequest, AstronomicalCalculationService
from pandit_astro_engine.models import LocalDateTimeInput, Location

service = AstronomicalCalculationService()  # reads ASTRO_ENGINE_EPHEMERIS_PATH from the environment
result = service.calculate(
    AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=2000, month=1, day=1, hour=6, minute=30, timezone="Asia/Kolkata"
        ),
        location=Location(latitude=28.6139, longitude=77.2090, altitude_meters=216),
    )
)

result.planets.sun.longitude       # absolute sidereal ecliptic longitude, degrees [0, 360)
result.planets.mercury.combustion  # CombustionStatus | None
result.planets.rahu.node_convention
result.solar_events.sunrise.utc_datetime
result.metadata.ephemeris_mode     # SWISS_EPHEMERIS_FILES | MOSHIER | JPL -- always disclosed
result.metadata.time_resolution    # local/UTC/ephemeris-time distinction, DST flags, offsets
```

See `models.py` for the full `CalculationResult` schema. Every `PlanetState` also carries its own `ephemeris_mode`, because the lunar node's position is computed analytically and can genuinely report a different mode than the planets in the same request — the aggregate `metadata.ephemeris_mode` never blurs that; it reports the lowest-precision mode present across all computed bodies.

## Supported bodies

Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu (`models.CelestialBody`) — stable, machine-readable identifiers used consistently everywhere in this codebase.

## Units and precision

- Longitude/latitude: degrees, double precision (`float`), never prematurely rounded internally.
- Longitude is always normalized to `[0, 360)`.
- Speed: degrees/day, sign preserved (negative = retrograde).
- `degree_components`: degree/minute/second decomposition of the **absolute** longitude, derived purely arithmetically from the precise value — this is not sign-relative degree (that's a Phase 5 Rashi-placement concept).
- Combustion separation/thresholds: degrees, per `docs/ASTROLOGY_STANDARDS.md` "Combustion standard."

## Timezone handling

IANA timezone identifiers via Python's `zoneinfo` (backed by the `tzdata` package), giving correct historical offsets and DST rules for arbitrary valid zones — never hard-coded IST or any other zone's logic. Ambiguous (DST fall-back) and nonexistent (DST spring-forward gap) local times raise a typed error (`AmbiguousLocalTimeError` / `NonexistentLocalTimeError`) by default; callers can opt into `DisambiguationPolicy.EARLIER`/`LATER` to resolve explicitly instead of the engine silently guessing. `TimeResolution` in every result distinguishes local civil time, UTC (UT1), and Ephemeris/Terrestrial Time (ET), plus the resolved UTC offset and DST-active flag.

## Ephemeris data

Swiss Ephemeris supports three calculation modes: full-precision JPL-derived `.se1` data files, Swiss Ephemeris's own Moshier analytical approximation (no external files, ~1 arcsecond accuracy), or JPL ephemeris files directly. **This repository does not, and will not, commit `.se1` data files** — they carry the same license terms as the Swiss Ephemeris software itself (`LEGAL_REGULATIONS.md`: locked to the Professional License route, not yet purchased).

- Configure `ASTRO_ENGINE_EPHEMERIS_PATH` (see root `.env.example`) to point at a local directory of legitimately-obtained `.se1` files for full precision.
- If unset (the default for local development in this repository), the engine explicitly uses the Moshier fallback — never silently; every result's `metadata.ephemeris_mode` (and each `PlanetState.ephemeris_mode`) discloses exactly which mode produced it.
- Setting `CalculationConfig.allow_moshier_fallback=False` makes the engine raise `EphemerisDataUnavailableError` instead of silently using Moshier, for callers that require full-precision-or-fail behavior.

### Licensing prerequisite

Swiss Ephemeris Professional License is locked as the production/commercial-distribution route (`LEGAL_REGULATIONS.md`) and has **not yet been purchased** — this is a pre-production/legal task, not a Phase 4 engineering task. `pyswisseph` (the Python binding used here) is AGPL-3.0-licensed for development use, which is what this phase uses; production/commercial distribution must not proceed until the Professional License is purchased and the agreement is signed (`Phases.md` Phase 21 gate).

## Deterministic behavior

Every calculation is a pure function of `(local_datetime, location, config)` — no hidden state, no network calls, no randomness. Verified by `tests/test_consistency.py` across 2,000 randomized instants: identical input always produces a byte-identical `CalculationResult`.

## Reference validation methodology

- **`tests/test_reference_validation.py`** validates tropical Sun longitude against four independently published 2024 equinox/solstice UTC instants (`datasets/fixtures/astro_engine/golden_solstice_equinox.json`, sourced from timeanddate.com/CBS News/thesuntoday.org — genuinely independent of this codebase, since an equinox/solstice is defined by the Sun's tropical longitude being exactly 0°/90°/180°/270° by astronomical definition). All four matched to within 0.0007°, against a 0.01° tolerance.
- **`tests/test_consistency.py`** validates internal determinism and invariants (Rahu/Ketu 180° relationship, longitude range, retrograde-vs-speed-sign consistency, combustion-threshold consistency) across 2,000 randomized instants spanning 1900-2100. This is **not** independent accuracy validation — it validates that the engine is internally consistent at scale, which is a different (and honestly labeled) claim.
- **`tests/test_boundary.py`** covers a real, documented Mercury retrograde station (Dec 2023/Jan 2024), degree wraparound near 0°/360°, midnight/date-line boundaries, and the ~26-hour real-world gap between the UTC+14 and UTC-12 timezone extremes.

## Known limitations

- **No bulk independent reference dataset.** `Phases.md`'s "hundreds/thousands of birth dates" comparison against a trusted, independent reference source was **not performed at that scale** — no legitimate bulk independent ephemeris dataset (e.g. a licensed batch export from NASA JPL Horizons) was available in this environment. The four-case golden equinox/solstice set and the 2,000-case internal-consistency suite are real and passing, but they are not a substitute for that bulk independent comparison. Obtaining one (e.g. a JPL Horizons batch export, or a second independent ephemeris library used purely for cross-validation) is a follow-up task, not assumed complete here.
- **`rise_trans` searches forward from the given instant.** If the query instant is already local daytime, the "next sunrise" found may belong to the following calendar day while "next sunset" belongs to the current one (both are still correct, individually) — see `tests/test_solar_events.py` for the documented example. Phase 5+ callers computing a birth chart's "sunrise for that day" should search from local midnight, not the birth instant itself, if same-day pairing is required.
- **`SolarEvent.local_datetime` is not populated** (only `utc_datetime`) — a local-time conversion convenience, not added in Phase 4 to keep scope tight; UTC plus the request's timezone is sufficient to derive it.
- **Only Lahiri ayanamsa is implemented** (`models.Ayanamsa`) — the standards document only locks Lahiri for Phase 4; additional ayanamsas are a future, explicit addition, never silently assumed equivalent.
- **KP's sub-lord subdivision, Lal Kitab, and Nadi** remain out of scope per `docs/ASTROLOGY_STANDARDS.md` (Phase 9, after dedicated research validation) — this engine's `CalculationConfig` has no modes for them yet.

## Testing

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest                        # 72 tests: unit, validation, determinism, boundary, golden, consistency, performance
ruff check .
ruff format --check .
mypy src
```

Performance (measured on this development machine, Moshier mode): ~0.5-0.7ms per full 9-body calculation; ~2,000-2,300 calculations/sec sustained batch throughput. Real Swiss Ephemeris file mode will differ (additional file I/O) but was not benchmarked here since no data files are configured in this environment.
