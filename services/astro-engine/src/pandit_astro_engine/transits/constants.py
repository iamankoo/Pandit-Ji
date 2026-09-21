"""Transit / Gochar constants (docs/ASTROLOGY_STANDARDS.md v1.6.0, TR-10, TR-11).

Every value here is a Pandit Ji engineering convention, not a classical source
statement. The scan steps are chosen so a body cannot cross a sign or Nakshatra
boundary and come back inside one step except around a station, which the
scanner handles explicitly (see `events.py`).
"""

from __future__ import annotations

from pandit_astro_engine.models import CelestialBody

SYSTEM_ID = "transit_gochara"

#: Standards version under which Phase 8 results are produced
#: (docs/ASTROLOGY_STANDARDS.md v1.6.0, Phase 8 methodology lock).
TRANSIT_STANDARDS_VERSION = "1.6.0"

#: Pandit Ji engineering convention (as in Phase 7); no source states one.
BOUNDARY_CONVENTION = "half_open_start_inclusive_end_exclusive"
TIME_BASE = "utc"

#: Bisection stops when the bracket is at most this many days wide (~0.86 ms).
SEARCH_TOLERANCE_DAYS = 1e-8
SEARCH_TOLERANCE_SECONDS = SEARCH_TOLERANCE_DAYS * 86_400.0

#: A request window may not exceed this many years of 365.2425 days.
MAX_WINDOW_YEARS = 200
MAX_WINDOW_DAYS = MAX_WINDOW_YEARS * 365.2425
#: A window may not produce more events than this (no partial list is returned).
MAX_EVENTS = 50_000

#: Scan step in days per body (docs TR-10).
SCAN_STEP_DAYS: dict[CelestialBody, float] = {
    CelestialBody.MOON: 0.25,
    CelestialBody.MERCURY: 0.5,
    CelestialBody.VENUS: 1.0,
    CelestialBody.SUN: 2.0,
    CelestialBody.MARS: 2.0,
    CelestialBody.JUPITER: 5.0,
    CelestialBody.SATURN: 5.0,
    CelestialBody.RAHU: 5.0,
    CelestialBody.KETU: 5.0,
}

ALL_BODIES: tuple[CelestialBody, ...] = tuple(CelestialBody)
NODES: tuple[CelestialBody, ...] = (CelestialBody.RAHU, CelestialBody.KETU)

#: Engineering-evidence record for the accuracy disclosure (TR-10).
HORIZONS_EVIDENCE = (
    "engineering_evidence: 42-sample comparison of the Swiss Ephemeris tropical longitude of date "
    "(Moshier mode, through the Phase 4 adapter) with JPL Horizons (geocentric apparent ecliptic "
    "longitude of date), 7 bodies x 6 dates 1950-2060, retrieved 2026-09-21; maximum differences "
    "0.26 arcsec (Sun), 0.19 (Mars), 0.15 (Mercury, Venus), 0.38 (Jupiter), 0.27 (Saturn), 4.78 "
    "(Moon); planetary longitude only, the Lahiri ayanamsa value is not independently verified, "
    "and the ayanamsa implied by the sidereal calculation differs from get_ayanamsa_ut by up to "
    "about 15.6 arcsec (nutation scale, about 1.5 hours of Saturn's motion; not investigated)"
)
