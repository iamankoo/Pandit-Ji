# astro-engine

Deterministic astronomical and chart calculation engine (`Phases.md` Phases 4, 5, 7, 8 and 9 WP-A1/A2/A3/WP-B-1/WP-B-2/WP-C). Canonical service name — do not rename to `astrology-engine`.

**Responsible for**: planetary positions (longitude/latitude/speed/degrees), retrograde, combustion, sunrise/sunset, deterministic timezone conversion (Phase 4); Ascendant/Lagna, whole-sign Houses/Bhavas, Rashi placement, Nakshatra/Pada, house lords, planetary aspects (graha drishti), planetary dignity, and the full locked Shodashvarga divisional-chart set plus the Chandra (Moon) chart (Phase 5); Vimshottari Dasha (Phase 7); transit / Gochar facts and Sade Sati (Phase 8); Ashtakavarga Bhinna and Sarva facts across four independent source profiles, and -- BPHS profiles only -- Trikona/Ekadhipatya Shodhana reductions and Pinda Sadhana (Phase 9 WP-A1/A2/A3); Rashi Drishti, a static sign-to-sign aspect table (Phase 9 WP-B-1); Chara Karaka ranking under two body-scope profiles and the separate Constant Karaka table (Phase 9 WP-B-2); a continuous, degree-based refinement of aspect strength, BPHS profile only so far (Phase 9 WP-C) — see `docs/ARCHITECTURE.md` §"Astrology Engine Architecture" and `docs/ASTROLOGY_STANDARDS.md` for the standards this implements.

**Not responsible for**: Yoga/Dosha rule evaluation, Ashtakavarga's Ch. 71 longevity calculation (blocked under the Ayurdaya policy) or Ch. 70/72 interpretive judgments, Chalit/Bhava-Chalit (explicitly deferred, see `docs/ASTROLOGY_STANDARDS.md`), any interpretation of Dasha, transit or Ashtakavarga facts, or narration. No HTTP, no database, no dependency on `agent`/`rule-engine`/`knowledge`/`verification`.

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

result.planets.sun.longitude  # absolute sidereal ecliptic longitude, degrees [0, 360)
result.planets.mercury.combustion  # CombustionStatus | None
result.planets.rahu.node_convention
result.solar_events.sunrise.utc_datetime
result.metadata.ephemeris_mode  # SWISS_EPHEMERIS_FILES | MOSHIER | JPL -- always disclosed
result.metadata.time_resolution  # local/UTC/ephemeris-time distinction, DST flags, offsets
```

See `models.py` for the full `CalculationResult` schema. Every `PlanetState` also carries its own `ephemeris_mode`, because the lunar node's position is computed analytically and can genuinely report a different mode than the planets in the same request — the aggregate `metadata.ephemeris_mode` never blurs that; it reports the lowest-precision mode present across all computed bodies.

## Kundli (Phase 5)

```python
from pandit_astro_engine import KundliCalculationService
from pandit_astro_engine.models import AstronomicalCalculationRequest, LocalDateTimeInput, Location

kundli = KundliCalculationService().calculate(
    AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=1947, month=8, day=15, hour=0, minute=0, timezone="Asia/Kolkata"
        ),
        location=Location(latitude=28.6139, longitude=77.2090, altitude_meters=216),
    )
)

