🪔 Pandit Ji — 20-Phase Master Development Plan

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

Deliverable: versioned astrology rule engine.

## Phase 7 — Dasha & Timing Engine

Build the temporal intelligence.

Implement:

- Vimshottari Dasha
- Mahadasha
- Antardasha
- Pratyantar
- Dasha start/end
- Current Dasha
- Future Dasha
- Historical Dasha
- Dasha transitions

Then connect Dasha with:

- Houses
- Lords
- Planets
- Yogas
- Career
- Marriage
- Education
- Finance
- Relationships

Deliverable: complete life-period timeline.

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
- Sade Sati
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

Deliverable: dynamic transit engine.

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
- Bhakoot
- Nadi
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

## Phase 13 — Self-Hosted AI Model

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

## Phase 14 — Pandit Ji Agent

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

## Phase 15 — Evidence & Verification Engine

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

## Phase 16 — Life-Domain Intelligence

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

## Phase 17 — Backend Platform

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

## Phase 18 — Pandit Ji Web + Mobile App

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

## Phase 19 — Voice + Personalization

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

## Phase 20 — Validation, Backtesting & Production Launch

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
