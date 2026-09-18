# Pandit Ji Astrology Standards

Status: **LOCKED canonical location** — `docs/ASTROLOGY_STANDARDS.md` is the single, authoritative document for calculation standards, Vedic defaults, ayanamsa, zodiac, house systems, ephemeris configuration, astronomical calculation requirements, astrology methodology separation, interpretation standards, reproducibility, uncertainty, and versioning. There is no separate `docs/calculation-standards.md` — any earlier reference to that filename referred to this document and should be treated as resolved in favor of this one.

Version: 1.1.0 (Phase 1 completion — see §Versioning at the end of this document for the change log).

This document defines **standards and methodology contracts**, not implementations. Every section below states what a later phase's engine must compute and how, not the engine itself. Each section names the `Phases.md` phase responsible for the actual implementation.

## Core rule
**Facts flow one direction; AI only narrates.**

The AI must never independently calculate planetary positions, houses, ascendant, nakshatra/pada, divisional charts, dashas, transits, yogas/doshas, Panchang timings, Muhurta windows, numerology numbers, or compatibility scores.

## AI scope boundary

- **Self-hosted requirement**: Pandit Ji's core astrology reasoning (chart interpretation, prediction, agent planning, personalization, knowledge reasoning, core chatbot responses) must not depend on external hosted proprietary LLM APIs. See `research/AI_MODELS.md` and `docs/ARCHITECTURE.md` §7's `LLMProvider` abstraction for the technical mechanism; this document fixes it as a standing product requirement, not merely an implementation preference.
- **Fact-vs-narration boundary**: the AI consumes structured facts and evidence bundles produced by the calculation engine, rule engine, and knowledge base (defined in this document and `docs/ARCHITECTURE.md`); it narrates and explains them, and never originates them. This is the same invariant as the Core rule above, restated as an explicit AI-scope requirement per Phase 1 exit criteria.

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
- Note: the sub-lord subdivision arithmetic must be validated against an authoritative KP reference before implementation (see `docs/ARCHITECTURE.md` §14)

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
- Chinese astrology, Tarot, Vastu/Feng Shui, Horary: system identity acknowledged as in-scope per `features.md`; each requires its own dedicated methodology definition before implementation, following the same pattern as the systems above (system identity, basis, core assumptions, source/tradition separation, non-mixing rule); detailed standards for these are deferred to the phase that implements them (Phase 9 for KP/Lal Kitab/Nadi/Western/Chinese, Phase 16 for cross-domain analysis touching Vastu) and must be written before that phase begins, following this document's format
- Palmistry: see §Palmistry below (implemented as part of the palm-reading pipeline; see `docs/ARCHITECTURE.md` §17 item 3 for the still-open scope/priority question on when this is built)

## Divisional charts (Vargas)

Defines the standard and contract that **Phase 5 (Birth Chart / Kundli Engine)** implements — not implemented in Phase 1.

- **D1 / Rashi chart**: the base birth chart — each planet's sidereal longitude placed directly into its zodiac sign and house, using the Default Vedic profile's ayanamsa/house baseline. All other divisional charts are derived from this same set of longitudes; D1 is the foundation, not a division.
- **D9 / Navamsa**: each of the 12 signs is divided into 9 equal parts of 3°20′ each; a planet's Navamsa sign is determined by classical Parashari rule based on which 3°20′ segment its longitude falls into and the modality (movable/fixed/dual) of its D1 sign, per the standard starting-point convention. Represents marriage, spouse, dharma, and the inner strength of D1 placements.
- **Divisional-chart framework**: Pandit Ji's locked varga set is the classical Shodashvarga (16 principal divisional charts): D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D27, D30, D40, D45, D60. Each varga is derived deterministically from the same D1 sidereal longitudes via its classical division formula — no varga is independently observed or separately calculated from the ephemeris.
- **What each chart represents** (canonical significations, to be expanded per-varga during Phase 5): D1 = self/body/overall life; D2 (Hora) = wealth; D3 (Drekkana) = siblings/courage; D4 (Chaturthamsa) = property/home/fortune; D7 (Saptamsa) = children/progeny; D9 (Navamsa) = marriage/spouse/dharma; D10 (Dasamsa) = career/profession; D12 (Dwadasamsa) = parents; D16 (Shodasamsa) = vehicles/general happiness; D20 (Vimsamsa) = spiritual pursuits; D24 (Chaturvimsamsa) = education/learning; D27 (Nakshatramsa/Bhamsa) = strengths/weaknesses; D30 (Trimsamsa) = misfortunes/challenges; D40 (Khavedamsa) = auspicious/inauspicious effects; D45 (Akshavedamsa) = general life conduct; D60 (Shashtiamsa) = overall past-karma/fine-grained life analysis.
- **Chart-specific applicability**: which varga is authoritative for which life-domain question is determined by the domain-to-varga mapping used in `docs/ARCHITECTURE.md` §7's Astrology Planner (e.g., a marriage question requires D1 + D9; a career question requires D1 + D10). This mapping is finalized during Phase 5/Phase 16, not Phase 1.
- **Versioning/configuration**: the varga division scheme (classical Parashari, as fixed above) is part of `calculation_config`; if an alternate varga scheme is ever supported, it must be a distinct, explicit configuration value, never silently substituted.

## Vimshottari Dasha

Defines the standard and contract that **Phase 7 (Dasha & Timing Engine)** implements — not implemented in Phase 1.