kundli.lagna.rashi  # Ascendant sign (whole-sign House 1)
kundli.houses[0].lord  # House 1's lord
kundli.planets[1].nakshatra.pada  # A planet's Nakshatra + Pada
kundli.charts[9].planets  # Navamsa (D9) placements
kundli.chandra_chart.houses[0].rashi  # Chandra Lagna (Moon-as-Ascendant chart)
kundli.astronomical  # The embedded Phase 4 CalculationResult this was built from
```

`KundliCalculationService` wraps `AstronomicalCalculationService` (Phase 4) rather than duplicating any Swiss Ephemeris call: the single new primitive Phase 5 needs — the Ascendant — is added to `ephemeris.py`, the same adapter boundary Phase 4 established. See `kundli_models.py` for the full `Kundli` schema, `rashi.py`/`nakshatra.py`/`lordship.py`/`dignity.py`/`aspects.py`/`vargas.py` for each standard's implementation, and `docs/ASTROLOGY_STANDARDS.md` (v1.3.0) for the locked formulas themselves.

### Divisional charts (Vargas)

All sixteen locked Shodashvarga charts (D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D27, D30, D40, D45, D60) are available via `kundli.charts[varga_number]`, keyed by the varga's number. Each is derived purely from the same D1 sidereal longitudes (`vargas.py`) — never independently observed or separately calculated from the ephemeris. A chart's own Ascendant is the varga-transformed D1 Ascendant (classical practice: the Ascendant is treated as another ecliptic point for this purpose, not a separately-defined per-varga concept).

### Chandra (Moon) chart

`kundli.chandra_chart` applies the same whole-sign methodology as D1, but with the Moon's own sign as house 1 instead of the Ascendant. `None` only when the Moon was not among the requested bodies.

## Dasha (Phase 7)

`pandit_astro_engine.dashas` calculates the Vimshottari Dasha (Mahadasha, Antardasha, Pratyantar) as deterministic temporal facts with provenance. It produces no interpretation: no life-domain reading and no Maraka timing. Sookshma, Prana, other Dasha systems and birth-time rectification are out of scope.

```python
from pandit_astro_engine.dashas import DashaCalculationService, DashaTimeline

facts = DashaCalculationService().calculate(request)  # request: AstronomicalCalculationRequest
facts.status, facts.profile_ids  # SUCCESS; balance / year-length / sub-period profile IDs
facts.starting  # birth Nakshatra, Pada, lord, elapsed and remaining fraction
facts.periods  # flat, ordered period tree (parent_id, path, UTC boundaries)

timeline = DashaTimeline(facts)
timeline.resolve(instant_utc)  # Mahadasha / Antardasha / Pratyantar owning an instant
timeline.transitions(DashaLevel.ANTARDASHA)  # boundaries between consecutive periods
```

- **Profiles** (`docs/ASTROLOGY_STANDARDS.md` v1.5.0 section "Phase 7 methodology lock"): default balance `DASHA_STANDARD_V1_BALANCE_LONGITUDE`, default year `YEAR_365_2425_FIXED_DAY`, sub-periods `DASHA_SUBPERIOD_PROPORTIONAL_FULL_PARENT_V1`. These are Pandit Ji engineering conventions, not classical certainty; the balance method is a documented source conflict, and the two source-alternative balance profiles are registered as inactive rather than approximated.
- **Time**: UTC is canonical; arithmetic is exact rational microseconds from the birth instant with no calendar or leap-year arithmetic; each boundary is floored once to a whole microsecond.
- **Boundaries**: half-open [start, end); a shared boundary belongs to the later period; the timeline end is exclusive.
- **Precision**: EXACT, APPROXIMATE (needs an uncertainty interval; stable starting lord only) or NOT_EVALUABLE. An interval reaching a Nakshatra boundary is `NOT_EVALUABLE(starting_lord_ambiguous)`.
- **Failures** are structured (`status` plus `reason_code`), never guessed and never a stack trace.
- **Size**: a full three-level timeline is about 900 period nodes and roughly 0.7 MB as JSON; the evidence bundle records a compact form of each node.

## Transits (Phase 8)

`pandit_astro_engine.transits` calculates transit / Gochar facts with provenance: each planet's sign, degree, Nakshatra, speed and retrograde state; houses counted from the natal Moon (and, opt-in, the natal Lagna); favourable-house readings kept per source; the Phaladeepika-specific Vedha fact; sign-based contacts with natal planets; sign ingress, station and (opt-in) Nakshatra ingress events; and the Sade Sati sign-band timeline. It produces no interpretation: no good or bad verdict, prediction, remedy or alert. Ashtakavarga scoring, degree or orb contacts, Dhaiya, Ashtama Shani and degree-based Sade Sati variants are out of scope.

```python
import datetime as dt
from pandit_astro_engine.transits import NatalReference, TransitCalculationService

