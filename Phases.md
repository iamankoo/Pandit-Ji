🪔 Pandit Ji — 21-Phase Master Development Plan

## Phase 1 — Product & Astrology Standards

Define exactly what Pandit Ji supports and, critically, which calculation standards/rules it follows.

- Vedic astrology baseline
- Lahiri ayanamsa
- Sidereal zodiac
- House calculation standards
- D1/D9/divisional-chart definitions
- Vimshottari Dasha methodology
- Nakshatra definitions
- Yoga/Dosha definitions
- KP/Lal Kitab/Nadi/Western modules
- Panchang/Muhurta standards
- Numerology methodology
- Data/privacy rules
- Prediction language policy

Deliverable: `docs/ASTROLOGY_STANDARDS.md` (locked canonical location — the single, authoritative standards document; no separate `docs/calculation-standards.md`)

## Phase 2 — System Architecture

Design the complete technical architecture before implementation.

```
Flutter / Web
      ↓
API Gateway
      ↓
FastAPI
      ↓
Agent Orchestrator
 ┌────┼─────┬──────┐
 ↓    ↓     ↓      ↓
Chart Rules Dasha Knowledge
 ↓    ↓     ↓      ↓
 └────┴─────┴──────┘
          ↓
      AI Reasoner
          ↓
      Verification
```

Define:

- Services
- APIs
- Queues
- Databases
- AI infrastructure
- Caching
- Authentication
- Observability

Deliverable: architecture documentation + diagrams.

## Phase 3 — Repository & Engineering Foundation

Create the production repository.

```
pandit-ji/
├── apps/
│   ├── mobile/
│   ├── web/
│   └── admin/
├── services/
│   ├── astro-engine/
│   ├── rule-engine/
│   ├── agent/
│   ├── knowledge/
│   └── verification/
├── packages/
│   ├── shared/
│   ├── contracts/
│   └── ui/
├── datasets/
├── tests/
├── docs/
└── infrastructure/
```

Canonical service names (locked): `astro-engine`, `rule-engine`, `agent`, `knowledge`, `verification`. Do not use alternative names such as `astrology-engine`, `ai-agent`, or `knowledge-base` anywhere in the codebase or documentation.

Set up:

- Git
- CI/CD
- Docker
- Docker Compose
- Environment management
- Testing framework
- Linting
- Formatting
- Pre-commit hooks
- Development/staging/production environments

Deliverable: clean executable project skeleton.

## Phase 4 — Astronomical Calculation Engine

This is one of the most important phases.

Build the deterministic astronomical foundation.

Implement:

- Sun
- Moon
- Mars
- Mercury
- Jupiter
- Venus
- Saturn
- Rahu
- Ketu
- Planetary longitude
- Latitude
- Speed
- Retrograde
- Combustion
- Planetary degrees
- Sunrise/sunset
- Timezone conversion

Use a reliable ephemeris foundation such as Swiss Ephemeris.

### Testing

Compare results against trusted reference calculations across hundreds/thousands of birth dates.

Deliverable: deterministic planetary calculation engine.

## Phase 5 — Birth Chart / Kundli Engine

Turn astronomical data into complete charts.

Implement:

- Ascendant/Lagna
- Houses
- Rashis
- Bhavas
- Planet-house placement
- Planet-sign placement
- Nakshatra
- Pada
- House lords
- Planetary aspects
- Planetary dignity

Then:

- D1
- D9
- D10
- D2
- D3
- D4
- D7
- D12
- D16
- D20
- D24
- D27
- D30
- D40
- D45
- D60

where applicable under the selected standard.

Deliverable: complete machine-readable Kundli.

## Phase 6 — Vedic Astrology Rule Engine

Now we teach the system astrology rules, rather than asking the LLM to invent them.

Build structured rules for:

- Planet meanings
- House meanings
- Sign meanings
- Nakshatra meanings
- Lordships
- Aspects
- Strength
- Dignity
- Planetary relationships
- Benefic/malefic conditions
- Yogas
- Doshas

Every rule should have:

- Rule ID
- System
- Conditions
- Evidence
- Interpretation
- Priority
- Exceptions
- Sources/reference
- Tests

Rules are source-specific profiles (for example a BPHS profile and a Phaladeepika profile of the same yoga are separate rules), evaluated with ambiguity-preserving results (`docs/ASTROLOGY_STANDARDS.md` §Phase 6 rule-engine methodology). `Priority` is metadata only and never erases conflicting evidence.

Doshas in Phase 6 are profile-based:

- Mangal/Kuja Dosha as separately tagged source profiles (BPHS Ch. 80 v. 47–49 and Jataka Parijata), never as one generic rule
- Kaal Sarp Dosha only as a clearly tagged `MODERN_TRADITION` profile, never as a classical rule, and only once a named source is selected; until then it returns `NOT_EVALUABLE(source_profile_not_selected)`

Phase 6 does not calculate astronomy, dashas, transits, Panchang, upagrahas, special Lagnas, Pranapada, Shadbala, partial or degree-based aspects, Jaimini, longevity or D27; rules that need them return `NOT_EVALUABLE` with the dependency named.

Deliverable: versioned astrology rule engine.

## Phase 7 — Dasha & Timing Engine

Build the temporal intelligence.

Implement (Vimshottari Dasha only, to the Pratyantar level):

- Vimshottari Dasha
- Mahadasha
- Antardasha
- Pratyantar
- Dasha start/end
- Current Dasha
- Future Dasha
- Historical Dasha
- Dasha transitions

Phase 7 produces **deterministic temporal facts and their provenance**. "Connecting" Dasha to Houses, Lords, Planets, Yogas, Career, Marriage, Education, Finance and Relationships means exposing stable timing facts and references (period IDs, lords, UTC boundaries) that later phases consume. It does **not** mean interpreting them: life-domain intelligence belongs to Phase 12 (knowledge) and Phase 17 (life-domain intelligence), and Maraka timing is a later rule-engine consumer of these facts, not Phase 7 scope.

Dependencies:

- Phase 4 (UTC time resolution, Moon longitude) and Phase 5 (Nakshatra classification, Nakshatra-lord table)
- Phase 6 consumes Dasha facts through the evidence bundle; the rule engine never calculates a Dasha

Inputs: the birth Moon's sidereal longitude, the UTC birth instant with its original local input and IANA timezone, a birth-time precision (EXACT, APPROXIMATE with an uncertainty interval, or NOT_EVALUABLE), and explicit balance and year-length profile IDs.

Outputs: a `DashaFacts` result (system, status and reason code, profile IDs, boundary convention, precision, starting Nakshatra/Pada/lord, balance, the nested period tree with UTC boundaries, warnings, labelled provenance), period lookup and transition queries, and an additive optional `dasha` section in the Phase 6 evidence bundle.

Methodology: `docs/ASTROLOGY_STANDARDS.md` §Phase 7 methodology lock (v1.5.0). Balance and year length are explicit profiles, not classical certainty; the balance method remains a documented source conflict.

Exclusions:

- Other Dasha systems (Ashtottari, Yogini, Chara, Narayana and all others)
- Sookshma and Prana
- Birth-time rectification or automatic time correction
- Life-domain predictions (career, marriage, finance, education, health, relationships)
- Maraka interpretation, planetary-result or house/sign-based prediction, and any AI-generated interpretation

Exit criteria:

- Vimshottari to the Pratyantar level is implemented with explicit balance, year-length and sub-period profile IDs persisted in every result
- UTC is canonical; the birth-time precision is explicit; Nakshatra and Dasha boundaries are half-open and deterministic
- Periods are contiguous, non-overlapping and correctly nested; historical, current and future lookup work
- Dasha facts are recorded in the evidence bundle with provenance, and Phase 5 and Phase 6 behaviour is unchanged
- Tests cover the sequence, balance, generation, boundaries, precision, lookup, serialization and integration

