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
- AI narration from structured facts only
- Verification pass before final interpretation is released

This phase must remain consistent with the core Pandit Ji invariant:

**FACTS FLOW ONE DIRECTION; AI ONLY NARRATES.**

Palm-reading AI must not be the authoritative source of extracted measurements/facts — the vision/analysis pipeline is. The AI reasons over structured palm facts and triggered palmistry rules exactly as it reasons over structured chart facts and triggered yogas/doshas elsewhere in the product; it never infers a palm line or feature that the vision pipeline did not actually detect.

Deliverable: palm-reading vision pipeline + palmistry rule/knowledge layer + AI narration + verification, integrated behind the same evidence-bundle/verification architecture as the rest of Pandit Ji.

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