natal = NatalReference.from_kundli(kundli)  # kundli: the Phase 5 result
service = TransitCalculationService()
now = service.snapshot(natal, dt.datetime(2026, 9, 21, 12, tzinfo=dt.timezone.utc))
window = service.events(natal, start_utc, end_utc)  # ingress and station events
sade = service.sade_sati(natal, start_utc, end_utc)  # MODERN_TRADITION segments and episodes
now.snapshot.states, now.snapshot.favourable, now.snapshot.vedha, now.snapshot.contacts
```

- **Methodology** (`docs/ASTROLOGY_STANDARDS.md` v1.6.0, TR-01 to TR-15): default reference `TRANSIT_REF_MOON_SIGN`; four favourable-house readings (Phaladeepika, Brihat Samhita, Brihat Jataka, and a BPHS-derived reading) kept separately, with the Moon-from-Moon disagreement returned as `NOT_EVALUABLE(reading_ambiguous)`; Rahu and Ketu single-source and never consolidated; Vedha is a Phaladeepika-specific structural fact; Sade Sati is `SADE_SATI_SIGN_BASED_MODERN_V1`, a modern-tradition construct, not a classical rule.
- **Time**: UTC is canonical; sign, Nakshatra and window intervals are half-open `[start, end)`; ingress and station instants are found by bisection to 1e-8 day on a scan grid anchored to absolute multiples of the step, so an event's instant does not depend on the window that contains it.
- **Accuracy**: instants are numerical solutions and are never exact. Every result records the ephemeris mode, the ayanamsa, the solver tolerance and an accuracy disclosure (an independent 42-sample JPL Horizons comparison, engineering evidence only, and the ayanamsa-sensitivity note).
- **Limits**: a window of at most 200 years and at most 50,000 events; larger requests are `NOT_EVALUABLE` with no partial result.
- **Failures** are structured (`status` plus `reason_code`), never guessed and never a stack trace. An approximate natal time needs an explicit Moon range; a range reaching a sign boundary is `NOT_EVALUABLE(natal_moon_sign_ambiguous)`.

## Ashtakavarga (Phase 9 WP-A1, extended by WP-A2/A3)

`pandit_astro_engine.ashtakavarga` calculates Bhinnashtakavarga (per-planet, per-sign benefic-contributor counts) and Sarvashtakavarga (their sum) from natal sign placements only -- no ephemeris access. Four independent, page-verified source profiles are provided and none is a default; a caller must name one:

```python
from pandit_astro_engine.ashtakavarga import (
    AshtakavargaCalculationService,
    BRIHAT_JATAKA_ID,
)

