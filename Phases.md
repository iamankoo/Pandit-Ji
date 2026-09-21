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

## Phase 11 — Numerology + Compatibility

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
