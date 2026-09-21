# Pandit Ji Astrology Standards

Status: **LOCKED canonical location** — `docs/ASTROLOGY_STANDARDS.md` is the single, authoritative document for calculation standards, Vedic defaults, ayanamsa, zodiac, house systems, ephemeris configuration, astronomical calculation requirements, astrology methodology separation, interpretation standards, reproducibility, uncertainty, and versioning. There is no separate `docs/calculation-standards.md` — any earlier reference to that filename referred to this document and should be treated as resolved in favor of this one.

Version: 1.6.0 (Phase 8 transit methodology lock, on top of the v1.5.0 Phase 7 methodology lock, the v1.4.1 Nakshatra/Pada boundary-convention clarification and the v1.4.0 Phase 6 lock — see §Versioning at the end of this document for the change log).

This document defines **standards and methodology contracts**, not implementations. Every section below states what a later phase's engine must compute and how, not the engine itself. Each section names the `Phases.md` phase responsible for the actual implementation.

## Core rule
**Facts flow one direction; AI only narrates.**

The AI must never independently calculate planetary positions, houses, ascendant, nakshatra/pada, divisional charts, dashas, transits, yogas/doshas, Panchang timings, Muhurta windows, numerology numbers, or compatibility scores.

## AI scope boundary

- **Self-hosted requirement**: Pandit Ji's core astrology reasoning (chart interpretation, prediction, agent planning, personalization, knowledge reasoning, core chatbot responses) must not depend on external hosted proprietary LLM APIs. See `research/AI_MODELS.md` and `docs/ARCHITECTURE.md` §16's `LLMProvider`/AI Reasoner interface for the technical mechanism; this document fixes it as a standing product requirement, not merely an implementation preference.
- **Fact-vs-narration boundary**: the AI consumes structured facts and evidence bundles produced by the calculation engine, rule engine, and knowledge base (defined in this document and `docs/ARCHITECTURE.md`); it narrates and explains them, and never originates them. This is the same invariant as the Core rule above, restated as an explicit AI-scope requirement per Phase 1 exit criteria.

## Language and multilingual interaction

Standards and product-interaction requirement, locked per explicit project-owner decision (v1.4.0). It is not implemented in Phase 6; the Agent phase (`Phases.md` Phase 15) and the UI phases implement it.

- **Language understanding**: Pandit Ji's AI must understand English, Hindi, Hinglish, Romanized Hindi, mixed English/Hindi and natural code-switching (including within one conversation). This applies regardless of the UI language. There is **no AI language toggle** and no separate English, Hindi or Hinglish AI modes.
- **UI language**: controlled separately through Account → Language. Supported UI languages are English and हिन्दी. New users default to English, and the selected UI language persists per account. Changing the UI language does not automatically force the AI's response language, and the UI never changes because of the language the user types.
- **AI response language**: AI language understanding is multilingual by default. UI language selection is independent from AI language understanding. Agent-phase response-language behavior is defined in the Agent phase and is not defined here.
- **Language-neutral facts**: canonical astrology facts, rules, evidence and calculations use stable identifiers and structured tags, never language-specific phrases; language is realized only at the interaction and presentation layers.
- This section adds no model-specific, provider-specific, UI-implementation or language-classification requirements.

## Default Vedic profile
- Zodiac: Sidereal
- Ayanamsa: Lahiri
- House baseline: Vedic whole-sign
- Degree-level planetary positions, with sufficient underlying precision (minutes/seconds) retained internally for reproducibility even where a UI rounds for display
- Explicit versioned calculation configuration (see §Reproducibility)

Alternate systems (Western/Tropical, KP, Lal Kitab, Nadi, etc.) must be selected explicitly per calculation — never silently substituted for the Vedic default.