request = AshtakavargaCalculationService.from_kundli_request(kundli, BRIHAT_JATAKA_ID)
facts = AshtakavargaCalculationService().calculate(request)
facts.charts, facts.sarva, facts.lagna_chart  # lagna_chart is None under this profile
```

- **Profiles** (`docs/ASTROLOGY_STANDARDS.md` v1.7.0, AV-01 to AV-08): `ASHTAKAVARGA_BRIHAT_JATAKA_SASTRI_IX_1_7`, `ASHTAKAVARGA_PHALADEEPIKA_SASTRI_XXIII_3_9`, `ASHTAKAVARGA_BPHS_GRID_KAPOOR_66`, `ASHTAKAVARGA_BPHS_VERSE_KAPOOR_66`. BPHS's own printed dot grid and its own printed verse-translation list disagree with each other on 5 of 56 cells inside the same chapter, so there is no unqualified "BPHS" profile.
- **Conflicts preserved, never resolved**: 9 of the 56 (chart, contributor) cells disagree across the four readings (`ashtakavarga.constants.CROSS_TABLE_CONFLICTS`); every profile still returns its own printed value at every cell, and two carry a translator's footnote (kept as `translator_note`, never merged).
- **Lagna's own chart** (BPHS Ch. 66 v. 65-68) is present only under the two BPHS profiles; Brihat Jataka and Phaladeepika are silent on it and it is never synthesized for them (`facts.lagna_chart` is `None`).
- **Out of scope** (deferred, not silently dropped): BPHS Ch. 71's Ashtakavarga-based longevity (blocked under the Ayurdaya policy -- lifespan/death-timing claims); Ch. 70 and 72's interpretive effect-judgments; any use by Shadbala's Drik Bala or by Gochara/transits (Phase 8); Rahu and Ketu are never Bhinnashtakavarga contributors (no source read gives either a table; they are used only for the WP-A2 occupancy test).
- **Failures** are structured (`status` plus `reason_code`): a missing Ascendant longitude is `NOT_EVALUABLE(lagna_unavailable)`; a missing planet longitude is `NOT_EVALUABLE(natal_positions_incomplete)`; a non-finite longitude is `INVALID_INPUT(non_finite_longitude)`; an unknown profile ID is `UNSUPPORTED_PROFILE`.

### Reductions and Pinda Sadhana (Phase 9 WP-A2/A3, BPHS profiles only)

`AshtakavargaCalculationService.calculate_reductions` computes Trikona Shodhana, Ekadhipatya Shodhana and Pinda Sadhana (Rasi, Graha and Yoga Pinda) -- a separate, additive request/response pair that leaves `calculate()` and `AshtakavargaFacts` completely unchanged:

```python
from pandit_astro_engine.ashtakavarga import AshtakavargaCalculationService, BPHS_GRID_ID

request = AshtakavargaCalculationService.from_kundli_reduction_request(kundli, BPHS_GRID_ID)
facts = AshtakavargaCalculationService().calculate_reductions(request)
facts.charts, facts.lagna_chart  # ChartReduction: trikona_corrected, ekadhipatya_corrected
facts.pinda, facts.lagna_pinda  # PindaResult: rasi_pinda, graha_pinda, yoga_pinda
```

- **BPHS-only** (`docs/ASTROLOGY_STANDARDS.md` v1.8.0, AV-09 to AV-13): no source read gives Brihat Jataka or Phaladeepika a reduction procedure at all. Requesting one under either profile returns `NOT_EVALUABLE(reduction_unsupported_for_profile)`, never a silently computed result.
- **Node positions required**: `NatalPositions.rahu_longitude` / `.ketu_longitude` are needed for Ekadhipatya Shodhana's occupancy test (a sign occupied only by Ketu counts as "with a planet", confirmed by BPHS's own worked example); missing either is `NOT_EVALUABLE(node_positions_required)`.
- **Exact integer arithmetic throughout**, verified against BPHS's own worked examples (Ch. 67 pp. 868-869, Ch. 68 p. 876, Ch. 69 pp. 879-880): Trikona Shodhana subtracts each trine group's minimum from all three; Ekadhipatya Shodhana leaves both-occupied pairs unchanged, reduces both by their minimum when neither is occupied, and otherwise keeps the occupied sign unchanged while clamping the empty one to `max(0, empty - occupied)`.
- **Three conflicts carried forward, never guessed**: Graha Pinda's multiplier for Sun/Moon/Saturn (5, proven by the worked example's own total, not the verse's stated 6) is resolved, but Mercury's (table 5 vs verse 6) is not -- a sign occupied solely by Mercury with a nonzero value makes that chart's Graha/Yoga Pinda `NOT_EVALUABLE(mercury_multiplier_conflict)`. A sign shared by more than one classical planet is `NOT_EVALUABLE(multiple_occupants_unsupported)` (no source states an aggregation rule) when nonzero. A lordship pair with exactly one sign occupied AND equal Trikona-corrected values is `NOT_EVALUABLE(ekadhipatya_equal_value_conflict)` for the *whole chart* -- BPHS's own printed illustration answers this exact shape two different ways in two different pairs (`ashtakavarga.models.EkadhipatyaConflict` keeps both readings, with provenance); since Rasi Pinda sums all 12 signs, one unresolved sign withholds the chart's entire Rasi, Graha and Yoga Pinda, not just that sign's contribution.

## Rashi Drishti (Phase 9 WP-B-1)

`pandit_astro_engine.jaimini` computes Rashi Drishti (BPHS Ch. 8 v. 1-3): a static, longitude-independent sign-to-sign aspect table, entirely separate from Phase 5/6's planet-to-house graha drishti (`aspects.py`). Only WP-B-1 is implemented; Chara Karaka (WP-B-2) and every other Jaimini system are out of scope until separately approved.

```python
from pandit_astro_engine.jaimini.rashi_drishti import has_rashi_drishti, rashi_drishti
from pandit_astro_engine.rashi import Rashi