- **Total cycle**: 120 years, distributed across nine planetary lords in a fixed sequence.
- **Nine planetary lords and fixed durations** (years): Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17 (sums to 120).
- **Sequence**: Ketu → Venus → Sun → Moon → Mars → Rahu → Jupiter → Saturn → Mercury → (cycles back to Ketu).
- **Starting Mahadasha lord**: the lord of the nakshatra occupied by the natal Moon at birth (see §Nakshatra standards for the nakshatra-lord sequence).
- **Balance of the first Mahadasha**: determined by how far the Moon has progressed through that nakshatra at the birth instant — the remaining fraction of the nakshatra's 13°20′ span, converted to time as that same fraction of the starting lord's full dasha-year duration.
- **Hierarchy**: Mahadasha → Antardasha → Pratyantar (and, if later required, Sookshma) are nested applications of the same nine-lord sequence and proportional-duration logic, each level starting from its parent period's own lord and subdividing the parent's duration across the nine lords in the same fixed sequence and proportion.
- **Exact timestamps and boundary conditions**: all dasha transitions are computed as precise moments (date and time), not whole-day boundaries, derived from the birth instant plus cumulative duration — boundary dates must be computed to at least day-level precision, with the exact moment retained internally for reproducibility.
- **Reproducibility**: identical birth data and calculation configuration must reproduce an identical Mahadasha/Antardasha/Pratyantar timeline, byte-for-byte, every time.

## Nakshatra standards

Defines the standard and contract that **Phase 5** (as part of the Kundli engine) implements — not implemented in Phase 1.

- **27 Nakshatras** spanning the full 360° sidereal zodiac.
- **Zodiacal span**: 13°20′ (360° ÷ 27) per Nakshatra.
- **Padas**: four padas per Nakshatra, each 3°20′ (13°20′ ÷ 4).
- **Planetary lord sequence**: the same nine Vimshottari lords (Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury), repeating three times across the 27 Nakshatras (9 × 3 = 27).
- **Boundary handling**: Nakshatra and pada boundaries are computed from the Moon's (or other relevant planet's) exact sidereal longitude after ayanamsa correction, at full internal precision (degrees/minutes/seconds). A position falling essentially exactly on a boundary must be flagged for review rather than silently rounded to one side.
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
- Conflicting rules (an explicit list of other rule IDs this rule is known to contradict, so the evidence-bundle contradiction analysis in `docs/ARCHITECTURE.md` §6 can surface both sides)

**Do NOT invent a universal list of Yogas/Doshas where traditions disagree.** Where Parashari, Jaimini, Lal Kitab, KP, or other schools define a given Yoga/Dosha differently, each school's version is recorded as its own tagged rule under its own source/tradition, and the evidence bundle presents both rather than the system silently picking a winner.

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

## Data & privacy principles

Product-level data/privacy principles (data minimization, purpose limitation, consent/notice, birth-data/location-data/conversation-data/palm-image handling, retention/deletion, access control, encryption, auditability, personalization-vs-training-data separation, third-party/vendor restrictions, user export/deletion, minor/child safeguards) are defined in `PRODUCT_POLICIES.md` §"Data & Privacy Principles" — this document cross-references rather than duplicates that content, per the source-of-truth hierarchy (`SOURCE_OF_TRUTH.md`). `LEGAL_REGULATIONS.md` remains the detailed legal/compliance baseline underneath both.

## Prediction language policy

- Clearly distinguish three claim classes at all times (matching `SOURCE_OF_TRUTH.md`'s claim-class taxonomy): **calculation facts** (deterministically computed), **traditional interpretations** (what a named tradition/school teaches, per §Yoga/Dosha standards' source-tagging), and **empirical/scientific evidence** (measured, backtested performance — see `docs/ARCHITECTURE.md` §9 and `research/BACKTESTING.md`). Never blur these into one undifferentiated claim.
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
Image quality, hand side, visible structures and uncertainty must be separated from interpretation. No medical diagnosis from palm images. (See `docs/ARCHITECTURE.md` §17 item 3 for the open scope/priority question on when the full palm-reading pipeline is built; this standard applies whenever it is.)

## Versioning
Changes to calculation standards require versioning, changelog, regression tests and explicit approval. A standards change record must include: version number, date, change description, reason, affected calculations, affected interpretations, regression-test requirement, and approval status. Historical calculation behavior must never be silently altered — a standards version change is itself a new, distinct, recorded configuration state.

### Change log
- **v1.0.0** (Pre-Phase-1 Foundation package): initial draft — Core rule, Default Vedic profile, Supported systems (list only), Interpretation, Uncertainty, Reproducibility, Health, Remedies, Palmistry, Versioning.
- **v1.1.0** (Phase 1 completion): added AI scope boundary; expanded Time/Location standards; expanded Supported systems into full per-system methodology standards (Vedic, Western/Tropical, KP, Lal Kitab, Nadi, with Lal Kitab/Nadi explicitly marked provisional pending research validation); added Divisional charts (Vargas), Vimshottari Dasha, Nakshatra standards, Yoga/Dosha standards, Panchang/Muhurta standards, and Numerology standards sections; added Data & privacy principles (cross-reference to `PRODUCT_POLICIES.md`); added Prediction language policy; added Birth-time uncertainty section. Approval status: locked per project-owner direction to close all 13 `Phases.md` Phase 1 content requirements.

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