Test requirements: unit, boundary, invariant (containment, no gaps, no overlaps, duration conservation, determinism), precision and uncertainty, DST and UTC conversion, serialization round trip, evidence-bundle integration and regression of the existing suites.

Deliverable: complete life-period timeline (facts and provenance; no interpretation).

## Phase 8 — Transit / Gochar Engine

Build real-time and historical planetary movement analysis.

Implement:

- Current transits
- Historical transits
- Future transits
- Transit → natal planet
- Transit → natal house
- Jupiter
- Saturn
- Rahu
- Ketu
- Sade Sati (owned by this phase, not Phase 6)
- Major transit events

Create:

```
Natal Chart
     +
Current Date
     ↓
Transit State
     ↓
Relevant Events
```

Phase 8 produces **deterministic transit facts and their provenance** (the natal reference, each planet's sign, degree, speed and retrograde state, structural relations to the natal chart, when a state changes, and the Sade Sati sign-band timeline). It does **not** interpret them: "Transit-based predictions" and "Transit alerts/readings" (`features.md` §7) belong to Phase 12 (knowledge), Phase 15 (agent), Phase 17 (life-domain intelligence) and Phase 20 (notifications). "Relevant Events" means the engineering-defined structural events below, not judged significance.

Dependencies:

- Phase 4 (Swiss Ephemeris positions, speed and retrograde; UTC time resolution; the Mean Node default and True Node alternate) and Phase 5 (sign classification, Nakshatra classification, graha drishti, the Kundli as the natal reference)
- Phase 7 conventions (UTC canonical, half-open intervals, the EXACT / APPROXIMATE / NOT_EVALUABLE precision model, labelled provenance)
- Phase 6 consumes transit facts through the evidence bundle; the rule engine never calculates a transit

Inputs: a natal reference (the Moon's sidereal longitude, its precision, and for an exact natal time the Lagna and the natal planet longitudes), a UTC instant and/or a UTC window, methodology profile IDs, and the Phase 4 calculation configuration.

Outputs: a `TransitFacts` result (system, status and reason code, profile IDs, boundary convention, configuration, natal summary, an accuracy block, an optional instant snapshot with per-planet state, favourable-set readings, Vedha facts and sign-based contacts, an optional window with events, an optional Sade Sati section, warnings, labelled provenance) and an additive optional `transit` section in the Phase 6 evidence bundle.

Methodology: `docs/ASTROLOGY_STANDARDS.md` §Transit / Gochar standards (v1.6.0, TR-01 to TR-15). Default reference is the natal Moon sign (`TRANSIT_REF_MOON_SIGN`); the Lagna is an optional engineering-convention fact. The favourable-house readings of Phaladeepika, Brihat Samhita, Brihat Jataka and a BPHS-derived reading are separate profiles; the Moon-from-Moon disagreement is preserved (`NOT_EVALUABLE(reading_ambiguous)`). Vedha is a Phaladeepika-specific structural profile. Rahu and Ketu are single-source and kept separate. Sade Sati is a `MODERN_TRADITION` sign-based profile, not a classical rule.

Events (all Pandit Ji engineering conventions): sign ingress (including backward re-entry), retrograde and direct stations, and, opt-in, Nakshatra ingress; transit-to-natal contacts are sign-based only (same-sign conjunction and Phase 5 graha drishti).

Limits: a window of at most 200 years and at most 50,000 events per request.

Exclusions:

- Effect or prediction text, good or bad verdicts, remedies, alerts, notifications and any AI-generated interpretation
- Ashtakavarga scoring and transit scoring by bindus (Phase 9), Sarvatobhadra Chakra, Latta, half-sign or decanate effectiveness
- Degree-based or orb-based contacts, applying and separating aspects
- Dhaiya, Ashtama Shani and degree-based Sade Sati variants (reserved profile IDs only)
- Birth-time rectification, HTTP endpoints and database tables (Phase 18)

Exit criteria:

- Transit states, events and the Sade Sati timeline are implemented with explicit profile IDs, configuration and ephemeris mode persisted in every result
- UTC is canonical; sign, Nakshatra and window intervals are half-open and deterministic; ingress and station instants are documented as numerical solutions with a stated tolerance and are never called exact
- Source conflicts (Moon from the Moon, Rahu and Ketu, the Venus Vedha wording) are preserved and returned as `NOT_EVALUABLE` where they prevent a single answer
- Transit facts are recorded in the evidence bundle with provenance, and Phase 4, 5, 6 and 7 behaviour is unchanged
- Tests cover synthetic-motion ingress, stations and retrograde re-entry, boundaries, source readings, Vedha, nodes, Sade Sati segments and episodes, precision and limits, DST and UTC conversion, serialization and hashing, integration and regression of all earlier suites

Test requirements: unit, boundary, invariant (segments tile, events ordered and unique, determinism), source-reading and conflict, node, precision and limit, timezone and UTC conversion, serialization round trip, evidence-bundle integration, an independent JPL Horizons comparison fixture (engineering evidence, 42 samples) and regression of the existing suites.

Known limitations: Moshier mode unless Swiss Ephemeris data files are configured (about 0.4″ for planets and about 5″ for the Moon in tropical longitude against JPL Horizons in a 42-sample comparison; seconds at a sign boundary and minutes near a station); the Lahiri ayanamsa value and the sidereal frame are not independently verified (the implied ayanamsa differs from `get_ayanamsa_degrees` by up to about 15.6″, about 1.5 hours of Saturn's motion) and published ingress times differ by hours across sources; no Sanskrit-level verification of any Gochar source; Vedha and the node readings are single-source.

Deliverable: dynamic transit engine (facts and provenance; no interpretation).

## Phase 9 — Advanced Astrology Systems

Add the remaining astrology methodologies.

Modules:

- KP Astrology
- KP Horary
- Lal Kitab
- Nadi Astrology
- Horary Astrology
- Western Astrology
- Tropical zodiac
- Western aspects
- Placidus
- Chinese astrology
- Vastu
- Feng Shui-related modules
- Tarot

Vedic strength and scoring systems:

- Shadbala — BPHS Ch. 27–28
- Ashtakvarga — BPHS Ch. 66–72

Both require methodology audits before implementation.

Jaimini module (isolated, requires a scope decision and methodology audit before implementation):

- Chara Karakas (BPHS Ch. 32)
- Jaimini sign aspects (Rashi Drishti, BPHS Ch. 8)

Vedic longevity (Ayurdaya) methods (BPHS Ch. 43; requires Shadbala and a methodology and product-policy audit before implementation; produces structural facts only, not lifespan predictions). Maraka timing is a later rule-engine consumer of the Phase 7 Dasha facts (Phase 7 exposes timing facts only; it does not interpret Maraka periods).

Each system should be isolated as a module, rather than mixing incompatible rules.

Deliverable: modular multi-system astrology framework.

Status (2026-09-25, project-owner decisions; details in `docs/ASTROLOGY_STANDARDS.md` v1.21.0 and `SUMMARY.md` §34-§35): **complete as scoped by the owner, with accepted deferrals.** The module list above is kept unchanged as the original roadmap.

| Roadmap item | Outcome |
|---|---|
| KP Astrology, KP Horary | Implemented as a foundation (positions, cusps, star/sub lords, 249 table, significators a-d, Ruling Planets, horary chart); no event judgment or timing |
| Lal Kitab | Deferred (owner-accepted): no edition could be read; presumed in copyright |
| Nadi Astrology | Deferred (owner-accepted): leaf-matching is not a deterministic calculation |
| Horary Astrology (general) | Deferred (owner-accepted): tradition not chosen; KP Horary implemented |
| Western Astrology, Tropical zodiac, Western aspects, Placidus | Implemented (WP-D) |
| Chinese astrology | Implemented as Four Pillars calendar pillars; luck cycles need the person's sex (not collected) |
| Vastu | Deferred (owner-accepted); cross-domain Vastu stays with Phase 17 |
| Feng Shui-related modules | Deferred (owner-accepted) |
| Tarot | Implemented as deck, spreads and seeded or user-selected layouts; meanings deferred (owner-accepted). *(Phase 12: Waite's meanings are stored as public-domain knowledge text; the Phase 9 engine itself still returns no meanings.)* |
| Shadbala | Implemented: the BPHS verse profile (no total) and a separate modern profile after B. V. Raman (with totals); Ishta/Kashta (Ch. 28) research only |
| Ashtakvarga | Implemented (WP-A1/A2/A3, evidence bundle WP-EB) |
| Chara Karakas, Rashi Drishti | Implemented (WP-B), with planet-level Rashi Drishti added |
| Arudha Pada, Karakamsa | Implemented on the owner's Phase 9 directive (not in the original list above) |
| Jaimini Dashas | Deferred (owner-accepted) |
| Ayurdaya | Excluded: `PRODUCT_POLICIES.md` prohibits lifespan outputs (owner decision) |

Every implemented system is recorded in the rule-engine evidence bundle as an optional section (no rule reads them yet). Deferred and excluded systems are not implemented and must not be presented as available.

## Phase 10 — Panchang, Muhurta & Calendar Engine

Build the Indian calendar subsystem.

Implement:

- Tithi
- Vara
- Nakshatra
- Yoga
- Karana
- Hora
- Choghadiya
- Rahu Kaal
- Gowri
- Panchak
- Bhadra
- Tara Balam
- Chandra Balam
- Sunrise
- Sunset
- Moonrise
- Moonset

Special points (sunrise-dependent calculations consumed by Phase 6 rules):

- Sun-based upagrahas (Dhooma, Vyatipata, Parivesha, Indrachapa, Upaketu)
- Gulika and Mandi, as separately tagged source readings (not assumed identical)
- Special Lagnas (Bhava, Hora, Ghatika, Varnada)
- Pranapada

Tara Balam here is the Panchang/Muhurta factor; Tara in the Ashtakoot compatibility list belongs to Phase 11.

Then:

- Muhurta
- Marriage
- Griha Pravesh
- Mundan
- Housewarming
- Other auspicious activities

Deliverable: complete Panchang/Muhurta engine.

Status (2026-09-25, owner approval of Phase 10; details in `docs/ASTROLOGY_STANDARDS.md` v1.23.0 PC-01 to PC-31, MU-01 to MU-14 and `SUMMARY.md` §36): **implemented for the source-verified scope, with the items below not implemented and open owner decisions.** The list above is kept unchanged as the original roadmap.

| Roadmap item | Outcome |
|---|---|
| Tithi, Vara, Nakshatra, Yoga, Karana | Implemented with exact transitions; reproduced on the Calendar Reform Committee's printed calendar (61 days) |
| Sunrise, Sunset, Moonrise, Moonset | Implemented; CRC sunrise default, Phase 4 upper-limb convention as an explicit alternative |
| Hora | Implemented (equal hours from sunrise); unequal horas not implemented (no source) |
| Rahu Kaal | Implemented (Kalaprakasika translator's note); Yamaganda and Gulika Kalam also given |
| Choghadiya, Gowri | Not implemented: no primary source read (PC-22) |
| Panchak | Implemented as two different computations: Nakshatra Panchaka and the remainder Panchaka |
| Bhadra | Implemented as the Vishti karana; Bhadra residence not implemented |
| Tara Balam, Chandra Balam | Implemented (Chandra Bala in two profiles); need the person's birth nakshatra and Moon sign |
| Calendar (month, Adhik Maas, years) | Implemented: amanta and purnimanta months, adhika and kshaya, Saka and Chaitradi Vikrama years; Lahiri saura frame by default, CRC frame as a labelled alternative, both reported |
| Sun-based upagrahas, Gulika and Mandi, special Lagnas, Pranapada | Implemented with separately tagged readings |
| Muhurta: Marriage, Griha Pravesh, Mundan, Housewarming | Implemented as factor facts and window search (Housewarming = Griha Pravesh); no verdict |
| Other auspicious activities | Not implemented (no rule set read) |

Owner decisions of 2026-09-25 (standards v1.24.0): **Phase 10 is accepted as complete for its supported scope.** Lahiri is the default saura frame for user-facing results, with the CRC 23 deg 15 min frame as a labelled alternative (PC-15); the Muhurta rules stay as astro-engine data, a recorded deviation (MU-03); Choghadiya and Gowri stay deferred and unavailable until verified primary sources exist (PC-22); no further Muhurta purposes until the three are validated in production (MU-01); no Shadbala strength threshold, so Shadbala-dependent rules stay NOT_EVALUABLE (SM-11). Deferred items: Choghadiya, Gowri, unequal horas, Bhadra residence, regional solar calendars, Karttikadi/Ashadhadi Vikrama years, other Muhurta purposes. Roadmap note: Griha Pravesh and Housewarming are one ceremony and one rule set.

**Stopping point (2026-09-25): Phase 10 closure is complete for the approved scope. Phase 11 has not started.** The next session must begin by rereading `SUMMARY.md` (§39) and this file, and may continue only from the saved stopping point after the owner's explicit approval. *(Superseded 2026-09-27: Phase 11 is implemented; see the Phase 11 status block and `SUMMARY.md` §40.)*

## Phase 11 — Numerology + Compatibility

Status (2026-09-25): **not started**; awaiting the owner's explicit approval (see `SUMMARY.md` §39). *(Superseded by the Phase 11 status block at the end of this section, 2026-09-27.)*

Build separate engines.

### Numerology

- Moolank
- Bhagyank
- Name numerology
- Lucky numbers
- Numerology interpretation

### Compatibility

Implement:

- Ashtakoot
- Varna
- Vashya
- Tara
- Yoni
- Graha Maitri
- Gana
- Bhakoot (Bhakoot Dosha in compatibility is owned by this phase, not Phase 6)
- Nadi (Nadi Dosha in compatibility is owned by this phase, not Phase 6)
- 36-point system
- Doshas
- Additional compatibility factors

Deliverable: compatibility + numerology services.

Phase 11 produces **deterministic numerology numbers and matching facts with their provenance**. It does not interpret them: numerology and compatibility interpretation, reports and AI conversation belong to Phase 12 (knowledge), Phase 15 (agent) and Phase 19 (app). "Tara" here is the matching factor (Tara Kuta), not the Phase 10 Muhurta Tara Balam; "Nadi" here is the matching factor (Nadi Kuta / Nadi Dosha), not the Phase 9 Nadi Astrology.

Dependencies:

- Phase 4 (UTC time resolution, the Moon's sidereal longitude) and Phase 5 (Nakshatra, Pada and Rashi classification, sign lords)
- Phase 6 (the BPHS Ch. 3 natural relationships, reused for Graha Maitri; the Kuja/Mangal rule profiles, compared across two people through the evidence bundle)
- Phase 7 conventions (the EXACT / APPROXIMATE / NOT_EVALUABLE birth-time precision model)
- Phase 6 consumes Phase 11 facts through the evidence bundle; the rule engine never calculates them

Inputs: for numerology, a civil date of birth and/or an explicitly supplied Latin spelling of the name in use, a profile ID and (Pythagorean) a master-number policy; for compatibility, a profile ID with no default, two people's birth date-time, timezone, coordinates and precision (no gender, sex or role), the caller's current civil date and a consent attestation.

Outputs: `NumerologyFacts` (Moolank, Bhagyank, each profile's own date numbers, the name number, Cheiro's associated numbers, interpretation references, provenance) and `CompatibilityFacts` (per-factor facts, doshas with exception conditions, the Ashtakoot total only when every kuta is evaluated, the ten-porutham counts, policy checks, provenance), plus additive optional `numerology` and `compatibility` sections in the evidence bundle and a Kuja partner comparison.

Methodology: `docs/ASTROLOGY_STANDARDS.md` v1.25.0 (NU-01 to NU-16, CM-01 to CM-12, AK-01 to AK-16, TP-01 to TP-14, EV-11 to EV-16).

Exclusions:

- Gender, sex or bride/groom role collection or inference; any matching for a person under 18
- An overall compatible/incompatible verdict, statements of effect, caste-based rules, remedies
- Numerology interpretation text, generated lucky numbers, colours or stones; transliteration of non-Latin names
- Regional nadi schemes, varga kuta, name-letter matching, porutham gothram and asterism sex; HTTP endpoints and database tables (Phase 18)

Exit criteria:

- Both numerology profiles and both matching systems are implemented as separate, versioned profiles with provenance in every result
- Role-dependent factors are not evaluable unless role-invariant; no 36-point total is produced from a partial set of kutas
- Matching is refused for anyone under 18 before any calculation; no gender or role input exists
- Non-Latin names are not evaluable rather than transliterated; interpretation is deferred
- Facts are recorded in the evidence bundle; earlier bundles hash as before; Phase 4-10 behaviour is unchanged
- Tests cover every kuta and porutham, the source tables and worked examples, the policies, uncertainty, determinism and regression of all earlier suites

Status (2026-09-27, owner's Phase 11 directive; details in `docs/ASTROLOGY_STANDARDS.md` v1.25.0 and `SUMMARY.md` §40): **implemented for the source-supported scope, with the limits below.** The lists above are kept unchanged as the original roadmap.

| Roadmap item | Outcome |
|---|---|
| Moolank | Implemented (Cheiro's Birth number; Chaldean default, Pythagorean alternate) |
| Bhagyank | Implemented (Phase 1 arithmetic), with Cheiro's separate date numbers and Balliett's birth number reported beside it |
| Name numerology | Implemented for Latin spellings (Cheiro and Balliett tables); Devanagari and other scripts not evaluable, no transliteration |
| Lucky numbers | Chaldean: Cheiro's own-series and interchangeable numbers, as source associations; Pythagorean: deferred (no rule read) |
| Numerology interpretation | Deferred to Phase 12 (source references only). *(Phase 12: still deferred; no usable proofread text, see the Phase 12 status block.)* |
| Ashtakoot (Varna, Vashya, Tara, Yoni, Graha Maitri, Gana, Bhakoot, Nadi) | Implemented after Muhurta Chintamani v. 21-37. Tara, Graha Maitri, Bhakoot and Nadi always evaluable; Varna and Gana only when role-invariant; Yoni not evaluable for asymmetric printed cells; Vashya never scored (the source leaves most relations to usage and the point schemes disagree) |
| 36-point system | Not produced under v1.25.0: it requires all eight kutas, and Vashya is never scored |
| Doshas (Bhakoot, Nadi) | Implemented with the source's exception conditions; Bhakoot cancellation verdict not evaluated (disputed); Gana dosha by role |
| Additional compatibility factors | The ten poruthams of Kalaprakasika Ch. XIII as a separate system (role-dependent ones not evaluable); the Kuja/Mangal partner comparison from the Phase 6 profiles |

Owner decisions still open: an explicit, consented role input (would unlock Varna, Gana, Dhinam, Mahendhram, Sthree-Dheergham and most Rasi rules); a Vashya source or reading (would allow the 36-point total); a Devanagari letter table; numerology interpretation content (Phase 12); a default matching system (none is set); whether 18 stays the matching age threshold.

Owner acceptance (2026-09-27): **Phase 11 is accepted as complete for its source-supported scope**, exactly as documented above: unsupported or unresolved functionality stays deferred or NOT_EVALUABLE, and in the full-roadmap sense the 36-point system is not produced and role-dependent factors are not evaluable. The open decisions above are not resolved.

**Stopping point (2026-09-27): Phase 11 closed for its source-supported scope. Phase 12 has not started.** The next session must begin by rereading `SUMMARY.md` §40 first, then this file, and verify the actual repository HEAD before any Phase 12 work, which needs the owner's explicit approval. *(Superseded 2026-10-01: Phase 12 is implemented; see the Phase 12 status block and `SUMMARY.md` §41.)*

## Phase 12 — Astrology Knowledge Base

Now build the knowledge layer.

Instead of dumping books into an LLM, structure knowledge into:

```
Planet
 ├── Meaning
 ├── Significance
 ├── Strength
 ├── Houses
 ├── Relationships
 └── Rules

House
 ├── Significance
 ├── Career
 ├── Marriage
 ├── Finance
 └── Education
```

Store:

- Astrology concepts
- Rules
- Interpretations
- Exceptions
- Terminology
- Domain mappings
- Traditional references

Use PostgreSQL + vector search where useful.

Deliverable: structured astrology knowledge system.

Phase 12 produces **source-backed, versioned knowledge with its provenance, and a bounded retrieval foundation**. It adds no calculation, no rule and no narration: structured facts and the Phase 6 rules decide what applies to a chart; retrieved text is never a fact about a chart. The five concepts CALCULATION, RULE, KNOWLEDGE, INTERPRETATION and NARRATION stay separate. Interpretation content is allowed in the knowledge base only when it is source-backed, provenance-tagged, profile-specific where sources differ and distinct from chart facts and from AI narration (owner decision, 2026-10-01).

Dependencies:

- Phases 4-11 (the deterministic facts and their provenance); Phase 6 (the rule YAML and the relationship tables, which knowledge references and never restates; the evidence bundle, which gains no knowledge section)
- The Phase 3 `knowledge` schema namespace and the `vector` extension (migration 0001), the Phase 2 two-store architecture (`docs/ARCHITECTURE.md` section 10)
- Phase 9 (the Tarot deck identifiers and the Shadbala profiles, referenced), Phase 11 (numerology interpretation was deferred to this phase)

Inputs: curated content files (`services/knowledge/content/`: sources, planet and house statements, terms, domain mappings, references, exceptions, the parsed Waite corpus), the Phase 6 rule files (for validation of every rule reference), and one embedding configuration. No user data of any kind.

Outputs: a sealed, versioned **knowledge version** (sources and editions, concepts, statements, terms, rule references, domain mappings, exceptions, chunks, embeddings, ingestion runs) in PostgreSQL with pgvector; a `KnowledgeBase` read interface over one sealed version; a `Retriever` returning bounded, deterministic hits with full provenance and the fixed stamp `KNOWLEDGE_TEXT_NOT_A_CHART_FACT`. Internal service interfaces only.

Methodology: `docs/ASTROLOGY_STANDARDS.md` v1.26.0 (KB-01 to KB-42). Source group: `research/ASTROLOGY_SOURCES.md` Group 25 and section 6.10.

Exclusions:

- HTTP endpoints, public APIs and final database APIs (Phase 18); AI narration and conversation (Phase 15); the final self-hosted model and any fine-tuning (Phase 14); the verification pass (Phase 16); palmistry knowledge (Phase 13)
- Any calculation, rule evaluation or change to a Phase 4-11 result; a Shadbala strength threshold (SM-11 stays closed); any strong/weak classification
- Remedies content or a remedies engine; Lal Kitab (deferred in Phase 9); Choghadiya and Gowri (deferred in Phase 10); numerology interpretation text and Pythagorean lucky numbers (no usable text); Hindi, Sanskrit and Hinglish knowledge text, Hindi renderings and any translation by the project or by an AI; a Devanagari letter table
- Translator prose of in-copyright translations (BPHS, Phaladeepika, Brihat Jataka): only short source terms, structured facts and citations are stored

Test requirements: schema and migration (reversible, constraints, triggers, vocabularies against the Python enums), ingestion (deterministic, idempotent, resumable, version identity), chunking, structured content, retrieval (filters, bounds, determinism, provenance), languages (English, Hindi, Hinglish, with explicit unsupported behaviour), privacy and chart-fact boundary, regression (Phase 6 rule files and rule-set hash, evidence-bundle fields, Tarot deck identifiers, no calculation/rule/server import of the knowledge package), and the in-memory and PostgreSQL stores compared.

Exit criteria:

- Sources and editions are recorded with reading level, copyright status and storage permission; only the permitted content is stored
- The knowledge schema, a forward-only migration, versions, sealed immutability and idempotent ingestion are implemented and verified on PostgreSQL with pgvector
- Planet and house concepts, their source-profile statements, terms, rule references, exceptions and domain mappings exist with provenance; conflicts are recorded, not resolved; unsupported pairs are `NOT_EVALUABLE`
- Chunking, the embedding-provider abstraction (with a migration path to Phase 14) and retrieval with filters are implemented; no retrieved text can become a chart fact; no user data is stored
- Earlier phases are unchanged (asserted), documentation is consistent, tests and CI pass job by job

Status (2026-10-01, owner's Phase 12 directive; details in `docs/ASTROLOGY_STANDARDS.md` v1.26.0 and `SUMMARY.md` section 41): **implemented for the source-supported scope, with the limits below.** The roadmap lists above are kept unchanged.

| Roadmap item | Outcome |
|---|---|
| Planet: Meaning, Significance, Houses, Relationships, Rules | Meaning and significance: source significations (BPHS Ch. 3, Brihat Jataka Ch. II, Phaladeepika Ch. XV) as separate profiles; houses: the mechanical inversion of the two house-karaka tables (`PROJECT_DERIVED`); relationships: referenced from the Phase 6 tables, not restated; rules: references to the existing rule files |
| Planet: Strength | Only a translator's remark and references to the two Shadbala profiles; no threshold and no classification (SM-11) |
| House: Significance | BPHS Ch. 11 v. 2-13 (all twelve), Ch. 32 v. 31-33 (six, conflicting at the 2nd), two karaka tables that differ at houses 4, 6, 9 and 10 |
| House: Career, Marriage, Finance, Education | 48 house/domain pairs recorded: six `SOURCE_SUPPORTED`, Marriage-2nd `UNRESOLVED_CONFLICT`, all others `NOT_EVALUABLE` |
| Store: concepts, rules, exceptions, terminology, traditional references | Implemented (ten exceptions, 53 source-attested terms, 53 rule references, source and edition records with locations) |
| Store: interpretations | Structured significations (all Vedic); Tarot meanings verbatim from the public-domain Waite text (78 cards); numerology interpretation deferred (no usable text) |
| Store: domain mappings | As above; a mapping is never a rule or a prediction |
| PostgreSQL + vector search where useful | Implemented: pgvector, exact search by default, HNSW partial expression index per embedding configuration on demand |

Not implemented or deferred, with the reason: Hindi and Hinglish knowledge text and cross-language retrieval quality (no Hindi source; behaviour measured, not claimed: KB-25); numerology interpretation (Cheiro and Balliett: uncorrected OCR and an uncertain Indian reprint copyright; Balliett interpretation not read); Lal Kitab, remedies, Choghadiya and Gowri (as above); Jataka Parijata and Saravali knowledge (not read for this purpose); Phaladeepika bhava-effect chapters (rule-like, left to Phase 6); a qualified Sanskrit review. **Belongs to Phase 14**: the final embedding model and its multilingual quality. **Belongs to Phase 15**: narration over retrieved knowledge. **Belongs to Phase 16**: verification of narrated claims against knowledge and facts. **Belongs to Phase 18**: HTTP endpoints, the public database API, rate limits and caching of retrieval. **Belongs to Phase 21**: Hindi and Hinglish retrieval and answer-quality evaluation.

Owner decisions still open: the final embedding model and any Hindi/Hinglish retrieval target; a Hindi source and a Sanskrit reviewer; legal clearance and a proofread text for Cheiro (and a reading of Balliett) before numerology interpretation is stored; further sources for house significations; whether remedies are ever a knowledge domain; whether Tarot meanings should be exposed to users at all (`PRODUCT_POLICIES.md`). The Phase 11 open decisions are unchanged and unresolved.

**Stopping point (2026-10-01): Phase 12 implemented for its source-supported scope. Phase 13 has not started.** The next session must begin by rereading `SUMMARY.md` section 41 first, then this file, and verify the actual repository HEAD before any Phase 13 work, which needs the owner's explicit approval.

## Phase 13 — Palm Reading & Vision Intelligence

AI Palm Reading is a locked product feature (see `features.md` §34). Build the deterministic vision/analysis pipeline that produces structured palm facts, and the palmistry rule/knowledge layer that interprets them — before any AI narration is introduced.

Pipeline:

```
User Palm Image
        ↓
Image Quality Validation
        ↓
Hand Detection / Localization
        ↓
Palm Region Extraction
        ↓
Palm Landmark / Feature Extraction
        ↓
Palm-Line / Palm Feature Analysis
        ↓
Structured Palm Facts
        ↓
Palm-Reading Rules / Knowledge
        ↓
AI Reasoning
        ↓
Verification
        ↓
Final Interpretation
```

Build:

- Image quality validation (lighting, blur, occlusion, framing)
- Hand detection / localization
- Left/right hand classification
- Palm region extraction
- Palm landmark / feature extraction
- Palm-line / palm feature analysis (a dedicated vision model/pipeline — generic hand-landmark detection alone is not palmistry interpretation)
- Structured, versioned palm-fact output
- Palmistry rules/knowledge layer (source-tagged, same discipline as the Vedic rule engine)
- The interfaces for AI narration from structured facts only (the narration itself is Phase 15; owner decision B, 2026-10-02)
- The palm evidence bundle and the claim-checkable interface that the verification pass will check (the verification pass itself is Phase 16; owner decision B, 2026-10-02)

This phase must remain consistent with the core Pandit Ji invariant:

**FACTS FLOW ONE DIRECTION; AI ONLY NARRATES.**

Palm-reading AI must not be the authoritative source of extracted measurements/facts — the vision/analysis pipeline is. The AI reasons over structured palm facts and triggered palmistry rules exactly as it reasons over structured chart facts and triggered yogas/doshas elsewhere in the product; it never infers a palm line or feature that the vision pipeline did not actually detect.

Deliverable: palm-reading vision pipeline + palmistry rule/knowledge layer + the palm evidence bundle and the interfaces for AI narration (Phase 15) and verification (Phase 16), integrated behind the same evidence-bundle/verification architecture as the rest of Pandit Ji. (Wording amended 2026-10-02 by owner decision B: the original listed "AI narration + verification" as Phase 13 deliverables although Phases 14, 15, 16 and 18 own them; `docs/ARCHITECTURE.md` §34 item 6.)

The pipeline stages "AI Reasoning", "Verification" and "Final Interpretation" above are performed by Phases 15 and 16 over the evidence bundle that this phase produces; this phase ends at the Structured Palm Facts, the Palm-Reading Rules/Knowledge and the evidence bundle.

**Phase 13 produces deterministic (reproducible within a documented numerical tolerance), provenance-backed palm facts, palmistry knowledge and rule outputs, an evaluation harness and stable contracts and interfaces.** Phase 14 supplies the self-hosted LLM only (no palm vision model). Phase 15 supplies the agent and AI narration. Phase 16 supplies verification. Phase 18 supplies upload, object storage, persistence, consent and retention infrastructure and the public API.

Final owner decision lock (2026-10-02, second directive; `research/PALM_READING.md` section 1A; standards v1.28.0 PM-25 to PM-31). **All seven decisions the research left open are resolved**: (A) the further prohibited interpretation categories are permanent: criminality, mental illness or psychiatric diagnosis, fertility, paternity, sexual conduct, ethnic or racial ranking, intellectual superiority or inferiority, moral character labelling and claims that a person is inherently good or bad, pure or impure, trustworthy or untrustworthy from palm features; never a training label; the vision pipeline may detect a physical feature for a legitimate technical reason but never turns it into one of these interpretations. (B) Phase 13 builds the rule infrastructure (schema, source-profile isolation, validation, provenance) and a deliberately small source-backed fixture set that proves the architecture, **not** the full production Western rule list; production interpretation coverage is limited to concepts actually read and source-supported in Heron-Allen, Cheiro or Benham; no invented, AI-generated or consensus rule; one source profile and one source location per rule; conflicts stay `UNRESOLVED_CONFLICT` with no winner unless a future owner decision selects one; broader coverage is a later controlled expansion by knowledge-version update. (C) The palm ruleset lives at **`services/rule-engine/palm_rules/`**, never under `services/knowledge/rules/`, with its own manifest and version, with no effect on the Phase 6 Vedic ruleset, its hash or `KV-06361d7aba28c1ce`, and with dedicated isolation tests; no alternative location remains. (D) Implementation does not wait for every chapter: only source-supported concepts are used; thumb, fingers, nails, unread mounts, unread signs and other unread minor features stay `NOT_READ` / `NOT_EVALUABLE` and are never used for production interpretation; a source coverage manifest makes this machine-checkable. (E) Indian Hasta Samudrika is not part of Phase 13: status `RESEARCH_PENDING`, no production interpretation; the extension points `PALM_WESTERN` (implemented) and `PALM_INDIAN_HASTA_SAMUDRIKA` (reserved, not implemented) exist by name. (F) Dataset governance: no user image is silently added to training or evaluation data; adults only; both hands; diverse devices, lighting, backgrounds, hand sizes, palm shapes, resolutions, orientations and occlusion; no mandatory skin-tone labels; privacy-preserving fairness evaluation; contributor-independent train, validation and test splits; annotation guidelines, two independent annotators where practical with adjudication, a provenance manifest, content hashes, a dataset version and an annotation version; no dataset in git; no assumption that a public palmistry dataset is suitable. (G) Reproducibility tolerances are `CALIBRATION_REQUIRED`: the framework is built, the numbers are measured later and versioned, and no bit-for-bit claim is made for a learned component unless demonstrated. The legal items (whether palm images are personal data in the relevant context, legal basis and notice and consent, derived palm facts, retention and deletion, audit logging versus deletion, the Third Schedule and other DPDP provisions, dataset consent withdrawal after training, minors, further regulatory obligations, training-data consent and reuse) remain production-launch gates, not resolved; Phase 13 implementation may proceed on synthetic, fixture or internal appropriately governed data.

Methodology and decisions (2026-10-02): `docs/ASTROLOGY_STANDARDS.md` v1.27.0 (PM-01 to PM-24) and v1.28.0 (PM-25 to PM-31); research `research/PALM_READING.md`; sources `research/ASTROLOGY_SOURCES.md` Group 26 and section 6.11; component `services/palm-vision` (`docs/ARCHITECTURE.md` §35, ADR-008). Owner decisions: A the component `services/palm-vision`; B the phase boundaries above; C palm rules in the rule engine under a completely separate palm ruleset root that never touches the Phase 6 Vedic ruleset or its hash; D Western chirology first, Indian Hasta Samudrika a separate future profile, never merged; E sources read (Heron-Allen, Cheiro, Benham, each only as far as the research records); F a purpose-built consented internal dataset for production training and evaluation, public datasets for research and baselines only after licence and provenance verification; G minors excluded until counsel clears the workflow; H training on user images off by default; I skin-tone fairness evaluated without unjustified personal labels; J no medical diagnosis, disease, death or lifespan prediction; K reproducibility within a documented numerical tolerance; L palmistry knowledge is a new knowledge version and `KV-06361d7aba28c1ce` stays valid; M legal counsel remains a production launch gate.

Dependencies:

- Phases 4-12 (the fact, rule, evidence and knowledge patterns; Phase 6 for the rule engine and evidence-bundle conventions, which stay unchanged; Phase 12 for the sealed, versioned knowledge service and its provenance model); the Phase 3 `knowledge` schema and migration chain (0001, 0002); `packages/contracts` and `packages/shared`
- No dependency on Phases 14, 15, 16 or 18: the model, agent, verifier, upload and storage are not needed to build or test this phase (a later phase consumes its interfaces)
- External, before the model can be trained or evaluated: the consented internal dataset (decision F) and counsel's clearance for any collection (decisions G, M); the research, sources and owner reviews recorded in the standards

Inputs: an image reference and the image bytes supplied by tests, fixtures or an evaluation manifest (never live user data in this phase); curated palm knowledge content with provenance (`research/ASTROLOGY_SOURCES.md` Group 26); the palm ruleset YAML; a pinned model artifact set (hand and landmark models, the palm-line model) with recorded hashes and licences; the versioned `quality_config`; the evaluation dataset manifest. No upload, no user account, no stored user image.

Outputs: `services/palm-vision` (image quality, hand detection, hand-side classification, palm region, landmarks, the palm-line/feature model, the structured versioned `PalmFactSet` with provenance and artifact identities); the palm contracts in `packages/contracts` (`PalmFactSet`, `PalmFact`, `PalmRuleEvaluation`, `PalmEvidenceBundle`); palmistry knowledge for the first Western profile as a **new** sealed knowledge version (with a forward-only migration for the vocabulary extension); the palm ruleset at `services/rule-engine/palm_rules/` (own manifest and version; a small source-backed fixture set, not the full production list) with its rule-engine extension and evaluation; the source coverage manifest; the `PalmEvidenceBundle`; the evaluation harness and a versioned evaluation report; the interface documentation for Phases 15 and 16. Internal service interfaces only.

Technologies and components: OpenCV, NumPy, MediaPipe (hand detection, landmarks, side) and PyTorch (the palm-line/feature model), as locked in `TECH_STACK.md`; MediaPipe landmarks are a localisation tool and are never presented as palmistry; PostgreSQL and the Phase 12 knowledge service for knowledge; the rule engine for rules; S3-compatible storage by reference only.

Exclusions:

- The LLM (Phase 14); the agent, AI reasoning and AI narration (Phase 15); the verification pass (Phase 16); upload and object-storage APIs, signed URLs, public endpoints, user-data persistence, consent and retention infrastructure (Phase 18); capture guidance in the apps (Phase 19); large-scale and field validation (Phase 21)
- Any change to a Phase 4-12 result, the Phase 6 rule files, the Phase 6 rule-set hash, the evidence-bundle fields or the Phase 12 knowledge version `KV-06361d7aba28c1ce`
- Medical diagnosis, disease prediction, death prediction and lifespan prediction (decision J); and, permanently, the further categories of the final decision A (criminality, mental illness or psychiatric diagnosis, fertility, paternity, sexual conduct, ethnic or racial ranking, intellectual superiority or inferiority, moral character labelling, inherent good or bad, pure or impure, trustworthy or untrustworthy claims): no rule, statement, chunk or label may express them
- The full production Western rule list (only the rule infrastructure and a small source-backed fixture set are in scope); any rule for a concept that has not been read; any consensus rule; any AI-generated palmistry rule
- Indian Hasta Samudrika / Samudrika Shastra (`RESEARCH_PENDING`, no production interpretation; `PALM_INDIAN_HASTA_SAMUDRIKA` is a reserved name only)
- Indian Hasta Samudrika (a separate future profile), Lal Kitab, remedies, face reading, Hindi, Sanskrit and Hinglish palmistry text and any translation by the project or by an AI
- Minors: no collection, no analysis (decision G); training on user images (decision H); any claim that palm images are or are not biometric or sensitive personal data
- Hand-shape classes, nail and colour readings, mount "development", event dating on lines, semantic minor lines and the signs (standards PM-08) until a later standards version includes them

Test requirements: the palm-fact contract (canonical JSON, fixed-point coordinates, hashes, derivation chain, OBSERVED/DERIVED/INTERPRETED separation); reproducibility within the documented tolerance on pinned artifacts across platforms (the tolerance is set from measured runs and then asserted); the image-quality gate (accept, retry, reject, reason codes, no hardcoded production threshold); each vision stage on fixtures; hand side including `UNDETERMINED`; the rule engine's palm ruleset (loads in isolation, never loads into the Vedic engine); privacy (no pixels, landmarks or geometry in logs or evidence; image referenced by id); the evidence bundle and the claim-checkable interface; the prohibited-reading filter (every category of standards PM-13 and PM-25 rejected in rules, statements and chunks, and never a label); the source coverage manifest validation (an unread, unsupported or excluded concept cannot back a rule; one source profile and one location per rule); the palm ruleset isolation tests at `services/rule-engine/palm_rules/` (Phase 6 hash and `KV-06361d7aba28c1ce` unchanged, disjoint rule-id namespaces, no cross-loading, a palm file under `services/knowledge/rules/` fails); knowledge (the new version, provenance, conflicts preserved, `NOT_EVALUABLE`, the migration forward and back); dataset-driven evaluation with precision, recall, IoU or Dice, landmark error, calibration and subgroup metrics (not simple assert-equal); and regression: the Phase 6 rule files and rule-set hash, the evidence-bundle fields, the Phase 9-11 results, the Phase 12 snapshot `KV-06361d7aba28c1ce` for the Phase 12 content, the migration chain, and the package import boundaries (no calculation, rule, knowledge, agent or verification package imports `palm-vision` and it imports none of them).

Exit criteria:

- The methodology is locked by the owner in the standards, the sources and conflicts are recorded, the palm-fact contract and the evidence bundle are stable and versioned, and the small source-backed rule fixture set (not a full rule list) has every rule traceable to one source profile and one source location recorded as read in the coverage manifest
- `services/palm-vision` produces the structured `PalmFactSet` end to end on the evaluation set with the quality gate in front of line analysis; every fact carries provenance and artifact identities; no interpretation is emitted by the vision model
- The palm ruleset and the new knowledge version exist with provenance; conflicts are recorded, not resolved; unsupported or prohibited readings are not stored or implemented; unsupported pairs are `NOT_EVALUABLE`
- A versioned evaluation report with subgroup metrics exists for the pinned artifacts and the dataset manifest; engineering acceptance thresholds are recorded; the production gate is the owner's decision
- Earlier phases are unchanged (asserted), documentation is consistent, tests and CI pass job by job
- Counsel clearance and the consented dataset are production launch gates, not exit criteria of the engineering work, and are reported as open

Documentation: standards (the PM section and its changelog), the source registry (Group 26 and the profile IDs), `research/PALM_READING.md`, `docs/ARCHITECTURE.md` (§35, the contract table, the changelog of the known contradictions), ADR-008, `datasets/README.md`, the `services/palm-vision` README, `CONTRIBUTING.md` and `TECH_STACK.md` where they list components, and a `SUMMARY.md` handoff section.

Git/CI: owner identity `iamankoo <aniketraj00384@gmail.com>`, no AI attribution; commits scoped to this phase; a dedicated CI job for `services/palm-vision` (heavy dependencies only there, no model weights in git, an optional-model pattern like the Phase 12 model tests), the knowledge PostgreSQL job extended for the new migration, the existing jobs unchanged; after every push, CI is inspected job by job (never from a workflow-level green alone) and the optional-model coverage gap is reported.

Status (2026-10-02, owner decisions A to M): **research and methodology locked; implementation not started.** The roadmap lists above are kept unchanged except the two Build bullets and the Deliverable amended for decision B. Recorded: the sources read and their limits (Heron-Allen, Cheiro and Benham, each only partly read; the Samudrika tradition not read); the taxonomy support statuses; ten source conflicts; the categories excluded by policy; the palm-fact contract; the quality framework with no hardcoded threshold; the dataset methodology and the review of public datasets (none suitable for production); the privacy and legal status (the DPDP Act and Rules read contain no biometric or sensitive category; classification of palm images unresolved; counsel gate); the evaluation methodology. **No owner decision remains open** (the seven that were open are resolved by the final owner decision lock above). What remains is not a decision: the production-launch legal gates, the consented dataset, and the quantities that are measured (reproducibility tolerances, quality thresholds, dataset stratum sizes, evaluation acceptance thresholds), all `CALIBRATION_REQUIRED`. Future controlled expansions (reading more chapters and expanding rule coverage by knowledge-version update; the Indian profile) each need their own owner approval when wanted.

Implementation status (2026-10-03; `SUMMARY.md` §44). The infrastructure is built; the trained model, the dataset, the calibration and the legal clearance are not.

- **IMPLEMENTED**: the palm contracts (`packages/contracts` 0.2.0: `PalmFact`, `PalmFactSet`, `PalmRuleEvaluation`, `PalmEvidenceBundle`, canonical JSON with fixed-point integers and basis points, SHA-256 identities, provenance, the prohibited-interpretation policy, the source-coverage vocabulary); `services/palm-vision` 0.1.0 (image input, quality gate with ACCEPT/RETRY/REJECT, hand detection and side abstraction with `UNDETERMINED`, the PCF-1 palm frame and region, the 21-landmark abstraction, the line/feature stage with an explicit `MODEL_UNAVAILABLE` state, fact derivation, artifact policy, reproducibility comparison, the evaluation harness and metrics on a synthetic set); migration `0003_palm_knowledge_vocabulary` (additive) and the separate palm knowledge version `KV-a21c2c040abe9663` with the machine-checked source coverage manifest; `services/rule-engine/palm_rules/` (manifest, schema, tag vocabulary, conflicts file, six fixture rules) with its loader and evaluator and the isolation tests; the integration test and the CI jobs.
- **PARTIALLY IMPLEMENTED**: the palm-line stage (the interface, preprocessing and a baseline marked EXPERIMENTAL exist; no production line model); the Western knowledge (only the concepts recorded as read: Heron-Allen, Cheiro and Benham each only partly read).
- **CALIBRATION_REQUIRED**: every quality threshold, the reproducibility tolerances, the landmark and region tolerances, the evaluation acceptance thresholds (the default configuration never returns ACCEPT).
- **MODEL_REQUIRED**: the trained and validated palm-line/feature model; a hand and landmark model artifact with recorded hash and licence; line-role assignment, the Triangle and the Quadrangle as facts, and the mounts that need them are `NOT_EVALUABLE` until then. No accuracy figure exists and none is claimed.
- **DATASET_REQUIRED**: the consented adult dataset (both hands, device, lighting, resolution, orientation, occlusion, hand-size and palm-shape diversity, contributor-level splits). No dataset, image or weight is in git; the evaluation metrics were exercised only on a synthetic plumbing set and say nothing about real accuracy.
- **LEGAL_GATE** (not resolved, not implemented): classification of palm images, legal basis and notice, derived facts, retention and deletion, consent withdrawal, minors, training reuse. Production launch is blocked until counsel completes the review.
- **FUTURE_PHASE**: the LLM (14), the agent and narration (15), verification (16), upload, storage, consent and retention workflows and the public API (18), capture guidance (19), field validation (21); the Indian Hasta Samudrika profile (`RESEARCH_PENDING`).

**Stopping point (2026-10-03): Phase 13 is implemented as infrastructure and contracts, with no trained palm-line model, no dataset and no calibrated threshold.** Phase 14 has not started. The next session reads `SUMMARY.md` §44, this block and `CONTRIBUTING.md`, verifies HEAD and CI job by job, and begins Phase 14 only on the owner's explicit instruction.

## Phase 14 — Self-Hosted AI Model

Now build Pandit Ji's AI brain.

Evaluate open-weight models against:

- Hindi
- Hinglish
- English
- Reasoning
- Long context
- Structured output
- Tool calling
- Astrology terminology

Potential candidates:

- Qwen
- Llama
- Mistral
- Other suitable models

Don't blindly fine-tune immediately.

First establish:

```
Base LLM
   ↓
System instructions
   ↓
Tools
   ↓
Astrology engine
   ↓
Knowledge retrieval
   ↓
Reasoning
```

Deliverable: self-hosted AI inference service.

## Phase 15 — Pandit Ji Agent

This is where the project becomes an actual AI agent.

The agent should decide:

"What information do I need to answer this question?"

Example:

User: "Will my career improve next year?"

Agent:

```
Intent = Career
        ↓
Need D1
Need D10
Need 10th house
Need 10th lord
Need Dasha
Need next-year transits
        ↓
Execute tools
        ↓
Collect evidence
        ↓
Reason
        ↓
Generate response
```

Build:

- Intent detection
- Planning
- Tool selection
- Tool execution
- Context management
- Memory
- Multi-step reasoning
- Error recovery

Deliverable: Pandit Ji Agent v1.

## Phase 16 — Evidence & Verification Engine

This phase is critical.

Before Pandit Ji answers:

```
AI Answer
    ↓
Verifier
    ↓
Are chart facts correct?
Are calculations correct?
Are rules actually triggered?
Any contradictions?
Any unsupported claims?
    ↓
Approve / Regenerate
```

Build:

- Calculation verification
- Rule verification
- Evidence tracking
- Contradiction detection
- Hallucination detection
- Unsupported-claim detection
- Confidence/uncertainty representation

Deliverable: verified-response pipeline.

## Phase 17 — Life-Domain Intelligence

Now build specialized analysis across the complete life spectrum.

Domains:

- Birth
- Personality
- Childhood
- School
- College
- Subjects
- Education
- Career
- Job
- Corporate life
- Business
- Startup
- Finance
- Wealth
- Love
- GF/BF
- Relationship
- Marriage
- Spouse
- Family
- Children
- Travel
- Foreign travel
- Foreign education
- Foreign settlement
- Personal life
- Spirituality

Each domain gets its own:

```
Domain
 ↓
Relevant charts
 ↓
Relevant planets
 ↓
Relevant houses
 ↓
Relevant dashas
 ↓
Relevant transits
 ↓
Rules
 ↓
Interpretation
```

Deliverable: complete domain reasoning system.

## Phase 18 — Backend Platform

Now expose everything through production APIs.

Build:

- Authentication
- User management
- Birth profiles
- Chart APIs
- Dasha APIs
- Transit APIs
- AI chat API
- Compatibility API
- Panchang API
- Numerology API
- Reports API
- Voice API
- Memory API
- Notification API

Add:

- Rate limiting
- Caching
- Background jobs
- WebSockets
- Logging
- Monitoring
- API versioning

Deliverable: production backend.

## Phase 19 — Pandit Ji Web + Mobile App

Now build the actual product experience.

```
Home
Good Morning 👋

Your Today
─────────────
🌙 Moon
🪐 Transit
📅 Panchang

Ask Pandit Ji
[ 🎙️ Talk ]

Career
Love
Marriage
Finance
Education
Travel
```

Main modules:

- Onboarding
- Birth details
- Kundli
- AI Chat
- Dasha
- Transits
- Life timeline
- Career
- Love
- Marriage
- Compatibility
- Panchang
- Muhurta
- Reports
- Numerology
- Remedies
- Profile
- Memory

Deliverable: polished mobile + web applications.

## Phase 20 — Voice + Personalization

Give Pandit Ji a natural conversational interface.

```
User speaks
    ↓
STT
    ↓
Pandit Ji Agent
    ↓
Astrology Tools
    ↓
Reasoning
    ↓
Response
    ↓
TTS
```

Support:

- Hindi
- Hinglish
- English

Add:

- Voice conversations
- Personal memory
- Saved charts
- Previous discussions
- Personalized recommendations
- Daily insights
- Important-period notifications

Deliverable: Pandit Ji Voice + Personal AI.

## Phase 21 — Validation, Backtesting & Production Launch

This is the final and arguably most important phase.

### Calculation validation

Test thousands of:

- Birth dates
- Birth times
- Locations
- Timezones
- Historical dates

### Rule validation

Test:

```
Input chart
     ↓
Expected rule activation
     ↓
Actual rule activation
```

### AI evaluation

Measure:

- Astrology factual accuracy
- Chart-data accuracy
- Rule adherence
- Hallucination rate
- Hindi quality
- Hinglish quality
- Reasoning consistency
- Follow-up consistency

### Predictive evaluation

If Pandit Ji makes future-oriented astrological claims, create a historical backtesting framework:

```
Historical birth data
       ↓
Pandit Ji prediction
       ↓
Known real-world outcome
       ↓
Compare
       ↓
Metrics
```

Do not assume 100% prediction accuracy. Measure it.

### Security

- Penetration testing
- Authentication testing
- Data encryption
- Privacy testing
- API security
- Abuse prevention

### Production

- Cloud infrastructure
- GPU inference
- Database
- Redis
- Monitoring
- Backups
- CI/CD
- Scaling
- Crash recovery
- Cost optimization

Deliverable: Pandit Ji production release.

## 🧠 The Complete Pandit Ji Stack

```
                         PANDIT JI
                            │
                    ┌───────▼────────┐
                    │  User Interface │
                    │ Flutter / Web   │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │ Voice / Chat    │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │ AI AGENT        │
                    │ Planner         │
                    │ Memory         │
                    │ Tool Calling   │
                    └───────┬────────┘
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
       Astrology Engine  Knowledge      Verification
              │             │              │
       ┌──────┼──────┐      │              │
       ▼      ▼      ▼      ▼              ▼
      D1     D9     D10   Rules         Evidence
      Dasha Transit Yoga  Knowledge     Validator
              │             │              │
              └─────────────┼──────────────┘
                            ▼
                     SELF-HOSTED LLM
                            │
                            ▼
                    FINAL RESPONSE
```