rashi_drishti(Rashi.ARIES)  # (Rashi.LEO, Rashi.SCORPIO, Rashi.AQUARIUS)
has_rashi_drishti(Rashi.ARIES, Rashi.TAURUS)  # False -- Taurus is Aries's adjacent fixed sign
```

- **One profile, one source, no default needed**: `RASHI_DRISHTI_BPHS_8_1_3` (`jaimini.profiles`). BPHS's own translator note (page-image verified) attributes the rule to Parasara, not Jaimini, though it is commonly nicknamed the "Jaimini system" because Jaimini's own corpus also uses it.
- **Derived, not transcribed**: the table is computed from the already-locked Phase 5 `RASHI_MODALITY` classification (`rashi.py`), so it can never silently drift from the Chara/Sthira/Dwiswabhava table the rest of the engine uses; a dedicated test proves the derivation reproduces BPHS's own printed 12-sign table exactly.
- **Deliberately not implemented**: Ch. 8 v. 4-5 (the same table applied to a planet's own placement) is read and verified but excluded, because it would produce a planet-level aspect that disagrees with the already-locked Vedic graha drishti for the same placement — the two systems are never blended.

## Chara Karaka and Constant Karaka (Phase 9 WP-B-2)

`pandit_astro_engine.jaimini.chara_karaka` ranks planets by descending degree traversed within their own sign to name the eight Chara ("inconstant") Karakas (BPHS Ch. 32 v. 1-17); `pandit_astro_engine.jaimini.constant_karaka` gives the separate, static Constant Karaka table (v. 18-21). Re-verifying the source at page-image level (not reusing an earlier, less rigorous pass) found BPHS's own text does not settle its Chara Karaka candidate-body scope -- v. 1-2 states three positions ("Some say Rahu will become a Karka when there is a state of similarity in ... longitude ...; yet some say the 8 planets including Rahu will have to be considered irrespective of such a state") without choosing one.

```python
from pandit_astro_engine.jaimini.chara_karaka import CharaKarakaRequest, calculate_chara_karaka
from pandit_astro_engine.jaimini.profiles import CHARA_KARAKA_EIGHT_BODY_ID
from pandit_astro_engine.jaimini.constant_karaka import constant_karakas

result = calculate_chara_karaka(
    CharaKarakaRequest(profile_id=CHARA_KARAKA_EIGHT_BODY_ID, longitudes={...})
)
result.roles  # RoleAssignment per Karaka (Atma .. Dara), or None if the top rank is an unresolved tie

