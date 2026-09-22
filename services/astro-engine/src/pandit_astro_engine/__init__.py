"""astro-engine: deterministic astronomical and chart calculation engine.

Phase 4 (Astronomical Calculation Engine): Swiss Ephemeris-backed
planetary positions (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn,
Rahu, Ketu), retrograde, combustion, sunrise/sunset, and deterministic
timezone conversion.

Phase 5 (Birth Chart / Kundli Engine): Ascendant/Lagna, whole-sign
houses/Bhavas, Rashi placement, Nakshatra/Pada, house lords, planetary
aspects (graha drishti), planetary dignity, and the full locked
Shodashvarga set of divisional charts (D1, D2, D3, D4, D7, D9, D10, D12,
D16, D20, D24, D27, D30, D40, D45, D60) plus the Chandra (Moon) chart --
see `docs/ARCHITECTURE.md` §"Astrology Engine Architecture" and
`docs/ASTROLOGY_STANDARDS.md` for the standards this package implements.

Phase 7 (Dasha & Timing Engine): Vimshottari Dasha to the Pratyantar level
as deterministic temporal facts with provenance (`pandit_astro_engine.dashas`);
see `docs/ASTROLOGY_STANDARDS.md` section "Phase 7 methodology lock".

Phase 8 (Transit / Gochar Engine): deterministic transit facts, ingress and
station events and the Sade Sati sign-band timeline (a MODERN_TRADITION
profile) with provenance (`pandit_astro_engine.transits`); see
`docs/ASTROLOGY_STANDARDS.md` section "Transit / Gochar standards".

Phase 9 WP-A1/A2/A3 (Ashtakavarga): Bhinnashtakavarga and Sarvashtakavarga
facts across four independent, never-merged source profiles (Brihat Jataka,
Phaladeepika, and BPHS's own printed dot grid and printed verse-translation
list, which disagree with each other on 5 of 56 cells), and -- BPHS
profiles only -- Trikona/Ekadhipatya Shodhana reductions and Pinda Sadhana
(Rasi/Graha/Yoga Pinda), with provenance (`pandit_astro_engine.ashtakavarga`);
see `docs/ASTROLOGY_STANDARDS.md` section "Ashtakavarga standards".

Phase 9 WP-B-1 (Jaimini, Rashi Drishti only): a static, longitude-independent
sign-to-sign aspect table (BPHS Ch. 8 v. 1-3), kept strictly separate from
Phase 5/6's planet-to-house graha drishti (`pandit_astro_engine.jaimini`);
see `docs/ASTROLOGY_STANDARDS.md` section "Jaimini standards". No other
Jaimini system (Chara Karaka, Jaimini Dashas, Arudha Pada, Karakamsa, ...)
is implemented yet.

Yoga/Dosha rule evaluation, Dasha and transit interpretation, Ashtakavarga
Ch. 71's longevity calculation (blocked under the Ayurdaya policy), narration,
and any AI/LLM involvement remain out of scope here and belong to later
phases and other services (`rule-engine`, `agent`, `knowledge`) -- see each
phase's boundary section in `Phases.md`.

This package remains a pure library: no HTTP, no database access, no
dependency on `agent`, `rule-engine`, `knowledge`, or `verification`.
"""

from pandit_astro_engine._version import __version__
from pandit_astro_engine.health import get_health
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.kundli_models import Kundli
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CalculationResult,
    CelestialBody,
)
from pandit_astro_engine.service import AstronomicalCalculationService

__all__ = [
    "get_health",
    "__version__",
    "AstronomicalCalculationService",
    "AstronomicalCalculationRequest",
    "CalculationResult",
    "CelestialBody",
    "KundliCalculationService",
    "Kundli",
]