### Time standards
Birth time must be normalized correctly and never silently guessed when critical information is missing. Required handling:
- Timezone at the birth location and date (not the user's current timezone)
- Historical timezone changes (a location's UTC offset may have differed from its present-day offset on the birth date)
- DST where applicable for that location/date
- Conversion to UTC before any ephemeris calculation, with local civil time retained alongside it for display/audit
- If the user provides an approximate time (see §Birth-time uncertainty), that approximation must be preserved through the whole pipeline, not resolved into a false-precision exact timestamp

### Location standards
Birthplace must be represented using latitude, longitude, timezone, and historical timezone/DST information where required. Missing or ambiguous critical location/time data must be surfaced to the user for clarification, never silently guessed or defaulted.

## Astrology systems (methodology separation)

Pandit Ji supports multiple astrology methodologies. **Systems must not be silently mixed** — a Vedic answer must never silently apply Western, KP, Lal Kitab, or Nadi rules, and vice versa. Every calculation and every rule/interpretation must be tagged with the system it belongs to. When methodologies are intentionally compared for a user, both must be explicitly labeled as such.

For each system: system identity, zodiac/basis, house methodology (where applicable), core calculation assumptions, major interpretive methodology, source/tradition separation, and configuration/versioning are defined below. Detailed rule content and the actual engines are implemented in later phases as noted; this section fixes the assumptions those phases must implement against.

### Vedic / Jyotish (default)
- Zodiac: Sidereal (Lahiri ayanamsa, per Default Vedic profile above)
- Houses: Vedic whole-sign
- Core assumptions: Parashari framework — divisional charts (§Divisional charts), Vimshottari Dasha (§Vimshottari Dasha), Nakshatra-based timing (§Nakshatra standards), Parashari yoga/dosha rules (§Yoga/Dosha standards)
- Interpretive methodology: classical Parashari/Jaimini traditions, cited per rule (see `research/ASTROLOGY_SOURCES.md`)
- Implemented across Phases 4-8 (calculation foundation, Kundli engine, rule engine, Dasha/transit engine)

### Western / Tropical
- Zodiac: Tropical (no ayanamsa/precession correction — this is the defining difference from the Vedic sidereal profile, not an alternate ayanamsa value)
- Houses: Placidus (default Western house system)
- Core assumptions: same underlying ephemeris/planetary-position engine as Vedic, computed against the tropical zero point instead of sidereal; same aspect-detection mechanism, tropical orb conventions
- Interpretive methodology: traditional Western natal astrology by default; psychological/humanistic framing is a configurable interpretive layer, not a calculation difference
- Source/tradition separation: Western interpretive rules must never be applied to a Vedic (sidereal) chart or vice versa
- Configuration: a distinct `calculation_config` row (`zodiac_type=tropical`, `house_system=placidus`)
- Implemented in Phase 9 (Advanced Astrology Systems)

### KP (Krishnamurti Paddhati)
- Zodiac: Sidereal, but using the **Krishnamurti ayanamsa**, not Lahiri — this must be a distinct, explicit configuration value; KP must never silently reuse the Vedic default's Lahiri ayanamsa
- Houses: Placidus cusps (KP's traditional house basis)
- Core assumptions: the sub-lord theory — each nakshatra (already divided by the 9 Vimshottari lords) is further subdivided into 249 sub-divisions using the same 9-lord proportional scheme applied recursively (sub-lord, and traditionally sub-sub-lord); significators are derived from house/cuspal sub-lord analysis
- Interpretive methodology: KP significator and ruling-planet analysis, distinct from Parashari yogas
- Source/tradition separation: KP must not reuse Parashari yoga/dosha rules; its own rule set is separate
- Implemented in Phase 9
- Note: the sub-lord subdivision arithmetic must be validated against an authoritative KP reference before implementation (see `docs/ARCHITECTURE.md` §30)

### Lal Kitab
- Basis: differs fundamentally from Parashari Vedic astrology — traditional Lal Kitab practice does not use the varga (divisional chart) system or nakshatra-based timing the way Parashari Jyotish does, and historically some variants work from a simplified, fixed house-based chart representation rather than degree-precision positions
- Core assumptions: **provisional, pending dedicated source validation** — this document does not assert a final Lal Kitab calculation methodology as settled fact. An astrology-literate reviewer must validate the exact chart-construction and remedy-derivation rules against recognized Lal Kitab texts (`research/ASTROLOGY_SOURCES.md`) before Phase 9 implements it
- Interpretive methodology: remedies are the central interpretive output in Lal Kitab practice; remedy content must be sourced and tagged the same way as any other traditional rule (§Yoga/Dosha standards' source/tradition requirement applies equally here)
- Source/tradition separation: Lal Kitab houses/rules must never be silently combined with Parashari Vedic houses/rules, even though both may present a similar 12-house layout
- Implemented in Phase 9, after research validation

### Nadi
- Basis: Vedic sidereal, but traditional Nadi Jyotish practice relies on extremely precise birth time and, historically, matching a chart to pre-recorded leaf texts at a fine-grained subdivision finer than the standard varga scheme
- Core assumptions: **provisional, pending dedicated source validation**, for the same reason as Lal Kitab above — generic rule-based computation may not faithfully represent traditional Nadi practice, which is traditionally text-matching rather than generic rule evaluation. This document intentionally does not assert a specific Nadi computational methodology as final.
- Source/tradition separation: Nadi timing/interpretation must not be silently substituted for or merged with standard Parashari Vimshottari timing
- Implemented in Phase 9, after research validation

### Numerology, Chinese astrology, Tarot, Vastu/Feng Shui, Horary, Palmistry
- Numerology: see the dedicated §Numerology standards section below (implemented Phase 11)
- Chinese astrology, Tarot, Vastu/Feng Shui, Horary: system identity acknowledged as in-scope per `features.md`; each requires its own dedicated methodology definition before implementation, following the same pattern as the systems above (system identity, basis, core assumptions, source/tradition separation, non-mixing rule); detailed standards for these are deferred to the phase that implements them (Phase 9 for KP/Lal Kitab/Nadi/Western/Chinese, Phase 17 for cross-domain analysis touching Vastu) and must be written before that phase begins, following this document's format
- Palmistry: AI Palm Reading is a locked product feature (`features.md` §34); see §Palmistry below for the interpretation-boundary standard, and `Phases.md` Phase 13 (Palm Reading & Vision Intelligence) for the dedicated vision-pipeline/rule-layer implementation

## Divisional charts (Vargas)

Defines the standard and contract that **Phase 5 (Birth Chart / Kundli Engine)** implements — not implemented in Phase 1.

- **D1 / Rashi chart**: the base birth chart — each planet's sidereal longitude placed directly into its zodiac sign and house, using the Default Vedic profile's ayanamsa/house baseline. All other divisional charts are derived from this same set of longitudes; D1 is the foundation, not a division.
- **D9 / Navamsa**: each of the 12 signs is divided into 9 equal parts of 3°20′ each; a planet's Navamsa sign is determined by classical Parashari rule based on which 3°20′ segment its longitude falls into and the modality (movable/fixed/dual) of its D1 sign, per the standard starting-point convention. Represents marriage, spouse, dharma, and the inner strength of D1 placements.
- **Divisional-chart framework**: Pandit Ji's locked varga set is the classical Shodashvarga (16 principal divisional charts): D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D27, D30, D40, D45, D60. Each varga is derived deterministically from the same D1 sidereal longitudes via its classical division formula — no varga is independently observed or separately calculated from the ephemeris.
- **What each chart represents** (canonical significations, to be expanded per-varga during Phase 5): D1 = self/body/overall life; D2 (Hora) = wealth; D3 (Drekkana) = siblings/courage; D4 (Chaturthamsa) = property/home/fortune; D7 (Saptamsa) = children/progeny; D9 (Navamsa) = marriage/spouse/dharma; D10 (Dasamsa) = career/profession; D12 (Dwadasamsa) = parents; D16 (Shodasamsa) = vehicles/general happiness; D20 (Vimsamsa) = spiritual pursuits; D24 (Chaturvimsamsa) = education/learning; D27 (Nakshatramsa/Bhamsa) = strengths/weaknesses; D30 (Trimsamsa) = misfortunes/challenges; D40 (Khavedamsa) = auspicious/inauspicious effects; D45 (Akshavedamsa) = general life conduct; D60 (Shashtiamsa) = overall past-karma/fine-grained life analysis.
- **Chart-specific applicability**: which varga is authoritative for which life-domain question is determined by the domain-to-varga mapping used in `docs/ARCHITECTURE.md` §8's Astrology Planner (e.g., a marriage question requires D1 + D9; a career question requires D1 + D10). This mapping is finalized during Phase 5/Phase 17, not Phase 1.
- **Versioning/configuration**: the varga division scheme (classical Parashari, as fixed above) is part of `calculation_config`; if an alternate varga scheme is ever supported, it must be a distinct, explicit configuration value, never silently substituted.

### Varga derivation formulas

Locked per explicit project-owner decision (see §Versioning change log) during Phase 5's mandatory standards audit. Each formula below is the classical Parashari (Brihat Parashara Hora Shastra) derivation, applied to a planet's precise D1 sidereal longitude and sign. "Same sign" always means the planet's own D1 sign; sign counting is always forward/zodiacal.

- **D1 (Rashi)**: identity — see above.
- **D2 (Hora)**, 2 × 15°: odd D1 sign — 0-15° = Sun's Hora (maps to Leo), 15-30° = Moon's Hora (maps to Cancer); even D1 sign — reversed (0-15° = Moon's Hora/Cancer, 15-30° = Sun's Hora/Leo).
- **D3 (Drekkana)**, 3 × 10°: 0-10° = same sign; 10-20° = 5th sign from it; 20-30° = 9th sign from it (BPHS trine-counting rule — the "sequential" alternate convention some software uses is explicitly not adopted).
- **D4 (Chaturthamsa)**, 4 × 7°30′: parts land on the same, 4th, 7th, and 10th sign from the D1 sign, in that order (kendra/quadrant counting).
- **D7 (Saptamsa)**, 7 × 4°17′8.571…″: odd D1 sign — count of 7 consecutive signs starts at the same sign; even D1 sign — starts at the 7th sign from it.
- **D9 (Navamsa)**: see above.
- **D10 (Dasamsa)**, 10 × 3°: odd D1 sign — count of 10 consecutive signs starts at the same sign; even D1 sign — starts at the 9th sign from it.
- **D12 (Dwadasamsa)**, 12 × 2°30′: count of 12 consecutive signs always starts at the same sign (no odd/even distinction).
- **D16 (Shodasamsa)**, 16 × 1°52′30″: count of 16 consecutive signs (cycling the zodiac as needed) starts at Aries for movable D1 signs, Leo for fixed, Sagittarius for dual.
- **D20 (Vimsamsa)**, 20 × 1°30′: count starts at Aries for movable D1 signs, Sagittarius for fixed, Leo for dual.
- **D24 (Chaturvimsamsa / Siddhamsa)**, 24 × 1°15′ (two full zodiac cycles): odd D1 sign — count starts at Leo; even D1 sign — starts at Cancer.
- **D27 (Nakshatramsa / Bhamsa)**, 27 × 1°6′40″: count starts at Aries for movable D1 signs, Cancer for fixed, Libra for dual.
- **D30 (Trimsamsa)**, 30 divisions, non-equal spans: odd D1 sign — Mars rules 0-5° (maps to Aries), Saturn 5-10° (Aquarius), Jupiter 10-18° (Sagittarius), Mercury 18-25° (Gemini), Venus 25-30° (Libra); even D1 sign — Venus rules 0-5° (Taurus), Mercury 5-12° (Virgo), Jupiter 12-20° (Pisces), Saturn 20-25° (Capricorn), Mars 25-30° (Scorpio).
- **D40 (Khavedamsa)**, 40 × 0°45′: odd D1 sign — count starts at Aries; even D1 sign — starts at Libra.
- **D45 (Akshavedamsa)**, 45 × 0°40′: count starts at Aries for movable D1 signs, Leo for fixed, Sagittarius for dual.
- **D60 (Shashtiamsa)**, 60 × 0°30′: count of 60 divisions always starts at the same sign (sequential, no odd/even or modality distinction). **Scope limitation, locked explicitly rather than guessed**: this standard defines the sign/degree placement only. The classical 60-named-deity assignment per division is not asserted here and is not implemented in Phase 5 — a documented limitation, not a silent omission.

All fourteen formulas above are locked as of this version. Each is a distinct, explicit, versioned configuration value under `calculation_config`'s varga-scheme setting (§Reproducibility) — an alternate scheme for any one of them must never silently replace the formula recorded here.

## Vimshottari Dasha

Defines the standard and contract that **Phase 7 (Dasha & Timing Engine)** implements. The open conventions left to Phase 7 are locked in §Phase 7 methodology lock below (v1.5.0).

- **Total cycle**: 120 years, distributed across nine planetary lords in a fixed sequence.
- **Nine planetary lords and fixed durations** (years): Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17 (sums to 120).
- **Sequence**: Ketu → Venus → Sun → Moon → Mars → Rahu → Jupiter → Saturn → Mercury → (cycles back to Ketu).
- **Starting Mahadasha lord**: the lord of the nakshatra occupied by the natal Moon at birth (see §Nakshatra standards for the nakshatra-lord sequence).
- **Balance of the first Mahadasha**: determined by how far the Moon has progressed through that nakshatra at the birth instant — the remaining fraction of the nakshatra's 13°20′ span, converted to time as that same fraction of the starting lord's full dasha-year duration.
- **Hierarchy**: Mahadasha → Antardasha → Pratyantar (Sookshma and Prana are out of scope; see §Phase 7 methodology lock) are nested applications of the same nine-lord sequence and proportional-duration logic, each level starting from its parent period's own lord and subdividing the parent's duration across the nine lords in the same fixed sequence and proportion.
- **Exact timestamps and boundary conditions**: all dasha transitions are computed as precise moments (date and time), not whole-day boundaries, derived from the birth instant plus cumulative duration — boundary dates must be computed to at least day-level precision, with the exact moment retained internally for reproducibility.
- **Reproducibility**: identical birth data and calculation configuration must reproduce an identical Mahadasha/Antardasha/Pratyantar timeline, byte-for-byte, every time.
- **Ownership of open Vimshottari conventions (v1.4.0 clarification)**: the balance of the first Mahadasha (BPHS Ch. 46 v. 16 measures the Moon's stay in the nakshatra by time; this standard uses the Moon's longitude fraction), the year length (no verse states it; the translator's worked examples imply 30-day months), leap-year handling and boundary rounding remain **Phase 7** decisions. Phase 6 must not calculate them; it only consumes Phase 7 dasha lords (§Phase 6 rule-engine methodology). **Resolved in v1.5.0**: see §Phase 7 methodology lock (explicit profiles; the balance method stays a documented source conflict).

### Phase 7 methodology lock (v1.5.0)

Locked per explicit project-owner direction for the Phase 7 implementation. It fixes explicit **profiles** where the sources are silent or in conflict. **None of these profiles is presented as the only valid classical method.** Source-supported statements, translator notes, inferences and Pandit Ji engineering conventions are labelled separately and never merged; every result records the profile IDs it used.

- **Scope**: Vimshottari Dasha to the Pratyantar level (Mahadasha, Antardasha, Pratyantar), with start and end instants, current, past and future lookup, and transitions. The engine produces **temporal facts and their provenance only**. It does not interpret: no life-domain reading (career, marriage, finance, education, health, relationships), no planetary-result or house-based prediction, and no Maraka interpretation. **Maraka timing is a later rule-engine consumer of these facts, not Phase 7 scope.** Out of scope: Ashtottari, Yogini, Chara, Narayana and every other Dasha system; Sookshma and Prana; birth-time rectification or any automatic time correction.
- **Sequence and years** (source-supported at translation level, no Sanskrit-level verification): Sun 6, Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17, Ketu 7, Venus 20 (120), counted from Krittika (BPHS Ch. 46 v. 12–15, Kapoor, image-checked; Phaladeepika Adhyaya XIX sl. 2, OCR-level). The sequence is the one already locked in §Nakshatra standards; the implementation derives it from the Nakshatra-lord table so there is a single source of truth.
- **Balance at birth**: this is a **documented source conflict** and this standard does not resolve it. BPHS Ch. 46 v. 16 (Kapoor, translation level) measures the Moon's stay in the nakshatra as Panchanga time (ghatis and palas); the translator's note says modern researchers use the Moon's longitude; Phaladeepika XIX sl. 3 (OCR-level) uses a divisor of 60 without settling whether the unit is time or arc; the Uttara Kalamrita worked example (translator, OCR-level) differs by seven days between the two methods. Profiles:
  - `DASHA_STANDARD_V1_BALANCE_LONGITUDE` — **the Pandit Ji product default**, an engineering convention, not a classical source statement. remaining_fraction = 1 − (fraction of the birth Nakshatra already traversed by the Moon's sidereal longitude), computed by exact rational arithmetic; balance = remaining_fraction × the starting lord's full Mahadasha. It uses the Nakshatra classification convention of §Nakshatra standards (v1.4.1).
  - `DASHA_BPHS_KAPOOR_46_16_BALANCE_TIME` — documented, **inactive**: it needs the Moon's Nakshatra entry and exit instants, which are not computed. It is not approximated.
  - `DASHA_PHALADEEPIKA_SASTRI_XIX_3_BALANCE` — documented, **inactive**: the time-versus-arc reading of the source is unresolved.
- **Year length**: no BPHS verse read states it. Phaladeepika XIX sl. 4 (OCR-level) calls the Sun's return one solar year, also the Ududasa year; applying that to Vimshottari is an **inference**. Profiles are fixed-duration years with **no calendar-year or leap-year arithmetic**:
  - `YEAR_365_2425_FIXED_DAY` — **the Pandit Ji product default** (365.2425 mean solar days), an engineering convention. It equals a whole number of seconds (31,556,952).
  - `YEAR_365_25_FIXED_DAY` and `YEAR_360_FIXED_DAY` (a translator worked-example convention: months counted as 30 days) — active, selectable, never silently substituted.
  - `YEAR_SIDEREAL_365_256363_FIXED_DAY` (translator note, taken from the project research record and not re-verified) and `YEAR_SUN_RETURN_PHALADEEPIKA_XIX_4` (variable per birth; an inference) — documented, **inactive**.
- **Sub-periods**: profile `DASHA_SUBPERIOD_PROPORTIONAL_FULL_PARENT_V1`. Child duration = full nominal parent duration × child lord's years ÷ 120, children in the canonical sequence starting from the parent's own lord (BPHS Ch. 51 v. 1–2 and Ch. 61 v. 1, OCR-level in the registry). **How the birth-balance Mahadasha is subdivided is not stated in the sources read.** The engineering convention is that the balance Mahadasha keeps the sub-periods of the **full, untruncated** Mahadasha: sub-periods that ended before birth are omitted and the one containing birth starts at birth, flagged `truncated_at_birth` (with its untruncated `nominal_start_utc` preserved). The alternative of scaling the sub-periods to the balance length was not implemented. This treatment is recorded for explicit owner confirmation.
- **Time**: UTC is canonical. All arithmetic is exact rational arithmetic in microseconds from the birth instant; each boundary is serialized once as `floor` to a whole microsecond (at most one microsecond of quantization, applied identically to every shared boundary, so periods tile with no gap and no overlap). Local civil time is never used for duration arithmetic and is kept only as recorded input, with the IANA timezone, DST flags and ambiguity policy. Julian Day UT of the birth instant is retained from the existing time resolution.
- **Boundary convention** (a Pandit Ji engineering convention; no classical source read states an inclusivity rule): all Nakshatra, Pada and Dasha intervals are half-open, [start, end). A shared boundary belongs to the **later** period; the overall timeline end is exclusive.
- **Birth-time precision**: `EXACT`, `APPROXIMATE` or `NOT_EVALUABLE`. An approximate time is never treated as exact. An approximate time needs an explicit symmetric uncertainty interval; without one the result is `NOT_EVALUABLE(uncertainty_interval_missing)`. If the interval reaches a Nakshatra boundary (a closed interval, so touching counts) the starting lord is ambiguous and the result is `NOT_EVALUABLE(starting_lord_ambiguous)` with no timeline. If the starting lord is stable the result is `APPROXIMATE`, with the Moon's longitude range, the balance-fraction range and the range of the first Mahadasha's end (evaluated at the two interval endpoints and the nominal instant, not a proven bound); a Pada boundary inside the interval is a warning only. No rectification and no inference of an exact time.
- **Statuses and reason codes**: `SUCCESS`, `APPROXIMATE`, `NOT_EVALUABLE`, `INVALID_INPUT`, `UNSUPPORTED_PROFILE`, `CONFIGURATION_ERROR`, `INTERNAL_ERROR`. Every non-success result carries a machine-readable reason code and no periods; nothing is guessed. Sookshma-depth requests are rejected as `unsupported_hierarchy_depth`.
- **Facts contract**: `astro-engine` calculates and owns `DashaFacts` (system, status, profile IDs, boundary convention, precision, starting Nakshatra/Pada/lord, elapsed and remaining fractions, remaining duration, the period tree with UTC boundaries, warnings and labelled provenance). The rule engine never calculates a Dasha; it records the facts in the evidence bundle as an additive optional `dasha` section. No shipped Phase 6 rule reads Dasha facts yet, so the reserved `requires_dasha` reason is not emitted by any current rule.
- **Standards versions**: Phase 7 results record `standards_version = 1.5.0`. The Phase 5 Kundli constant (`STANDARDS_VERSION` in `kundli.py`) is **not** advanced and stays `1.3.0`: it names the standards whose formulas the Kundli implements, and v1.4.1 corrected an implementation defect against the 1.3.0 text (the standard already said to divide by 13°20′). Phase 6 rule evaluation keeps recording its own ruleset standards version.

## Transit / Gochar standards (Phase 8 methodology lock, v1.6.0)

Defines the standard and contract that **Phase 8 (Transit / Gochar Engine)** implements. Locked per explicit project-owner approval of the Phase 8 methodology report (Approval Gate 1, all nine recommendations). It fixes explicit **profiles** where sources are silent or in conflict. **No profile is presented as the only valid classical method.** Source-supported statements, translator notes, inferences, derived calculations, modern traditions and Pandit Ji engineering conventions are labelled separately and never merged; every result records the profile IDs it used. Evidence labels used in results: `source_supported`, `translator_note`, `inference`, `engineering_convention`, `derived_calculation`, `unresolved_conflict`, `modern_tradition`, `engineering_evidence`.

All source statements below are at **translation level**. No Sanskrit-level verification exists for any of them. Verification levels are recorded per item in `research/ASTROLOGY_SOURCES.md` (Phase 8 group).

- **TR-01 Scope.** Deterministic transit **facts and provenance only**, like Phase 7. The engine reports where a planet is, what it is doing, what structural relations it has to the natal Moon (and optionally the Lagna), and when its sign, station or (opt-in) Nakshatra state changes. It does not interpret. Out of scope: effect or prediction text, good or bad verdicts, remedies, alerts and notifications, Ashtakavarga scoring, Sarvatobhadra Chakra, Latta, half-sign or decanate "effectiveness", degree-based or orb-based contacts, applying and separating aspects, Dhaiya, Ashtama Shani and degree-based Sade Sati variants (reserved profile IDs only), birth-time rectification, HTTP endpoints and database tables (Phase 18 owns them; `docs/ARCHITECTURE.md` §26).
- **TR-02 Reference point: `TRANSIT_REF_MOON_SIGN` (default).** Houses are counted whole-sign from the natal Moon's sidereal sign, the Moon's sign being house 1. Source-supported at translation level: Phaladeepika Adhyaya XXVI sl. 1 (page-image checked) states that the Moon's Lagna is the reference for transit effects; Brihat Samhita Adhyaya CIV sl. 4 (page-image checked) counts "from the Janma Rasi"; the Brihat Jataka Ch. IX translator's commentary says the same (translator note). No source read gives a Lagna-based Gochar table.
- **TR-03 Optional Lagna fact: `TRANSIT_REF_LAGNA_SIGN`.** A positional fact only (whole-sign house of the transiting planet counted from the natal Lagna sign), labelled `engineering_convention`, never classical. It needs an exact natal time: otherwise `NOT_EVALUABLE(lagna_unavailable)`. No favourable-set, Vedha or verdict is attached to it.
- **TR-04 Favourable-house sets and the Moon-from-Moon conflict.** "Favourable set" means membership in a source's list of houses from the natal Moon; it is a structural fact, not a verdict. Each source is a separate reading with its own ID, evaluated separately:
  - `GOCHARA_FAVOURABLE_PHALADEEPIKA_SASTRI_XXVI_2` (source-supported; page-image checked): Sun 3, 6, 10; Moon 1, 3, 6, 7, 10; Mars and Saturn 3, 6; Mercury 2, 4, 6, 8, 10; Jupiter 2, 5, 7, 9; Venus every house except 6, 7, 10; and, for all planets, the 11th; Rahu and Ketu "similar to the Sun".
  - `GOCHARA_FAVOURABLE_BRIHAT_SAMHITA_SASTRI_CIV_4` (source-supported; page-image checked): the same sets as Phaladeepika for the seven planets; it does not mention the nodes.
  - `GOCHARA_FAVOURABLE_BRIHAT_JATAKA_SASTRI_IX_1_7` (source-supported; page-image checked): the benefic places from the Moon in each planet's Ashtakavarga: Sun 3, 6, 10, 11; Mars 3, 6, 11; Mercury 2, 4, 6, 8, 10, 11; Jupiter 2, 5, 7, 9, 11; Venus 1, 2, 3, 4, 5, 8, 9, 11, 12; Saturn 3, 6, 11; **Moon 1, 3, 5, 7, 10, 11**.
  - `GOCHARA_FAVOURABLE_BPHS_KAPOOR_66_DERIVED` (`derived_calculation`, not a source statement): the complement of the dot houses that the Moon contributes in each planet's Ashtakavarga chart (BPHS Ch. 66 v. 16–42, OCR-level lists; only p. 847, the Moon's chart, was page-image checked). It agrees with the others for the six non-Moon planets and gives **Moon 1, 3, 6, 7, 9, 10, 11**.
  - **Unresolved source conflict (Moon from the Moon):** the readings differ on houses 5 (Brihat Jataka only), 6 (all but Brihat Jataka) and 9 (BPHS-derived only). Houses 1, 3, 7, 10, 11 are in every Moon reading and houses 2, 4, 8, 12 are in none. For the Moon in house 5, 6 or 9 the consolidated result is `NOT_EVALUABLE(reading_ambiguous)` with every reading's outcome retained. No reading is chosen. Whether this is a textual variant or a translation matter cannot be settled without qualified Sanskrit review.
  - For the six non-Moon planets all four readings agree; the consolidated result carries every attesting reading ID.
- **TR-05 Rahu and Ketu.** Positional facts are calculated normally (Mean Node default, True Node an explicit alternate through the Phase 4 configuration; Ketu = Rahu + 180°; retrograde by speed sign, so Mean Node is always retrograde and has no stations). The only favourable-set statement found is Phaladeepika sl. 2 ("similar to the Sun"), single-source; a Jataka Parijata commentary quote of another work may say the opposite (unreviewed OCR of a Sanskrit line, not relied on). Therefore the nodes are evaluated only under the single-source profile `GOCHARA_FAVOURABLE_PHALADEEPIKA_SASTRI_XXVI_2`, flagged `single_source`; the consolidated result for a node is `NOT_EVALUABLE(node_reading_single_source)`. Node Vedha as the *subject* is `NOT_EVALUABLE(not_specified_by_source)` because sl. 2 says "similar to the Sun" only about the favourable houses.
- **TR-06 Vedha: `GOCHARA_VEDHA_PHALADEEPIKA_SASTRI_XXVI_3_8`.** Source-supported at verse level in Phaladeepika only (sl. 3–8, page-image checked). Further mentions (Phaladeepika's own footnotes citing Narada and Jataka Parijata, the Jataka Parijata commentary quoting another work, the Brihat Samhita translator's footnote) are cross-references (translator notes, unreviewed), not independent corroboration of the numbers. Table, favourable house to Vedha house: Sun 11→5, 3→9, 10→4, 6→12; Moon 7→2, 1→5, 6→12, 11→8, 10→4, 3→9; Mars and Saturn 3→12, 11→5, 6→9; Mercury 2→5, 4→3, 6→9, 8→1, 10→8, 11→12; Jupiter 2→12, 11→8, 9→10, 5→4, 7→3; Venus 1→8, 2→7, 3→1, 4→10, 5→9, 8→5, 9→11, 12→6, 11→3. Exceptions stated in the verses: Saturn does not obstruct the Sun and the Sun does not obstruct Saturn; the Moon and Mercury do not obstruct each other.
  - **Structural definition.** For a subject planet in a house that has a Vedha pair, the fact records the Vedha house (counted from the natal Moon) and which *transiting* planets occupy that house's sign, excluding the subject and the exempt planet. Natal planets are not occupants (the verses speak of transit). The fact is `vedha_present` true or false; it carries no verdict.
  - **Nodes as occupants.** The verses say "planets" without naming the nodes. If a node occupies the Vedha sign and would change the result (no other occupant is present), the fact is `NOT_EVALUABLE(node_participation_unspecified)`, following the Phase 6 policy (§Node policy). If another occupant already makes the fact true, it is true.
  - **Translation anomaly, preserved.** Sl. 8 (Venus) says Venus "will give bad effects" in the listed houses if marred, whereas the parallel slokas 3–7 speak of good effects when the Vedha place is free. It is unresolved whether this is a translator's slip or a real difference; a warning `translation_wording_anomaly_venus_sl8` is attached to every Venus Vedha fact, and the table is used unchanged.
  - Vedha is a Phaladeepika-specific profile. It is never combined with the Ashtakavarga method.
- **TR-07 Transit-to-natal contacts: `TRANSIT_CONTACT_SIGN_BASED_V1` (`engineering_convention`).** Only sign-based facts: same-sign conjunction of a transiting planet with a natal planet, and the Phase 5 whole-sign graha drishti (§Planetary aspects standard, unchanged) from the transiting planet's sign to the sign of a natal planet. Degree, orb, applying and separating aspects are not produced; `docs/ARCHITECTURE.md` §31's older phrase "transit-to-natal angles" is realised only as these sign-based contacts. Contacts need an exact natal time (`NOT_EVALUABLE` otherwise). A contact changes only at a transiting planet's sign ingress, so window results attach the contacts holding from each ingress instant.
- **TR-08 Events: `TRANSIT_EVENTS_ENGINEERING_V1` (`engineering_convention`).** No source read defines transit "events". Kinds: `SIGN_INGRESS` (including backward re-entry), `STATION_RETROGRADE`, `STATION_DIRECT`, and, opt-in only, `NAKSHATRA_INGRESS`. A station is the instant the sign of the longitude speed changes, retrograde being speed < 0 (the Phase 4 definition). Instants are found by bracketed bisection; every ingress or station instant is a numerical solution and never "exact" (TR-10).
- **TR-09 Sade Sati: `SADE_SATI_SIGN_BASED_MODERN_V1` (`modern_tradition`).** The combined unit was **not found** in the classical texts read (BPHS, Brihat Jataka, Brihat Samhita, Phaladeepika, Jataka Parijata; a keyword probe of unreliable OCR, so `NOT_VERIFIED_BY_OCR`, not proof of absence). Phaladeepika sl. 22 and Brihat Samhita CIV sl. 39–45 give Saturn's per-house effects individually, and describe every house except the 3rd, 6th and 11th from the Moon as unfavourable; a 12th–1st–2nd window is a subset of these, not a stated unit. The profile is a transparent sign-based construct and no classical certainty is implied:
  - Band: Saturn's sidereal sign is the natal Moon sign −1, 0 or +1 (phase 1 = 12th, phase 2 = 1st, phase 3 = 2nd from the Moon).
  - **Segments**: maximal intervals of Saturn in one band sign. They are never merged across a gap.
  - **Episodes**: maximal runs of contiguous segments. An exit and re-entry produces a separate episode, flagged `retrograde_reentry_of_previous_episode` when retrograde motion bounds the gap at either end: the previous episode ended by backward motion, or this episode was entered by backward motion (each segment and episode records `entered_by_backward_motion` and `ended_by_backward_motion`; backward means speed < 0 at the ingress). No "7½ years" duration is asserted; durations are derived only.
  - A segment or episode that starts before, or ends after, the requested window is clipped and flagged; its unknown boundary is `null`.
  - Approximate natal time whose Moon range reaches a sign boundary gives `NOT_EVALUABLE(natal_moon_sign_ambiguous)`.
  - Reserved and **not implemented** (`UNSUPPORTED_PROFILE`): `DHAIYA_SIGN_BASED_MODERN_V1`, `ASHTAMA_SIGN_BASED_MODERN_V1`, `SADE_SATI_DEGREE_45_MODERN_V1`. No Ashtakavarga is mixed in.
- **TR-10 Time, precision and boundaries.**
  - UTC is canonical; local time is display metadata. Positions are calculated at the Julian Day UT of the UTC instant, exactly as Phase 4 does (the sub-second UT1−UTC difference is ignored and documented).
  - **Boundary convention** `half_open_start_inclusive_end_exclusive` (`engineering_convention`, as in Phase 7): a sign or Nakshatra interval is [start, end); the later interval owns a shared boundary; a window is [start, end). Sign classification uses the existing exact convention (`rashi.sign_index_from_longitude`, Nakshatra by `nakshatra_position`).
  - **Solving.** Ingress and station instants use bisection on a bracket that contains exactly one change, to a fixed search tolerance of 1e-8 day (about 0.86 ms). Scan steps (days): Moon 0.25, Mercury 0.5, Venus 1, Sun 2, Mars 2, Jupiter 5, Saturn 5, Rahu and Ketu 5. A step in which the speed changes sign is split at the station, so that two sign crossings around a station inside one step are not missed. The scan grid is anchored to absolute multiples of the step (not to the window), so an event's instant does not depend on the window that contains it; a window scan starts one step before its start (so an ingress exactly at the start is found) and events are reported for the half-open window [start, end). Station instants are limited by the numerical noise of the ephemeris speed near zero (milliseconds), not by the bisection tolerance. An ingress that falls at the window start within the solver tolerance is already reflected in the state at the start, and does not replay as a spurious Sade Sati segment of the previous sign.
  - **Accuracy statement (`engineering_evidence`, not a validation).** Numerical resolution is not accuracy. Every result records the ephemeris mode, the ayanamsa and the solver tolerance, and states that instants are not exact. An independent comparison of the Swiss Ephemeris **tropical** longitude of date (Moshier mode, through the Phase 4 adapter) with JPL Horizons (geocentric apparent ecliptic longitude of date) on 42 samples (7 bodies, 6 dates, 1950–2060; fixture `services/astro-engine/tests/fixtures/horizons_transit_reference.json`, retrieved 2026-09-21) found maximum differences of 0.26″ (Sun), 0.19″ (Mars), 0.15″ (Mercury, Venus), 0.38″ (Jupiter), 0.27″ (Saturn) and 4.78″ (Moon), which correspond to seconds of time at a sign boundary, and to minutes for a slow planet near a station. This checks planetary longitude only, at these samples; it does not validate the Lahiri ayanamsa value or the sidereal frame.
  - **Ayanamsa sensitivity.** A sidereal ingress instant depends on the ayanamsa value. In the same 42 samples the ayanamsa implied by the sidereal calculation (tropical minus sidereal longitude) differed from the value returned by the ephemeris adapter's `get_ayanamsa_degrees` by −15.6″ to +15.7″, the size of nutation in longitude and about 1.5 hours of Saturn's motion; the cause was not investigated (a Swiss Ephemeris frame convention, not shown to be a defect). Published ingress times for the same event differ by hours across Tier 5 pages (Saturn into Pisces, 29 March 2025: two pages give 01:07 and 02:31 IST, the engine gives 21:44:41 IST; a 20-hour difference is about 3.3′ for a planet moving 0.066° per day). Only the date agrees, so published times are never used as golden references; results always record `ayanamsa`.
  - **Approximate natal time.** The Moon-based facts need the natal Moon's sign to be unambiguous: with an approximate natal time an explicit Moon longitude range is required (`NOT_EVALUABLE(natal_range_missing)` otherwise) and a range that reaches a sign boundary gives `NOT_EVALUABLE(natal_moon_sign_ambiguous)`. Positions and events do not depend on the natal chart and are still produced.
- **TR-11 Limits.** A request window may not exceed 200 years (200 × 365.2425 days): `NOT_EVALUABLE(window_too_large)`. A window may not produce more than 50,000 events: `NOT_EVALUABLE(event_limit_exceeded)` with no partial event list.
- **TR-12 Statuses and reason codes.** Statuses: `SUCCESS`, `NOT_EVALUABLE`, `INVALID_INPUT`, `UNSUPPORTED_PROFILE`, `CONFIGURATION_ERROR`, `INTERNAL_ERROR`. Reason codes include `moon_longitude_missing`, `natal_moon_sign_ambiguous`, `natal_range_missing`, `natal_range_inconsistent`, `natal_time_unknown`, `natal_planets_unavailable`, `non_finite_longitude`, `no_query`, `no_bodies`, `lagna_unavailable`, `reading_ambiguous`, `node_participation_unspecified`, `node_reading_single_source`, `not_specified_by_source`, `window_too_large`, `event_limit_exceeded`, `invalid_window`, `invalid_instant`, `ephemeris_unavailable`, `ephemeris_error`, `unsupported_profile`, `sidereal_zodiac_required`. Every non-success result carries a reason code and no facts; nothing is guessed.
- **TR-13 Facts contract.** `astro-engine` calculates and owns `TransitFacts` (system, status, profile IDs, boundary convention, configuration, natal summary, accuracy block, an optional instant snapshot, an optional window with events, an optional Sade Sati section, warnings and labelled provenance). The rule engine never calculates a transit: it records the JSON form in the evidence bundle as an additive optional `transit` section (the bundle serializes and hashes exactly as before when it is absent). No shipped rule reads transit facts. Cache keys (a documented design, not implemented until Phase 18): `(natal_reference_hash, instant or window, profile_ids, configuration_hash, engine_version)`.
- **TR-14 Ownership.** Ashtakavarga scoring and transit scoring by bindus are Phase 9 (BPHS Ch. 72 v. 30–31, page-image checked, treats Ashtakavarga as paramount over a transit check, so the two systems must not be merged). Interpretation of any transit fact is Phase 12, 15 and 17.
- **TR-15 Versions.** Phase 8 results record `standards_version = 1.6.0`. The Phase 5 Kundli constant stays `1.3.0`; Phase 7 results keep `1.5.0`.

## Nakshatra standards

Defines the standard and contract that **Phase 5** (as part of the Kundli engine) implements — not implemented in Phase 1.

- **27 Nakshatras** spanning the full 360° sidereal zodiac.
- **Zodiacal span**: 13°20′ (360° ÷ 27) per Nakshatra.
- **Padas**: four padas per Nakshatra, each 3°20′ (13°20′ ÷ 4).
- **Planetary lord sequence**: the same nine Vimshottari lords (Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury), repeating three times across the 27 Nakshatras (9 × 3 = 27).
- **Boundary handling**: Nakshatra and pada boundaries are computed from the Moon's (or other relevant planet's) exact sidereal longitude after ayanamsa correction, at full internal precision (degrees/minutes/seconds). A position falling essentially exactly on a boundary must be flagged for review rather than silently rounded to one side.
- **Boundary classification convention (v1.4.1; a Pandit Ji engineering convention, not a rule stated by any classical source)**: the classical texts read so far list shared endpoints (for example 13°20′ closes Ashwini and opens Bharani) and state no inclusivity rule, so this standard fixes one. Classification uses half-open intervals, lower bound inclusive and upper bound exclusive, for both Nakshatras and Padas: a longitude exactly on a boundary belongs to the upper Nakshatra or Pada, and 360° is 0° (Ashwini, Pada 1).
  - **Normalization**: the input longitude is first normalized with the existing floating-point modulo 360. No new normalization rule is introduced.
  - **Exact classification**: the normalized float is then classified by exact rational arithmetic on its exact value: Nakshatra index = ⌊n × 27 ÷ 360⌋ and Pada slot = ⌊n × 108 ÷ 360⌋ (Pada = slot mod 4 + 1), taken modulo 360 so that a normalized 360.0 maps to 0. There is no intermediate rounding and no tolerance. A float divisor such as 360.0/27.0 must not be used, because it is not exactly 13°20′ and can place an exactly representable boundary in the lower bucket (for example 40.0° must be Rohini, Pada 1, and 10.0° must be Ashwini, Pada 4).
  - **Display rounding** never decides classification.
  - **`near_boundary` flag**: unchanged. It remains an informational numeric flag (an epsilon of 1e-6°) raised for review near a Nakshatra or Pada boundary; it does not affect which Nakshatra or Pada is assigned.
  - **Known unchanged behaviour (not approved for change)**: because normalization uses the floating-point modulo, a negative longitude smaller in magnitude than about 2.8e-14° normalizes to 360.0 and therefore classifies as 0° (Ashwini), not Revati. Ephemeris longitudes are already in [0, 360), so this input does not occur in the pipeline.
  - **Scope**: this convention only fixes the side of a boundary. It does not select the Vimshottari balance-at-birth method, the year length, leap-year handling or rounding, which remain open Phase 7 decisions (§Vimshottari Dasha).
- **Moon's sidereal longitude → Janma Nakshatra**: the birth (Janma) Nakshatra and pada are derived by dividing the Moon's sidereal longitude at birth by 13°20′ (Nakshatra) and further by 3°20′ (pada), with the remainder giving both the pada and the dasha-balance fraction used in §Vimshottari Dasha.
- **Precision/reproducibility**: same precision and reproducibility requirements as the rest of the Default Vedic profile.

## Yoga / Dosha standards

Defines the standard for representing and evaluating Yogas and Doshas — the schema the rule engine implements in **Phase 6 (Vedic Astrology Rule Engine)**, not the rule content itself and not implemented in Phase 1.

Every Yoga/Dosha rule must be represented with:
- Rule-based detection logic (a pattern over chart facts, evaluated deterministically — never left to AI judgment)
- Required chart conditions (the facts that must hold for the rule to trigger)
- Supporting conditions (factors that strengthen the interpretation without being individually required)
- Cancellation/mitigation conditions where the tradition defines them (a rule may be triggered but reported as fully or partially cancelled per classical exception rules)
- Strength/severity/context (how strongly the rule applies given the specific chart, not a flat yes/no)
- Source/tradition (which text/school the rule comes from — see `research/ASTROLOGY_SOURCES.md`)
- Exceptions (documented exception conditions from the source tradition)
- Interpretation (the traditional meaning associated with the triggered rule — narrative phrasing is the AI's job at response time, not stored as free text in the rule itself)
- Timing relevance (which dasha/transit periods, if any, the rule's effects are most associated with)
- Conflicting rules (an explicit list of other rule IDs this rule is known to contradict, so the evidence-bundle contradiction analysis in `docs/ARCHITECTURE.md` §7 can surface both sides)

**Do NOT invent a universal list of Yogas/Doshas where traditions disagree.** Where Parashari, Jaimini, Lal Kitab, KP, or other schools define a given Yoga/Dosha differently, each school's version is recorded as its own tagged rule under its own source/tradition, and the evidence bundle presents both rather than the system silently picking a winner.

## Phase 6 rule-engine methodology

Defines the standard and contract that **Phase 6 (Vedic Astrology Rule Engine)** implements. Added in v1.4.0 from the Phase 6 methodology research (`research/ASTROLOGY_SOURCES.md`, Groups 1–8), per explicit project-owner approval. Rules evaluate facts from Phases 4–5 (and later phases where declared); the rule engine never calculates astronomy, dashas, transits or Panchang, and the AI layer never calculates astrology.

### Source tiers

- **Tier 1**: primary classical Sanskrit text or critical edition, reviewed by a qualified reader. No source has yet been reviewed at this level; no rule may be labelled `SANSKRIT-LEVEL VERIFIED` until one is.
- **Tier 2**: recognised scholarly or classical translation (for example the Santhanam and Kapoor translations of Brihat Parashara Hora Shastra, Sastri's Phaladeepika). Can establish a canonical rule, labelled `TRANSLATION-LEVEL VERIFIED`.
- **Tier 3**: traditional secondary source or translator's commentary. Supplies variants and supporting evidence; a translator's note is never treated as a verse and cannot by itself establish a canonical rule.
- **Tier 4**: modern practitioner source. May justify a separately tagged `MODERN_TRADITION` profile, never a canonical or classical rule.
- **Tier 5**: general internet content. Never evidence for a rule.

### Source profiles and rule identifiers

- Rules are **source-specific profiles**. Where traditions differ materially, each is a separate rule with its own profile ID; there is no generic `GAJAKESARI`, `KEMADRUMA` or `MANGAL_DOSHA` rule.
- Profile IDs are upper-case and underscore-separated: work code, translator or edition code where it matters, family, then chapter and verse (for example `BPHS_SAN_GAJAKESARI_36_3_4`, `BPHS_KAPOOR_80_47_49_MARS_HOUSES`, `JP_KUJA_DOSHA`, `MODERN_KAAL_SARP_<SOURCE>`). The registry of finalized profile IDs is in `research/ASTROLOGY_SOURCES.md` §6.
- Every profile records: source, edition, translator, source location, source version, astrology system, school, profile ID, conditions, readings, exceptions, cancellations, dependencies, interpretation tags, priority, and ambiguity/conflict metadata.
- **Priority is metadata only.** It may order display or evaluation where explicitly justified. It never removes conflicting evidence and never means "objectively true".
- Interpretation is a structured tag (domain, signification, effect class), never prose. Traditional wording belongs to the knowledge base (`Phases.md` Phase 12).

### Ambiguity-preserving evaluation

- A rule may carry several **readings**, each with a reading ID and its source. Each reading is evaluated separately.
- If all readings give the same result, that result is returned with every reading ID and source ID retained. If they differ, the result is `NOT_EVALUABLE(reading_ambiguous)` with every reading's outcome retained. A reading is never silently chosen.
- Source conflicts between profiles are provenance and profile metadata, grouped by a conflict group; they are not runtime truth statuses unless they make one rule's own reading ambiguous.

### Result statuses and reason codes

- Statuses: `TRIGGERED`, `NOT_TRIGGERED`, `CANCELLED`, `PARTIALLY_CANCELLED`, `NOT_EVALUABLE(reason)`. `PARTIALLY_CANCELLED` is used only where the source states a partial cancellation.
- Reason codes: `reading_ambiguous`, `missing_dependency:<id>`, `requires_shadbala`, `requires_dasha`, `requires_partial_drishti`, `requires_gender`, `requires_partner_chart`, `requires_moolatrikona`, `node_participation_unspecified`, `varga_scheme_conflict`, `time_base_unspecified`, `source_profile_not_selected`, `scope`, `not_specified_by_source`, `condition_absent_in_source`.
- A source silent on a point gives `not_specified_by_source`. A dependency owned by a later phase gives `missing_dependency:<id>`. A rule is never evaluated to `NOT_TRIGGERED` because an input was unavailable.

### Aspect refinement

- Phase 6 uses only the Phase 5 full-sign graha drishti (§Planetary aspects standard). It never substitutes full-sign aspect for a rule that needs partial, degree-based or Jaimini sign aspect.
- For a condition phrased as "aspected by X": if a full-sign aspect is present the condition is definitely true. For "unaspected": if no full-sign aspect is present, a partial aspect (BPHS Ch. 26 v. 2–5) may still exist, so the result is `NOT_EVALUABLE(requires_partial_drishti)` until Phase 9 provides partial aspects. BPHS Ch. 26 v. 2–5 gives partial aspects only on the 3rd/10th, 5th/9th and 4th/8th from the aspecting planet (the 7th is always full), so from any other house no aspect exists and "unaspected" is definitely true there; `requires_partial_drishti` applies only from those six houses (implementation clarification recorded during Phase 6 implementation).
- Jaimini rashi drishti and degree-based drishti are separate systems and are never blended with graha drishti.

### Strength

- "Strong", "stronger" and "weak" have no technical definition in the reviewed BPHS chapters. Rules that use them return `NOT_EVALUABLE(requires_shadbala)` until Shadbala (`Phases.md` Phase 9) exists. Rules that state an explicit dignity or house condition are evaluated normally. No composite strength score is defined.

### Natural relationships, natural nature and functional nature

- **Natural relationships** (Brihat Parashara Hora Shastra Ch. 3 v. 55, Santhanam translation, table checked against the page image). Friend / enemy / equal:

| Planet | Friends | Enemies | Equals |
|---|---|---|---|
| Sun | Moon, Mars, Jupiter | Venus, Saturn | Mercury |
| Moon | Sun, Mercury | none | Mars, Jupiter, Venus, Saturn |
| Mars | Sun, Moon, Jupiter | Mercury | Venus, Saturn |
| Mercury | Sun, Venus | Moon | Mars, Jupiter, Saturn |
| Jupiter | Sun, Moon, Mars | Mercury, Venus | Saturn |
| Venus | Mercury, Saturn | Sun, Moon | Mars, Jupiter |
| Saturn | Mercury, Venus | Sun, Moon, Mars | Jupiter |

  The Moon row follows the statement the translator quotes from the Benares (Chaukhamba) edition that the Moon has no enemy; the v. 55 counting formula alone would give a different Moon row. This is recorded as a bounded source conflict in `research/ASTROLOGY_SOURCES.md`.
- **Temporal relationship** (v. 56): a planet in the 2nd, 3rd, 4th, 10th, 11th or 12th sign from another is its temporal friend; otherwise its temporal enemy.
- **Compound relationship** (v. 57–58): natural plus temporal: friend + friend gives great friend; friend + enemy gives neutral; friend + equal gives friend; enemy + equal gives enemy; enemy + enemy gives great enemy; equal + equal gives neutral. The output field is `relationship_kind`.
- **Rahu and Ketu are excluded** from the relationship tables; the only node relationships found are in an unsourced translator's note (Tier 3), which is not used.
- **Natural benefic/malefic** (v. 11): Sun, Saturn, Mars, the waning Moon, Rahu and Ketu are malefic; the other planets are benefic; Mercury is malefic when joined with a malefic. Two Pandit Ji conventions, labelled as such and not classical: the Moon is waxing when its elongation from the Sun is 0°–180° and waning otherwise, with a near-boundary flag; Mercury's "joined with" means same-sign conjunction only. Mercury's values are benefic, malefic, `mixed` or `none`.
- **Functional nature**: the canonical BPHS functional-nature source is the 84-cell per-Lagna table of Ch. 34 v. 19–44 (12 Lagnas × 7 planets, checked cell by cell against the page images). Source labels are stored exactly as the source gives them (for example auspicious, malefic, killer, yogakaraka, neutral, association-dependent, and their combinations) and are never converted into a good/bad score. Cells the verse does not address are `not_specified_by_source`. No replacement universal algorithm is derived. The general rules of Ch. 34 v. 2–17 remain separate structural rules, not a functional-nature algorithm.

### Node policy (Rahu and Ketu)

- Natural nature: as in Ch. 3 v. 11 (malefic). Functional nature: no node cell exists in the Ch. 34 table and none is invented; Ch. 34 v. 16–17 (nodes act by association and house; a node in an angle with a trinal lord, or in a trine with an angular lord, is a yogakaraka) is a separate rule.
- No universal Parashari lordship, relationship table, dignity system, sign-lord inheritance, dispositor inheritance or conjunction inheritance is defined for nodes. Combustion follows §Combustion standard.
- A node participates in a rule only where the source supports it. If node participation would change the result and the source is silent: `NOT_EVALUABLE(node_participation_unspecified)`. Source-specific node traditions may be added later as separate profiles.

### Moolatrikona (Phase 6 fact)

- Moolatrikona is a Phase 6 data-driven fact, separate from the Phase 5 dignity model, which is unchanged. It is derived from sign and degree (Brihat Parashara Hora Shastra Ch. 3 v. 51–54): Sun Leo 0°–20°; Moon Taurus 3°–30°; Mars Aries 0°–12°; Mercury Virgo 15°–20°; Jupiter Sagittarius 0°–10°; Venus Libra 0°–15°; Saturn Aquarius 0°–20°. A rule that needs it while the fact is unavailable returns `NOT_EVALUABLE(requires_moolatrikona)`.

### Vargas and D27

- **D27 (Nakshatramsa / Bhamsa) is `UNRESOLVED`.** The §Divisional charts formula (Aries, Cancer, Libra by modality) is unchanged. BPHS Ch. 6 v. 24–26 says the count begins "from Aries and the movable signs"; the verse names no element or modality, so both the modality rule and the translator's element table are interpretations. The grammar needs qualified Sanskrit review. Any Phase 6 rule that uses D27 returns `NOT_EVALUABLE(varga_scheme_conflict)`.

### Dependencies owned by other phases

- Dasha (Phase 7), transits (Phase 8), Shadbala, partial and degree drishti, Jaimini and longevity methods (Phase 9), and Panchang, sunrise-based special points and Tara Balam (Phase 10) are not calculated by Phase 6. A rule that needs one returns `NOT_EVALUABLE(missing_dependency:<id>)` or the specific reason code above.

### Evidence bundle and reproducibility

- The evidence bundle preserves: the chart and calculation snapshot; the calculation configuration (ayanamsa, node model, house system, timezone, coordinates); the calculation-engine, standards, rule-engine and ruleset versions; the ruleset content hash; rule IDs, source profiles and reading IDs; triggered, non-triggered and `NOT_EVALUABLE` results; conflicts, unresolved dependencies and provenance. The same input, configuration, ruleset hash and engine version must produce the same bundle.
- **Standards version per phase**: each result records the standards version under which it was produced and is never re-labelled when the document advances. A Phase 5 calculation snapshot keeps `standards_version = 1.3.0` (its formulas are unchanged in v1.4.0); Phase 6 rule evaluation records `standards_version = 1.4.0`. The evidence bundle therefore carries both the calculation snapshot's standards version and the rule evaluation's.

## Panchang / Muhurta standards

Defines the standard and contract that **Phase 10 (Panchang, Muhurta & Calendar Engine)** implements — not implemented in Phase 1.

### Panchang
- **Tithi**: the angular distance between Moon and Sun's sidereal longitudes, divided by 12° (30 tithis per synodic lunar month).
- **Vara**: the weekday, reckoned sunrise-to-sunrise per traditional Vedic civil-day convention, not midnight-to-midnight.
- **Nakshatra**: as defined in §Nakshatra standards, computed for the Panchang date rather than a birth date.
- **Yoga** (Panchang Yoga, distinct from natal Yogas above): the sum of the Sun's and Moon's sidereal longitudes, divided by 13°20′ (27 Yogas).
- **Karana**: half of a Tithi; 11 Karanas cycling across a lunar month (7 repeating + 4 fixed, per classical convention).
- **Sunrise/sunset dependency**: Panchang element transitions (especially Tithi and the civil day itself) are reckoned from location-specific sunrise, not a fixed clock time — the engine must compute actual sunrise/sunset for the query location and date, not assume a constant.
- **Local location/timezone handling**: Panchang is inherently location-dependent (two locations can be in different Tithis at the same clock instant); the query location's coordinates and timezone must always be explicit inputs.
- **Regional/calendar configuration**: some regional calendar conventions (e.g., Tamil, Bengali) differ from the standard pan-Indian convention; the regional convention in use must be an explicit, recorded configuration value, defaulting to the standard (Drik-Ganita-based) pan-Indian convention.
- **Reproducibility**: identical date, location, and configuration must reproduce identical Panchang values.

### Muhurta
- **Purpose-specific timing**: different purposes (marriage/Vivah, Griha Pravesh, Mundan, and other Shubh Muhurat categories) have distinct classical rule sets; every Muhurta result must be tagged with the purpose it was computed for.
- **Location dependence**: inherits Panchang's location dependency in full.
- **Panchang dependencies**: Muhurta selection is built on top of the Panchang elements above, plus additional derived factors (Rahu Kaal, Choghadiya, Panchak, Bhadra, Tara Balam, Chandra Balam).
- **Configurable traditional rules**: different traditions/regions apply different Muhurta rule sets; the rule set in use must be versioned and tagged by source, following the same rule-representation schema as §Yoga/Dosha standards.
- **Auspicious/inauspicious criteria**: represented using the same evidence/rule structure as Yogas/Doshas (required conditions, supporting/conflicting factors, source/tradition), not as an unstructured label.
- **Source/tradition identification**: every Muhurta rule cites its source text.
- **Boundary handling**: Muhurta windows have precise start/end timestamps derived from the underlying Panchang element transitions — boundaries are exact moments, not whole days.

## Numerology standards

Defines the standard and contract that **Phase 11 (Numerology + Compatibility)** implements — not implemented in Phase 1.

- **Supported system(s)**: the Vedic/Chaldean-influenced Indian numerology framework (Moolank + Bhagyank) is the default; Western Pythagorean numerology is supported as an explicit, separately-configured alternate system. **The two systems must never be silently combined** — a result must be tagged with exactly one system.
- **Name-number methodology**: letter-to-number mapping depends on the configured system — Chaldean-style mapping uses sound-based values 1-8 (no letter maps to 9); Pythagorean mapping uses sequential values 1-9 by letter order. The mapping table in use must be an explicit, recorded configuration value.
- **Date-of-birth methodology / Moolank (Root/Driving Number)**: the digital root of the birth day-of-month only.
- **Bhagyank (Destiny/Life Path Number)**: the digital root of the complete birth date, summing all digits of DD, MM, and YYYY together before reduction.
- **Master-number handling**: numbers 11, 22 (and, in some traditions, 33) are traditionally not reduced further; whether master-number retention is enabled is an explicit configuration value, since this varies by tradition and must not be silently assumed either way.
- **Compound-number handling**: the intermediate two-digit sum reached before final single-digit reduction may carry its own interpretive meaning in some traditions (compound-number tables); both the intermediate compound number and the final reduced digit must be retained and exposed, not just the final digit.
- **Spelling/name-change handling**: name numerology depends on the exact spelling used at calculation time; the exact name string used must be recorded as an explicit input, and a different spelling must trigger a fresh calculation rather than silently reusing a stale result.
- **Reduction rules**: standard digital-root reduction (repeatedly sum digits until a single digit remains), except for retained master numbers per the configuration above.
- **Source/tradition**: every numerology result is tagged with which system (Vedic/Chaldean vs. Pythagorean) produced it.
- **Versioning**: numerology configuration follows the same reproducibility/versioning requirement as astrology calculation configuration (see §Reproducibility).

## Combustion standard

Defines the standard and contract that **Phase 4 (Astronomical Calculation Engine)** implements. Locked per explicit project-owner decision (see §Versioning change log).

Combustion (Asta) is a derived astrological status, not raw ephemeris output: a planet is combust when its angular separation from the Sun (computed from each body's precise geocentric ecliptic longitude) is within that planet's specific orb threshold. Per-planet thresholds (degrees of separation from the Sun), per the Brihat Parashara Hora Shastra tradition as commonly implemented in mainstream Vedic astrology software:

| Planet | Threshold (direct) | Threshold (retrograde) |
|---|---|---|
| Moon | 12° | — |
| Mars | 17° | — |
| Mercury | 14° | 12° |
| Jupiter | 11° | — |
| Venus | 10° | 8° |
| Saturn | 15° | — |

The Sun itself is never combust. Rahu/Ketu are not evaluated for combustion under this standard (they are not physical bodies with a solar-separation relationship in the same sense).

Requirements:
- Combustion is computed as a **derived layer over raw longitudes**, not embedded inside ephemeris retrieval — see `docs/ARCHITECTURE.md` §"Astrology Engine Architecture" and the Phase 4 ephemeris-adapter/derived-status separation.
- The angular separation used is the absolute difference between the planet's and Sun's geocentric ecliptic longitude, normalized to the [0°, 180°] range (shortest angular distance).
- The retrograde-specific threshold (Mercury, Venus) applies only when that planet's own retrograde status (per its documented speed-sign semantics) is true at the same instant.
- The exact separation value and the threshold applied must be preserved alongside the boolean combust/not-combust result, for reproducibility and later rule-engine use.
- This threshold table is itself a versioned configuration value (§Reproducibility) — a future alternate combustion standard (e.g., a different classical source) must be a distinct, explicit configuration, never silently substituted.

## Node convention (Rahu / Ketu)

Defines the standard and contract that **Phase 4 (Astronomical Calculation Engine)** implements. Locked per explicit project-owner decision (see §Versioning change log).

Both **Mean Node** and **True Node** conventions are supported as an explicit, distinct `calculation_config` value — never silently mixed or substituted for each other. **Mean Node is the default** for the Vedic profile (§Default Vedic profile), matching the traditional convention used in most classical Parashari/Panchang software. True Node remains available as an explicit alternate configuration (anticipating KP's typical preference, `Phases.md` Phase 9).

- **Mean Node**: the smoothly regressing average node position (Swiss Ephemeris `SE_MEAN_NODE`).
- **True Node**: the actual perturbed node position, which can briefly station/go direct (Swiss Ephemeris `SE_TRUE_NODE`).
- **Ketu** is always derived as Rahu's longitude + 180°, under whichever node convention Rahu was computed with — never independently calculated via a second method.
- The node convention used must be recorded in the calculation configuration alongside ayanamsa/zodiac/house-system (§Reproducibility), so a result is always traceable to which convention produced it.

## Planetary aspects standard

Defines the standard and contract that **Phase 5 (Birth Chart / Kundli Engine)** implements. Locked per explicit project-owner decision (see §Versioning change log).

Pandit Ji implements classical Vedic **graha drishti** (sign/house-based planetary aspect), not the Western degree-based aspect system (conjunction/sextile/square/trine/opposition) — those remain out of scope for Phase 5.

- **All nine grahas** (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu) cast the universal **7th-house/7th-sign aspect** — full-strength aspect on the sign/house directly opposite their own placement.
- **Mars** additionally aspects the **4th and 8th** signs/houses from its own placement.
- **Jupiter** additionally aspects the **5th and 9th** signs/houses from its own placement.
- **Saturn** additionally aspects the **3rd and 10th** signs/houses from its own placement.
- **Rahu and Ketu** cast only the standard 7th-house/sign aspect — **no special extra aspects** are attributed to them under this standard (unlike Mars/Jupiter/Saturn). This is an explicit locked decision, not an omission: some regional traditions attribute Mars-like extra aspects to Rahu/Ketu, but that variant convention is not adopted here.
- Aspects are evaluated sign-to-sign (whole-sign house convention, §Default Vedic profile) — a planet aspects every planet and every house placed in the aspected sign, not a degree-precise partial aspect.
- This aspect table is a versioned configuration value (§Reproducibility); an alternate aspect convention (e.g., Rahu/Ketu-as-Mars-like, or Western degree-based aspects) must be a distinct, explicit configuration, never silently substituted or blended with this one.

## Planetary dignity standard

Defines the standard and contract that **Phase 5 (Birth Chart / Kundli Engine)** implements. Locked per explicit project-owner decision (see §Versioning change log).

Dignity is evaluated from each planet's precise sidereal D1 longitude against the classical exaltation/debilitation degree and own-sign table below. **Mooltrikona is explicitly out of scope for Phase 5** — a documented deferral, not a silent omission; dignity states are limited to exalted/debilitated/own-sign/neutral.


**v1.4.0 note**: Moolatrikona remains outside this Phase 5 dignity model. Phase 6 derives a separate Moolatrikona fact from sign and degree (§Phase 6 rule-engine methodology); this table is unchanged.
| Planet | Exaltation (exact degree) | Debilitation (exact degree) | Own sign(s) |
|---|---|---|---|
| Sun | 10° Aries | 10° Libra | Leo |
| Moon | 3° Taurus | 3° Scorpio | Cancer |
| Mars | 28° Capricorn | 28° Cancer | Aries, Scorpio |
| Mercury | 15° Virgo | 15° Pisces | Gemini, Virgo |
| Jupiter | 5° Cancer | 5° Capricorn | Sagittarius, Pisces |
| Venus | 27° Pisces | 27° Virgo | Taurus, Libra |
| Saturn | 20° Libra | 20° Aries | Capricorn, Aquarius |

- **Exalted**: the planet's sign matches its exaltation sign (the exact degree is recorded for reference/strength-grading use by later phases, but sign-level exaltation does not itself require the exact degree).
- **Debilitated**: the planet's sign matches its debilitation sign.
- **Own sign**: the planet's sign is one of its own sign(s) above.
- **Neutral**: none of the above apply.
- Rahu/Ketu are not evaluated against this table under this standard (no classical exaltation/debilitation degree consensus is asserted here for the nodes; a future explicit addition, never silently assumed).
- This table is a versioned configuration value (§Reproducibility); Mooltrikona ranges, if added in a future phase, must be a distinct, explicit addition rather than silently merged into "own sign."

## Sign / House lordship standard

Defines the standard and contract that **Phase 5 (Birth Chart / Kundli Engine)** implements. This is the traditional, universally-agreed rulership table (no tradition-fork exists for it), recorded here as a versioned, citable standard rather than left as an implicit assumption inside code, per the same reproducibility discipline applied to every other standard in this document.

| Sign | Ruling planet |
|---|---|
| Aries | Mars |
| Taurus | Venus |
| Gemini | Mercury |
| Cancer | Moon |
| Leo | Sun |
| Virgo | Mercury |
| Libra | Venus |
| Scorpio | Mars |
| Sagittarius | Jupiter |
| Capricorn | Saturn |
| Aquarius | Saturn |
| Pisces | Jupiter |

- A house's "lord" (house-lord) is the ruling planet of the sign occupying that house, under the locked whole-sign house convention (§Default Vedic profile) — house lordship is therefore fully derived from sign lordship plus the house-to-sign mapping, not a separately defined concept.
- This table applies uniformly across D1 and every divisional chart (§Divisional charts (Vargas)): a chart's house/sign lords are always determined from that chart's own sign placements using this same table.
- Rahu/Ketu are never assigned sign rulership under classical Parashari convention and are excluded from this table; that exclusion is intentional, not an omission.

## Chalit / Bhava-Chalit and Ashtakvarga — explicitly out of scope for Phase 5

Both are recorded here as deliberate scope exclusions, not silent omissions or guesses:

- **Chalit (Bhava-Chalit) chart**: the alternate house-cusp-based bhava boundary system (as distinct from the locked whole-sign house convention) is deferred to a follow-up decision, per explicit project-owner direction. Phase 5 implements only the whole-sign Bhava convention already locked in §Default Vedic profile.
- **Ashtakvarga**: the Bindu/point-based strength-scoring system across all planets and houses is out of scope for Phase 5 per `Phases.md`'s explicit phase boundary (not listed among Phase 5's deliverables) and is deferred to whichever later phase's roadmap entry covers strength/scoring systems.

## Data & privacy principles

Product-level data/privacy principles (data minimization, purpose limitation, consent/notice, birth-data/location-data/conversation-data/palm-image handling, retention/deletion, access control, encryption, auditability, personalization-vs-training-data separation, third-party/vendor restrictions, user export/deletion, minor/child safeguards) are defined in `PRODUCT_POLICIES.md` §"Data & Privacy Principles" — this document cross-references rather than duplicates that content, per the source-of-truth hierarchy (`SOURCE_OF_TRUTH.md`). `LEGAL_REGULATIONS.md` remains the detailed legal/compliance baseline underneath both.

## Prediction language policy

- Clearly distinguish three claim classes at all times (matching `SOURCE_OF_TRUTH.md`'s claim-class taxonomy): **calculation facts** (deterministically computed), **traditional interpretations** (what a named tradition/school teaches, per §Yoga/Dosha standards' source-tagging), and **empirical/scientific evidence** (measured, backtested performance — see `docs/ARCHITECTURE.md` §11 and `research/BACKTESTING.md`). Never blur these into one undifferentiated claim.
- Never present a guaranteed future outcome.
- Never claim "100% accurate prediction" or equivalent unqualified certainty.
- Communicate uncertainty wherever it materially affects the interpretation (see §Birth-time uncertainty and §Uncertainty below).
- Never use fear-based framing to manufacture certainty or urgency.
- Never present astrology as a substitute for professional medical, legal, or financial advice (see §Health, and `PRODUCT_POLICIES.md`'s High-impact topics section).

## Interpretation
Every major conclusion should be traceable to:
1. calculation facts
2. applicable rule/source
3. relevant period
4. supporting factors
5. conflicting factors
6. evidence/confidence state

Clearly separate calculated fact, traditional interpretation, AI explanation, and user-provided information.

## Birth-time uncertainty
Birth-time precision materially affects some calculations (house cusps, exact Nakshatra/pada boundaries near a transition, Dasha balance). If a user provides an approximate time (e.g., "around 5 PM," "between 4-6 PM," "unknown"), that uncertainty must be preserved through the pipeline and reflected in the response — never silently converted into a false-precision exact timestamp. Future birth-time rectification functionality may be supported as its own explicitly-labeled methodology, but its output must never be presented as certainty.

## Uncertainty
Approximate birth time must remain approximate. Do not silently treat it as exact.

No scientifically unsupported guarantee of future prediction.

## Reproducibility
Store engine version, ephemeris/version, ayanamsa, house system, timezone database version, coordinates, and birth inputs with calculation results.

## Health
Astrological health content is traditional/educational only, never diagnosis, prognosis, treatment or emergency advice.

## Remedies
Gemstones, mantras, puja, fasting, donations and rituals are traditional/spiritual practices, not scientifically established treatments.

## Palmistry
Image quality, hand side, visible structures and uncertainty must be separated from interpretation. No medical diagnosis from palm images. AI Palm Reading is a locked product feature (`features.md` §34), implemented in `Phases.md` Phase 13 (Palm Reading & Vision Intelligence); this standard applies to that implementation.

## Versioning
Changes to calculation standards require versioning, changelog, regression tests and explicit approval. A standards change record must include: version number, date, change description, reason, affected calculations, affected interpretations, regression-test requirement, and approval status. Historical calculation behavior must never be silently altered — a standards version change is itself a new, distinct, recorded configuration state.

### Change log
- **v1.0.0** (Pre-Phase-1 Foundation package): initial draft — Core rule, Default Vedic profile, Supported systems (list only), Interpretation, Uncertainty, Reproducibility, Health, Remedies, Palmistry, Versioning.
- **v1.1.0** (Phase 1 completion): added AI scope boundary; expanded Time/Location standards; expanded Supported systems into full per-system methodology standards (Vedic, Western/Tropical, KP, Lal Kitab, Nadi, with Lal Kitab/Nadi explicitly marked provisional pending research validation); added Divisional charts (Vargas), Vimshottari Dasha, Nakshatra standards, Yoga/Dosha standards, Panchang/Muhurta standards, and Numerology standards sections; added Data & privacy principles (cross-reference to `PRODUCT_POLICIES.md`); added Prediction language policy; added Birth-time uncertainty section. Approval status: locked per project-owner direction to close all 13 `Phases.md` Phase 1 content requirements.
- **v1.2.0** (Phase 4 pre-implementation lock): added Combustion standard (per-planet orb thresholds, Brihat Parashara Hora Shastra tradition) and Node convention (Rahu/Ketu: Mean Node default, True Node supported as explicit alternate config) — both were confirmed genuinely unspecified during Phase 4's mandatory cross-check and required an explicit project-owner decision before the astronomical calculation engine could implement them. Reason: `Phases.md` Phase 4 requires combustion and Rahu/Ketu as deliverables; no prior version of this document defined either sufficiently to implement without guessing. Affected calculations: Phase 4's combustion status and node/Ketu derivation. Affected interpretations: none yet (Phase 6 rule content will consume these facts later). Regression-test requirement: Phase 4's golden/boundary tests must cover both thresholds and both node conventions. Approval status: locked per explicit project-owner decision.
- **v1.3.0** (Phase 5 pre-implementation lock): expanded §Divisional charts (Vargas) with full derivation formulas for the 14 remaining Shodashvarga charts (D2, D3, D4, D7, D10, D12, D16, D20, D24, D27, D30, D40, D45, D60), completing the locked 16-varga set; added Planetary aspects standard (Vedic graha drishti — universal 7th aspect for all nine grahas, Mars 4th/8th, Jupiter 5th/9th, Saturn 3rd/10th, no special extra aspects for Rahu/Ketu); added Planetary dignity standard (exact exaltation/debilitation degrees and own-sign table for the seven classical grahas, Mooltrikona explicitly excluded); added Sign/House lordship standard (the traditional 12-sign ruler table); recorded Chalit/Bhava-Chalit and Ashtakvarga as explicit out-of-scope deferrals for Phase 5. Reason: `Phases.md` Phase 5 requires house lords, planetary aspects, planetary dignity, and all sixteen divisional charts as deliverables; Phase 5's mandatory 35-item pre-implementation standards audit confirmed only D1/D9 had derivation formulas and aspects/dignity/lordship had no locked standard, so all were genuinely unspecified and required explicit project-owner decisions before the Kundli engine could implement them. Affected calculations: Phase 5's house-lord, aspect, dignity, and D2/D3/D4/D7/D10/D12/D16/D20/D24/D27/D30/D40/D45/D60 chart derivations. Affected interpretations: none yet (later rule-engine/interpretation phases will consume these facts). Regression-test requirement: Phase 5's boundary/golden/invariant tests must cover every varga formula's sign-boundary transitions, every aspect rule, and every dignity degree threshold. Approval status: locked per explicit project-owner decision (two `AskUserQuestion` rounds: aspects/dignity-scope/varga-research-approach/Chalit-deferral, then D3-rule-choice and overall-lock-confirmation).
- **v1.4.0** (Phase 6 pre-implementation lock): added §Phase 6 rule-engine methodology (source tiers; source-profile naming and rule identifiers; ambiguity-preserving evaluation; result statuses and reason codes; aspect refinement for "aspected"/"unaspected" conditions; strength dependency on Shadbala; BPHS Ch. 3 natural and compound relationships, natural benefic/malefic with two labelled Pandit Ji conventions, and the BPHS Ch. 34 84-cell functional-nature table as the canonical BPHS functional profile; node policy; Moolatrikona as a Phase 6 fact; D27 recorded as UNRESOLVED with the Phase 5 D27 formula unchanged; dependencies owned by other phases; evidence bundle contents) and clarified that Vimshottari balance and year-length conventions are Phase 7 decisions. Reason: `Phases.md` Phase 6 requires a versioned rule engine, and the Phase 6 methodology research (`research/ASTROLOGY_SOURCES.md` Groups 1–8) found relationships, natural and functional nature, strength, aspect refinement, node treatment, Moolatrikona and ambiguity handling genuinely unspecified. Affected calculations: none in Phases 4–5 (no formula changed). Affected interpretations: all Phase 6 rule outputs. Regression-test requirement: Phase 5 tests must pass unchanged; Phase 6 tests must cover every rule family. Also added §Language and multilingual interaction (AI understands English, Hindi, Hinglish, Romanized Hindi and code-switching regardless of UI language; no AI language toggle; UI language English or हिन्दी set in Account → Language, default English, persisted, independent of AI response language, which is defined in the Agent phase). Phase 5 calculation records keep `standards_version = 1.3.0`. Approval status: approved by the project owner, Phase 6 Group 8 decision.
- **v1.4.1** (Nakshatra/Pada boundary-convention clarification, 2026-09-20): §Nakshatra standards now records the half-open, lower-inclusive/upper-exclusive classification convention for Nakshatras and Padas, exact rational classification of the normalized float, and 360° = 0°, labelled a Pandit Ji engineering convention and not a classical source rule; the existing `near_boundary` behaviour and the tiny-negative-float normalization behaviour are recorded as unchanged. Reason: Phase 5's `nakshatra_position()` divided by the float 360.0/27.0 and assigned exactly representable boundary longitudes to the lower bucket (40.0° returned Krittika, 10.0° returned Pada 3); the defect was reproduced, and the project owner approved the convention and the correction. Versioning note: a patch-level increment was used because no formula, table or classical value changed, only the previously unstated side of a boundary; v1.5.0 remains available for the Phase 7 pre-implementation lock. Affected calculations: the Nakshatra and Pada of any longitude lying exactly on a boundary (implemented in commit `091ca1b`, CI run `35500359836`); all other longitudes classify identically to before (0 differences over 200,000 random longitudes, compared old versus new). Affected interpretations: any later consumer of Nakshatra, Pada or the Vimshottari starting lord for such a longitude; none yet, because no Phase 7 code exists. Regression-test requirement: exact-boundary, neighbourhood, normalization and Kundli-path tests (added in `091ca1b`; astro-engine 353 tests, rule-engine 235 tests). Open follow-up: Phase 5 calculation records still carry `standards_version = 1.3.0` (`kundli.py` `STANDARDS_VERSION`), although their boundary behaviour now follows v1.4.1; whether and how that constant advances is an owner decision and a code change, not made here. Approval status: the convention and the code correction were approved by the project owner; this documentation entry records that approval.
- **v1.5.0** (Phase 7 methodology lock, 2026-09-20): added §Phase 7 methodology lock to §Vimshottari Dasha: scope and exclusions (Vimshottari to the Pratyantar level; facts only, no interpretation; Maraka timing is a later rule-engine consumer; no Sookshma, Prana, other Dasha systems or rectification); the balance-at-birth default profile `DASHA_STANDARD_V1_BALANCE_LONGITUDE` with the two source-alternative profiles documented and inactive; the year-length default profile `YEAR_365_2425_FIXED_DAY` with alternatives; the sub-period profile `DASHA_SUBPERIOD_PROPORTIONAL_FULL_PARENT_V1`; UTC and exact-arithmetic time policy; the half-open boundary convention for Dasha periods; the EXACT, APPROXIMATE and NOT_EVALUABLE birth-time precision model; statuses and reason codes; the `DashaFacts` contract and the Phase 6 evidence-bundle integration. Reason: `Phases.md` Phase 7 requires Vimshottari Dasha; the balance method is a documented source conflict, no verse read states the year length, and the treatment of the birth-balance Mahadasha's sub-periods is not stated in the sources read, so each needed an explicit, labelled engineering profile before implementation. Every profile is a Pandit Ji engineering convention or a source-supported statement at its stated verification level, never presented as the only valid classical method. Affected calculations: new only (Vimshottari periods); no Phase 4, 5 or 6 formula changed. The Phase 5 `STANDARDS_VERSION` constant deliberately stays 1.3.0 (see the lock's version note). Affected interpretations: none; later phases consume the facts. Regression-test requirement: sequence and years, balance, generation, boundaries, precision, lookup, serialization and bundle-integration tests (astro-engine `test_dasha_*`, rule-engine `test_dasha_*`). Open items recorded for the owner: (1) confirmation of the full-parent treatment of the birth-balance Mahadasha's sub-periods; (2) the balance-method source conflict remains open by design and can be revisited if the Panchanga-time profile is implemented. Approval status: methodology defaults and scope approved by the project owner in the Phase 7 implementation directive; the sub-period treatment and the retained Kundli constant are implementation decisions recorded here for owner review.
- **v1.6.0** (Phase 8 methodology lock, 2026-09-21): added §Transit / Gochar standards (TR-01 to TR-15): scope and exclusions (transit facts and provenance only; no interpretation, remedies, alerts, Ashtakavarga scoring, degree or orb contacts, Dhaiya, Ashtama or degree-based Sade Sati); the `TRANSIT_REF_MOON_SIGN` default reference and the optional engineering-convention Lagna fact; the favourable-house readings of Phaladeepika, Brihat Samhita, Brihat Jataka and a BPHS-derived reading, with the Moon-from-Moon conflict preserved as `NOT_EVALUABLE(reading_ambiguous)`; the single-source Rahu and Ketu treatment; the Phaladeepika-specific Vedha profile with its exceptions, the node-occupant rule and the Venus translation anomaly; sign-based transit-to-natal contacts; the engineering-convention event kinds; the `modern_tradition` Sade Sati profile with segments and episodes; the UTC, half-open boundary, solver-tolerance and accuracy policy with the JPL Horizons engineering evidence and the ayanamsa-sensitivity note; the 200-year and 50,000-event limits; statuses and reason codes; the `TransitFacts` contract and the additive evidence-bundle section. Reason: `Phases.md` Phase 8 lists transits and Sade Sati but stated no dependencies, methodology, exclusions or exit criteria, and the sources read give a Gochar scheme with Vedha only in Phaladeepika and agree across texts only partly (the Moon from the Moon conflicts; the nodes are single-source; Sade Sati as a combined unit is not classical). Affected calculations: new only (transit states, events, Sade Sati segments); no Phase 4, 5, 6 or 7 formula changed (an additive node-ID constant was added to the ephemeris adapter). Affected interpretations: none; later phases consume the facts. Regression-test requirement: exact synthetic-motion ingress, station and retrograde re-entry tests; source-reading, Vedha, node and conflict tests; window, limit and precision tests; determinism and serialization; evidence-bundle integration; all earlier suites unchanged. Approval status: methodology approved by the project owner at Approval Gate 1 (all nine recommendations); implementation and results are recorded in `SUMMARY.md` §26 and await Approval Gate 2.

## Phase 1 standards checklist

Confirms all 13 `Phases.md` Phase 1 content requirements (exact wording preserved) are documented above as **standards**, not engines — each links to the phase that implements the corresponding engine:

- [x] Vedic astrology baseline — §Default Vedic profile, §Astrology systems (Vedic/Jyotish)
- [x] Lahiri ayanamsa — §Default Vedic profile
- [x] Sidereal zodiac — §Default Vedic profile
- [x] House calculation standards — §Default Vedic profile (Vedic whole-sign); §Astrology systems (Western Placidus, KP Placidus)
- [x] D1/D9/divisional-chart definitions — §Divisional charts (Vargas) — implemented Phase 5
- [x] Vimshottari Dasha methodology — §Vimshottari Dasha — implemented Phase 7
- [x] Nakshatra definitions — §Nakshatra standards — implemented Phase 5
- [x] Yoga/Dosha definitions — §Yoga/Dosha standards — implemented Phase 6
- [x] KP/Lal Kitab/Nadi/Western modules — §Astrology systems — implemented Phase 9
- [x] Panchang/Muhurta standards — §Panchang/Muhurta standards — implemented Phase 10
- [x] Numerology methodology — §Numerology standards — implemented Phase 11
- [x] Data/privacy rules — §Data & privacy principles (cross-reference to `PRODUCT_POLICIES.md`)
- [x] Prediction language policy — §Prediction language policy