constant_karakas()  # the 8-entry static table; father/mother are NOT_EVALUABLE(strength_undefined)
```

- **Two profiles, no default, mirroring the Ashtakavarga precedent**: `JAIMINI_CHARA_KARAKA_SEVEN_BODY_BPHS_32_1_17` (the base rule, 7 classical planets) and `JAIMINI_CHARA_KARAKA_EIGHT_BODY_BPHS_32_1_17` (the "yet some say" 8-body-unconditional reading, which the chapter's own translator's note says is what its own worked example, "the standard nativity", actually uses). The third, conditional reading is read but not implemented (too underspecified). Ketu is never a candidate under any reading; supplying it is a validation error.
- **Rahu's reverse-degree convention** (v. 3-8, "deduct his longitude in that particular sign from 30") is applied before ranking; Atma Karaka ties are broken by minutes then seconds, matching the source exactly.
- **Deficit handling matches BPHS's own v. 13, not a synthetic shortcut**: a tie "identical to the second of arc" between two candidates makes both "qualified for that particular karakaatwa" (they share the role), and because roles fill strictly in rank order, the shortfall always lands on the *lowest* role in the fixed sequence -- reported as `NOT_EVALUABLE(rank_deficit)` for that role, exactly as the 7-body profile's structural 7-candidates-for-8-roles shortfall is reported too. A tie at the very top (Atma Karaka itself) instead makes the *whole* result `NOT_EVALUABLE(tie_unresolved)` (no partial role list), since every other Karaka is judged relative to Atma Karaka (v. 9-12) -- a Pandit Ji reading bridging v. 3-8 and v. 13, documented as such, not a single verse's explicit statement.
- **Constant Karaka is a separate, independent fact set, deliberately not auto-wired as the Chara Karaka deficit's substitute**: BPHS's own worked illustration demonstrates only one substitution (a deficient Dara Karaka falling back to Venus, the constant husband/wife significator); generalizing that one example into an automatic rule for the other six non-Atma roles would invent a mechanism the source does not fully specify. Two of the eight Constant Karaka significations ("the stronger" of Sun/Venus for father, Moon/Mars for mother) are `NOT_EVALUABLE(strength_undefined)`, reproducing a conflict this project already had on record rather than guessing a strength rule.

## Partial/Degree Drishti (Phase 9 WP-C, BPHS profile only)

`pandit_astro_engine.partial_degree_drishti.bphs` computes a continuous, degree-based refinement of planet-to-house aspect strength (BPHS Ch. 26), layered on top of Phase 5/6's discrete graha drishti but never merged with it. A second, methodology-locked profile (Uttara Kalamrita, citing Sripatipaddhati-II) exists in `docs/ASTROLOGY_STANDARDS.md` but is not implemented yet -- there is no default and no shared calculation path between the two.

```python
from pandit_astro_engine.partial_degree_drishti.bphs import (
    BphsDrishtiRequest,
    calculate_bphs_drishti,
)
from pandit_astro_engine.models import CelestialBody

calculate_bphs_drishti(
    BphsDrishtiRequest(
        aspecting_body=CelestialBody.MERCURY, aspecting_longitude=0.0, aspected_longitude=60.0
    )
).value  # 15.0 -- the 3rd house's quarter aspect
```

- **BPHS's own five-branch formula (v.6-9) is algebraically identical to linear interpolation** between the discrete checkpoints BPHS itself states (v.2-5) -- a project-level derivation, documented as such and never presented as the source's own claim.
- **Houses 9 and 10 are a permanent, unresolved source-internal conflict, not a bug**: BPHS's own literal reduction step (Sanskrit-confirmed as "10 signs", not a translation error) correctly reproduces house 8 but contradicts BPHS's own stated house-9/house-10 pairing. `NOT_EVALUABLE(reduction_rule_conflict)` for non-special planets there; no winner is chosen.
- **Saturn/Mars/Jupiter's own special-house peaks are exact, source-confirmed full aspects** (`SUCCESS`, value 60) at the precise angle; any other separation within that planet's own special house is `NOT_EVALUABLE(special_formula_interior_unresolved)` -- no tolerance is invented.
- **Rahu/Ketu as the aspecting body**: both BPHS Ch. 26 and Uttara Kalamrita Ch. 2 are silent on this; the silence is not resolved by inference. `RAHU`/`KETU` remain structurally valid inputs (never a validation error), and the result is `NOT_EVALUABLE(aspecting_node_unresolved)`.

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
- **`tests/test_kundli.py::test_golden_india_independence_chart`** validates the Kundli engine's Ascendant and Moon-sign computation against India's widely published Independence chart (15 Aug 1947, 00:00 IST, New Delhi: Taurus Ascendant, Moon in Cancer — e.g. astrotheme.com, jyotishgram.com) — genuinely independent of this codebase, unlike `tests/test_kundli_invariants.py`'s internal-consistency checks.

## Known limitations

- **No bulk independent reference dataset.** `Phases.md`'s "hundreds/thousands of birth dates" comparison against a trusted, independent reference source was **not performed at that scale** — no legitimate bulk independent ephemeris dataset (e.g. a licensed batch export from NASA JPL Horizons) was available in this environment. The four-case golden equinox/solstice set and the 2,000-case internal-consistency suite are real and passing, but they are not a substitute for that bulk independent comparison. Obtaining one (e.g. a JPL Horizons batch export, or a second independent ephemeris library used purely for cross-validation) is a follow-up task, not assumed complete here.
- **`rise_trans` searches forward from the given instant.** If the query instant is already local daytime, the "next sunrise" found may belong to the following calendar day while "next sunset" belongs to the current one (both are still correct, individually) — see `tests/test_solar_events.py` for the documented example. Phase 5+ callers computing a birth chart's "sunrise for that day" should search from local midnight, not the birth instant itself, if same-day pairing is required.
- **`SolarEvent.local_datetime` is not populated** (only `utc_datetime`) — a local-time conversion convenience, not added in Phase 4 to keep scope tight; UTC plus the request's timezone is sufficient to derive it.
- **Only Lahiri ayanamsa is implemented** (`models.Ayanamsa`) — the standards document only locks Lahiri for Phase 4; additional ayanamsas are a future, explicit addition, never silently assumed equivalent.
- **KP's sub-lord subdivision, Lal Kitab, and Nadi** remain out of scope per `docs/ASTROLOGY_STANDARDS.md` (Phase 9, after dedicated research validation) — this engine's `CalculationConfig` has no modes for them yet.
- **Chalit (Bhava-Chalit) and Ashtakvarga are explicitly deferred** for Phase 5 (`docs/ASTROLOGY_STANDARDS.md` "Chalit / Bhava-Chalit and Ashtakvarga — explicitly out of scope for Phase 5") — a documented scope exclusion, not a silent omission. Only the locked whole-sign Bhava convention is implemented.
- **Mooltrikona is not implemented** — dignity (`dignity.py`) is limited to exalted/debilitated/own-sign/neutral, per the locked standard.
- **D60 (Shashtiamsa) sign/degree placement only** — the classical 60-named-deity assignment per division is not asserted or implemented.
- **The Ascendant's own `ephemeris_mode` is not disclosed.** Swiss Ephemeris's `houses_ex` (used for the Ascendant) does not return a mode flag the way `calc_ut` does for planetary bodies, so `Kundli` carries no separate "which mode computed the Ascendant" field — only each planet's own `ephemeris_mode` (inherited from Phase 4) is available. This is a real gap in what Swiss Ephemeris's Python binding exposes, not an oversight.
- **Ascendant computation is astronomically degenerate at true polar latitudes** (±90°) — Swiss Ephemeris still returns a value there (verified: no crash), but the classical concept of a "rising sign" itself breaks down at the poles; this is an inherent astronomical limitation, not an engine bug.

## Testing

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest                        # 850 tests: unit, validation, determinism, boundary, golden, consistency, performance (Phases 4, 5, 7, 8 and 9 WP-A1/A2/A3)
ruff check .
ruff format --check .
mypy src
```

Performance (measured on this development machine, Moshier mode): ~0.5-0.7ms per full 9-body calculation; ~2,000-2,300 calculations/sec sustained batch throughput. Real Swiss Ephemeris file mode will differ (additional file I/O) but was not benchmarked here since no data files are configured in this environment.
