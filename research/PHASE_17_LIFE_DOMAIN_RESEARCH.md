# Phase 17 — Life-Domain Intelligence: Research and Architecture Lock

Status: **RESEARCH AND ARCHITECTURE LOCK (2026-10-06). NOT an implementation. Phase 17 has NOT started. This record is NOT owner-approved**: every item marked `OWNER_DECISION_REQUIRED` waits for the owner. Companion: `research/PHASE_17_DOMAIN_MATRIX.md` (matrices). Sources are registered only in `research/ASTROLOGY_SOURCES.md` Group 27 (the single canonical registry; no second registry was created). Methodology: `docs/ASTROLOGY_STANDARDS.md` v1.29.0 LD-01 to LD-24. Architecture: `docs/ARCHITECTURE.md` section 39 and `docs/architecture/adr/ADR-012-life-domain-intelligence.md` (status Proposed).

Nothing here is legal advice, and nothing here states that astrology predicts anything. A source-backed mapping means "a named classical text says it", not "it is true".

## 1. What the source of truth actually specifies for Phase 17

`Phases.md` Phase 17 (read in full) consists of: one sentence of objective ("build specialized analysis across the complete life spectrum"), a list of 27 domains, one seven-step chain (Domain, relevant charts, planets, houses, dashas, transits, rules, interpretation) and the deliverable "complete domain reasoning system". It specifies **no** inputs, outputs, contracts, services, reuse, exclusions, tests, documentation or exit criteria: every one of those is "Not specified in current source of truth". Everything else comes from other documents:

- `features.md` section 11 (life analysis), 12 (career and education), 13 (love, relationship and marriage), 20 (reports) and the product principle that interpretation must record supporting and conflicting factors.
- `docs/ARCHITECTURE.md` section 8: specialist modes are "prompt templates + evidence-assembly presets... configuration within `agent`, not new architecture".
- `docs/ASTROLOGY_STANDARDS.md` section "Divisional charts": the domain-to-varga mapping "is finalized during Phase 5/Phase 17". No later record finalized it (searched). Phase 17 therefore owns it.
- `Phases.md` Phase 7, 8 note that life-domain interpretation of dasha and transit facts belongs to Phase 12 and Phase 17; the Phase 15 and 16 blocks defer the dasha, transit, compatibility and knowledge adapters to Phase 18.

Corrections to the baseline audit (recorded, not hidden): (a) the audit said the ruleset had "about 219" rules; the actual loaded count is **51** (my earlier figure counted `rule_id` strings inside reading blocks); (b) the audit said the rules have "no domain axis"; in fact each rule carries a free-form `interpretation_tags.domain` list (44 rules `general`, 2 `marriage`, 5 `personality`+`status`), but there is no controlled vocabulary and no rule is tagged for most domains.

## 2. Sources actually read in this run

All texts were fetched on 2026-10-06 from archive.org into a scratch directory outside the repository (nothing was copied into the repository; copyright: only paraphrase, citation and locations are recorded). Levels use the registry vocabulary.

| Source | What was read | Level |
| --- | --- | --- |
| BPHS, R. Santhanam, Vol I (`BPHSEnglish`) | Ch. 7 v. 1-8 (use of the sixteen divisions), printed pp. 91-92 | `IMAGE-TRANSLATION` (the English; the Devanagari was seen, not read) |
| same | Ch. 11 v. 2-13 (house significations) re-read in OCR; the Phase 12 page-image check stands | `OCR-TRANSLATION` here, `IMAGE-TRANSLATION` (Phase 12) |
| same | Ch. 15 v. 1-14 (4th house, partial), Ch. 16 v. 1-32 (5th house and children), Ch. 21 v. 1-22 (10th), Ch. 22 v. 1-7 (11th), Ch. 23 v. 1-14 (12th), Ch. 37 v. 1-13 and Ch. 38 v. 1-4 (lunar and solar yogas; effects), Ch. 36 v. 3-4 and v. 37 | `OCR-TRANSLATION` |
| same | Ch. 6 v. 9 (Chaturthamsa) and a text search of Ch. 6 and 7 for "property", "landed", "real estate" (no hit) | `OCR-TRANSLATION` |
| Phaladeepika, Sastri 2nd ed. 1950 (`Phaladeepika2ndEd.1950ByVSubrahmanyaSastri`) | Adh. V sl. 1-9 (profession and livelihood), pp. 43-46; sl. 1 and sl. 9 on page images | sl. 1, 9: `IMAGE-TRANSLATION`; sl. 2-8: `OCR-TRANSLATION` |
| same | Adh. XVI sl. 1-35 (general effects of the twelve bhavas), pp. 161-175; sl. 2-8 (pp. 161-166) and sl. 31-35 (pp. 174-175) on page images | those: `IMAGE-TRANSLATION`; the rest `OCR-TRANSLATION` |
| same | Adh. X sl. 1-15 (the 7th house), Adh. XII sl. 1-5 (children), Adh. XXVII sl. 1-6 (ascetic yogas) | `OCR-TRANSLATION` (the sloka numbers in the OCR are irregular; page images not checked) |
| same | Adh. XVII (read only far enough to confirm it is death timing; **excluded by policy, not mined**) | n/a |
| Phase 12 repository records (`services/knowledge/content/houses.yaml`, `planets.yaml`, `domains.yaml`) | BPHS Ch. 11 v. 2-13, Ch. 32 v. 31-34, Ch. 3 v. 12-13; Phaladeepika XV sl. 15-17; Brihat Jataka II sl. 1 | as recorded there (page-image level, except Brihat Jataka OCR) |
| Repository: ruleset YAML (51 rules), rule-engine schema and evidence modules, agent intent and planner, contracts, astro-engine models | structure and tags | code reading |

Registry note: the Phaladeepika scan has no text layer; page positions were found by rendering (PDF page index is printed page + 34 to + 39 depending on plates).

## 3. Sources NOT obtained or NOT read (`NOT_READ`; nothing inferred from them)

BPHS Vol I Ch. 9, 12, 13, 14, 17, 18, 19, 20, 24 (the 144 bhava-lord placements), 25, 29 (bhava padas), 30 (upapada), 31, 33 (karakamsa), 34, 39 to 45; BPHS Vol II (including the dasha chapters, Ch. 46 onward); Phaladeepika Adh. VI to IX, XI, XIII to XV (other than the Phase 12 passages), XVIII to XXVI (other than those already in the registry); **Phaladeepika Adh. XIX and XX (dasha effects and the dashas of bhava lords: the key unread source for "domain-relevant dasha")**; Brihat Jataka except Ch. II sl. 1 (its domain chapters, including its house chapters, were not read); Saravali, Uttara Kalamrita, Jataka Parijata (domain chapters), Jaimini Sutras and Sripatipaddhati for domain use; any Hindi or Sanskrit-level review (none done; `SANSKRIT-LEVEL` is never claimed); any modern commentary (deliberately not used).

## 4. House methodology (research result)

The house significations of BPHS Ch. 11 v. 2-13 and the house karakas of Ch. 32 v. 34 and Phaladeepika XV sl. 17 are already in the knowledge store (Phase 12, page-image level) and are reused unchanged. This run adds source statements about **how a house's result is judged** and about which domain words appear in a house's own list:

- Direct domain terms in the house lists (verse, translator notes excluded): 1st physique, appearance, intellect, innate nature; 2nd wealth, family; 3rd brothers and sisters, journey; 4th conveyances, relatives, mother, lands, houses; 5th learning, knowledge, sons; 7th wife, travel, trade; 9th fortunes, religion, visits to shrines; 10th profession (livelihood), honour, father, living in foreign lands; 11th income, prosperity; 12th expenses.
- Derived (stated in effect chapters, not in the list): the 10th house chapter (Ch. 21) speaks of "karma" in the sense of the calling (the translator's note says so; the verse text is "work"/"calling" conditions on the 10th lord); the 12th house chapter (Ch. 23 v. 11-12) separates wandering from country to country from moving in one's own country by the condition of the 12th lord and 12th house; Phaladeepika V sl. 9 puts the "country of acquisition" in the 10th sign or the Navamsa of the 10th lord.
- No source read gives the **4th house** for education, a **house** for "love" as such, "college", "school", "startup", "investments", "childhood", "personal life", or "foreign education". Those are `NOT_EVALUABLE` (finding about the passages read, not a claim about the classical texts as a whole).
- Method of judging a house (BPHS Ch. 11 v. 14-16; Phaladeepika XV): a house prospers or suffers by its occupants, aspects, its lord's condition and the lord's relation to the 6th, 8th and 12th lords. These are D1 facts the engine already computes; this is the conditional skeleton a domain rule would use.

Conflicts (not resolved; recorded in section 12): father (10th in BPHS Ch. 11 v. 11, 9th in Phaladeepika XVI sl. 22-23; the BPHS translator's note admits both); the 2nd house for marriage (existing Phase 12 `UNRESOLVED_CONFLICT`); the karaka of the 10th.

## 5. Karaka methodology

Planet significations (BPHS Ch. 3 v. 12-13; Phaladeepika XV sl. 15-16; Brihat Jataka II sl. 1) and house karakas (BPHS Ch. 32 v. 34; Phaladeepika XV sl. 17) are in the knowledge store. Domain-relevant karakas, **only where one of those sources states them**:

| Domain concept | Planet (profile) |
| --- | --- |
| Education, learning | Mercury (Phaladeepika XV 15-16: learning; BPHS 32.34: 10th); Jupiter (knowledge: BPHS 3.12-13, Brihat Jataka II.1; Phaladeepika XV: genius, knowledge) |
| Marriage, spouse | Venus (wife: Phaladeepika XV 15-16; 7th house karaka BPHS 32.34, Phaladeepika XV.17) |
| Love | Venus ("love affairs": Phaladeepika XV 15-16) |
| Children | Jupiter (sons: Phaladeepika XV 15-16; 5th house karaka BPHS 32.34) |
| Wealth, income | Jupiter (wealth: Phaladeepika XV 15-16; 2nd and 11th house karaka) |
| Siblings | Mars (younger brothers: Phaladeepika XV 15-16; 3rd house karaka) |
| Parents | Sun (father), Moon (mother) (Phaladeepika XV 15-16) |
| Livelihood | Saturn (livelihood, servants: Phaladeepika XV 15-16); 10th-house karaka differs between BPHS (Mercury) and Phaladeepika (Jupiter, Sun, Mercury, Saturn): kept as separate profiles |
| Spirituality | no planet in a source read is stated as the karaka; Jupiter's "knowledge" is a generic signification, not a spirituality karaka (`NOT_EVALUABLE`) |

BPHS Ch. 32 v. 18-19 (stronger of Moon and Mars for the mother, translator's note in Ch. 15) and Jaimini Atmakaraka/Karakamsa (BPHS Ch. 32 and 33) were **not** read for domain use. Atmakaraka and Karakamsa facts exist in `astro-engine` (Phase 9), but a domain mapping from them is `NOT_READ`.

## 6. Varga (divisional chart) methodology

The only source read that assigns divisional charts to matters of life is **BPHS Ch. 7 v. 1-8** (image-verified, pp. 91-92): ascendant for physique; Hora for wealth; Drekkana for happiness through co-born; Chaturthamsa for fortunes; Saptamsa for sons and grandsons; Navamsa for spouse; Dasamsa for power (and position); Dvadasamsa for parents; Shodasamsa for conveyances and related happiness; Vimsamsa for worship; Chaturvimsamsa for learning; Bhamsa for strength and weakness; Trimsamsa for evil effects; Khavedamsa for auspicious and inauspicious effects; Akshavedamsa and Shashtiamsa for all indications. The translator's list in the notes repeats it ("Dasamamsa for power and position (i.e. livelihood etc.)") and gives an example (the 2nd and 4th lords in good Chaturvimsamsas for education); the example and the "i.e." are the translator's, not the verse. Phaladeepika (Adh. V) uses the **Navamsa** (not the Dasamsa) in judging livelihood: a separate profile.

Result (full table in the matrix): D1 physique, D2 wealth, D3 co-born, D7 children, D9 spouse, D10 power and position, D12 parents, D20 worship, D24 learning are `SOURCE_SUPPORTED` at their stated wording; D4 is "fortunes" only: **the standards' own statement "D4 = property/home" is NOT supported by BPHS Ch. 7 (recorded conflict, section 12) and "foreign residence" is `NOT_SUPPORTED`**; D9 "dharma" and D12 "ancestry" (standards wording) are not in the verse (`NOT_SUPPORTED` beyond "spouse" and "parents"); D16, D27, D30, D40, D45, D60 are listed by BPHS but none maps to a Phase 17 domain, so they are not used except D60/D45 "general".

Engine availability: `astro-engine` produces every divisional chart (`DivisionalChart`, `varga_scheme`), but the Phase 6 `ChartFacts` is **D1-only**: no rule can read a varga placement today. A domain analysis that uses D9, D10 and so on therefore needs an additive evidence section or fact extension (a Phase 17 requirement, not Phase 18).

## 7. Dasha methodology

**PHASE_17_DASHA_REQUIREMENTS** (what domain reasoning needs):
1. The Vimshottari Mahadasha and Antardasha (the Pratyantar level is available but nothing read requires it) with lord, UTC boundaries, status, profile ids and provenance, from Phase 7 `DashaFacts`, as an optional `DashaEvidence` section that already exists in the Phase 6 `EvidenceBundle` (`dasha_evidence.py`; no shipped rule reads it).
2. A deterministic, source-backed definition of a **domain-relevant dasha**. The only such statement read: Phaladeepika X sl. 13-14 (marriage): the dasha of the planet occupying, aspecting or owning the 7th; and Jupiter's transit trine to the sign or Navamsa of the 7th lord during that dasha. For every other domain the generalisation (occupier, aspector or owner of the domain's house) is an **analogy, not a stated rule** (`OWNER_DECISION_REQUIRED` whether to adopt it as an explicit, labelled engineering profile, as Phase 7 did for balance and year length).
3. Structural relation facts (does the dasha lord own, occupy or aspect house H; is it the karaka) computed deterministically from D1 facts (lordship, house, aspected houses). The agent must not compute them; they belong to the rule-engine side (section 13).
4. Sources needed to go further and unread: Phaladeepika Adh. XIX and XX, BPHS Vol II dasha chapters (`RESEARCH_PENDING`).
5. Birth-time dependence: a dasha fact whose `status` is not usable carries `NOT_EVALUABLE` through (the existing evidence section already refuses unusable facts).

**PHASE_18_DASHA_DEPENDENCY** (not Phase 17): the Dasha API; the agent-side tool that fetches or composes `DashaFacts` for a user (the `ASTRO_DASHA` capability adapter), as-of-date handling, caching and the user's saved birth profile. Phase 17 may only read a dasha section that is already inside a supplied bundle.

Open question for the owner (decision 4): whether Phase 17 may add the agent-side read of an already supplied bundle section (consumption, no calculation, no fetch) or must wait for Phase 18 (then Phase 17 domain results report dasha as `PHASE_18_DEPENDENCY`).

## 8. Transit methodology

**Phase 17 reasoning requirements.** Sources: Phaladeepika XVI sl. 31-35 (image-verified): the success or acquisition of a bhava is expected when the lord of the Lagna, in transit, comes to a sign trine to the sign or Navamsa occupied by the bhava lord, or to the bhava itself, or when the bhava lord transits trine to the Lagna lord's position, or when the two lords conjoin or aspect (sl. 31); when Jupiter transits trine to the sign or Navamsa of the bhava lord (sl. 32); when the karaka conjoins the lord of the Moon-sign or Lagna (sl. 31); enmity if the two lords are in the 6th/8th from each other (sl. 34); the same reckoned from the Moon (sl. 35). Phaladeepika XXVI sl. 1-8 (Moon-based favourable houses) is already in the Phase 8 standards. Required facts: the transit position of the Lagna lord, the bhava lord, the karaka and Jupiter (signs), plus the natal sign and **natal Navamsa** of the bhava lord. Phase 8 `TransitFacts` (optional bundle section `transit_evidence.py`; sign-level contacts, favourable-set membership, Vedha facts, Sade Sati; **no degree angles**) supplies the first; natal Navamsa needs the varga evidence of section 6.

Available now: transit facts as a bundle section; D1 chart facts. Missing: any rule that reads transit facts (none ships); the Navamsa-based comparison. **Phase 18 infrastructure** (not Phase 17): the Transit API, the agent tool that fetches transit facts for a date or window, windows for "next year", scheduling and notifications (Phase 20).

Everything in Phaladeepika XVII (transits of death and of relatives' death) is out of scope by policy and is not mined.

## 9. Existing ruleset: which rules can legitimately contribute (research result)

Only rules whose own source text states an effect that matches a domain, and where I read that text this run (full table in the matrix): BPHS Ch. 37 v. 6 Dhana yoga (states wealth), Ch. 37 v. 5 Adhi yoga (king, minister or army chief: position), Ch. 37 v. 7-10 Sunapha, Anapha, Duradhara (wealth, fame, intelligence: partly wealth), Ch. 38 v. 1 Vesi, Vosi, Ubhayachari (wealth, learning, fame, status), Ch. 36 v. 3-4 Gajakesari (wealth, intelligence, favour of the king), Ch. 36 v. 37 Lagnadhi (a "great person", learned in the Sastras), Ch. 37 v. 11-13 Kemadruma (reproach, lack of learning, penury), Ch. 75 Pancha Mahapurusha (personality, status: already tagged), Ch. 80 v. 47-49 and Jataka Parijata v. 34 Kuja dosha (marriage: already tagged; the two are different source profiles with a recorded conflict group). The 31 Nabhasa yogas (Ch. 35) were **not read for effect**: `NOT_EVALUABLE` for any domain beyond the existing `general` tag. No rule was assigned by name. **No rule is changed by this run.**

## 10. Domain-by-domain result

See the matrix. Of the 27 `Phases.md` domains: `SOURCE_SUPPORTED` 7 (Education, Career, Finance, Wealth, Marriage with conflicts noted, Family, Children); `PARTIALLY_SUPPORTED` 11 (Personality, Subjects, Job, Business, Love, Relationship, Spouse, Travel, Foreign travel, Foreign settlement, Spirituality); `NOT_EVALUABLE` 9 (Birth, Childhood, School, College, Corporate life, Startup, GF/BF, Foreign education, Personal life). No domain was forced to be supported. Marriage, Children and Spouse carry source content that collides with policy (section 11) and are gated. The `features.md` additions are Parents (`PARTIALLY_SUPPORTED`, conflict DC-01), Siblings (`SOURCE_SUPPORTED`), Income (`SOURCE_SUPPORTED`), Higher education and Entrepreneurship (`NOT_EVALUABLE`), Investments (`NOT_EVALUABLE`), Major life transitions (`NOT_EVALUABLE`), General life patterns (`PARTIALLY_SUPPORTED`: D1 and the all-indications vargas), Health (excluded, section 11).

## 11. Sensitive domains and policy (gaps; nothing decided here)

Existing policy, as written: `PRODUCT_POLICIES.md` (no guaranteed outcomes, no fear-based claims, professional-advice framing for health, finance, legal, relationships, pregnancy, death; minors: no sexualised readings, "age-appropriate controls to relationship/marriage features"); the Phase 13 palmistry prohibitions (medical, disease, death, lifespan, criminality, mental illness, **fertility, paternity**, sexual conduct, ethnic or racial ranking, intellectual ranking, moral character, inherent good or bad); astrology: lifespan and death-timing refusal plus disclaimers (Phase 15, owner-locked). Precedent: Phase 10 MU-10 and Phase 11 CM-10 did not encode statements of effect such as death, widowhood, loss of children or poverty; CM-04 required both persons to be 18 on the date.

Gaps found (each `OWNER_DECISION_REQUIRED`, and `LEGAL_REVIEW_REQUIRED` where marked):
1. **Children and fertility.** The classical text on the 5th house (BPHS Ch. 16 v. 1-32; Phaladeepika XII) contains statements about having no offspring, losing children and **illegitimacy** ("born of other's loins", v. 14-15): the same categories (fertility, paternity) the palmistry policy prohibits, which the astrology policy does not mention. Pregnancy is named only as a high-impact topic with a disclaimer. `LEGAL_REVIEW_REQUIRED`.
2. **Minors.** Relationship, love, GF/BF, marriage, spouse and children domains for under-18 subjects: no age gate exists in the agent contract (the agent receives no birth data). Precedent CM-04 (18). Childhood, school and college necessarily involve minors; no policy exists for interpreting a minor's chart at all.
3. **Sex of the subject.** Sources state the 7th-house reading for a man's "wife" and give a mirrored rule for a woman's "husband" (Phaladeepika X sl. 7-8). The product does not collect sex (recorded in the Phase 9 closure for Chinese luck cycles). Spouse analysis that depends on it is `NOT_EVALUABLE` until the owner decides what may be collected (data minimisation).
4. **Derogatory and fear statements in the sources**: Phaladeepika V sl. 4, 8 (theft, spying, "executioner or butcher" livelihoods), XXVII sl. 5 (ascetic classes described as hypocrite, outcast, heretic), X (death of a wife), BPHS Ch. 23 v. 9 ("will go to hell"), Ch. 37 v. 11-13 (penury). They conflict with "no fear-based claims" and, by analogy, with the palmistry bans on moral-character and intellectual-ranking readings (which do not apply to astrology as written).
5. **Finance and wealth.** Disclaimer already required for finance; BPHS gives amounts (Nishkas) and ages ("in his 36th year"): numerics and ages must not be encoded; "Investments" has no source.
6. **Health.** Not in the 27 domains; features.md says health may be interpreted but never diagnosis. Sources read give disease statements (Mars "disease"; 6th "ulcers"). Not mined. Whether Health is a Phase 17 domain is an owner decision (decision 11).
7. **Lifespan and death.** The 2nd, 3rd, 7th, 8th and 12th house lists contain "death" and "longevity"; the rule tag `marriage.spouse_longevity` exists in Phase 6. Phase 17 must not surface lifespan or death timing; whether a spouse-longevity tag may be narrated is an owner decision.

## 12. Source conflicts and documentation inconsistencies (recorded, not resolved)

| Id | Conflict | Sources |
| --- | --- | --- |
| DC-01 | Father: 10th house vs 9th house | BPHS Ch. 11 v. 11 (10th; translator's note says both) vs Phaladeepika XVI sl. 22-23 (9th) |
| DC-02 | Marriage and the 2nd house | BPHS Ch. 11 v. 3 (no wife) vs Ch. 32 v. 32-33 as printed ("wife") (existing Phase 12 record) |
| DC-03 | Karaka of the 10th | BPHS Ch. 32 v. 34 (Mercury) vs Phaladeepika XV sl. 17 (Jupiter, Sun, Mercury, Saturn) (existing) |
| DC-04 | Which divisional chart judges livelihood | BPHS Ch. 7 v. 1-8 (Dasamsa: power and position) vs Phaladeepika V sl. 1 (Navamsa of the 10th lord): two methods, two profiles |
| DC-05 | `ASTROLOGY_STANDARDS` "D4 = property/home/fortune" and "D9 = ... dharma", "D12 = parents" ... vs BPHS Ch. 7 v. 1-8 ("fortunes", "spouse", "parents") | standards wording is not supported beyond the verse; a documentation correction is for the owner |
| DC-06 | Reports ownership | see section 14 |
| DC-07 | Vastu in Phase 17 | see section 13 |
| DC-08 | Taxonomies differ (27, features.md, `Intent` 14, `domains.yaml` 4) | matrix sheet A |
| DC-09 | Rule count and domain axis in the baseline audit | section 1 |

Policy for conflicts (standards LD-18): never merged; each source profile is its own result; no source ranking unless a project rule already exists; Phase 16 reports `CONFLICTING_EVIDENCE` where claims cross profiles.

## 13. Vastu

`Phases.md` lists Vastu as "Deferred (owner-accepted); cross-domain Vastu stays with Phase 17"; `docs/ASTROLOGY_STANDARDS.md` line 95 says cross-domain Vastu analysis is Phase 17; the Phase 17 domain list does not include it; `features.md` lists "Vastu-related guidance" as a supported system; standards P9-04 records that the candidate sources (Mayamata, Manasara, Brihat Samhita Ch. 53) were identified and **not read**, the product collects no building data, and structural or construction advice is out of scope. Finding: **`RESEARCH_PENDING` and `DEFERRED`**; no methodology exists; nothing was invented; Phase 17 should not implement it. The "stays with Phase 17" wording is an ownership statement, not a requirement to build now (decision 12).

## 14. Reports

Evidence: `docs/ARCHITECTURE.md` section 2/5 item 8 places reports in `services/agent/reports/` as deterministic assembly; `reports/__init__.py` says "implemented starting Phase 17 / Phase 20's report templates"; `Phases.md` Phase 15 says reports are "Phase 17 and 20", but the Phase 20 block names no reports; Phase 11 says reports belong to Phase 19 (app); Phase 18 lists a "Reports API"; Phase 19 lists a Reports screen; `features.md` section 20 lists the reports (including Love and Marriage, Career, Wealth, Education, Videsh Yoga, Foreign education, Foreign settlement). **`UNRESOLVED_OWNER_DECISION`.** Recommendation: reports are composition: Phase 17 delivers the structured, verifiable `DomainAnalysisResult` that a report consumes; the template and assembly code and the API are Phase 18 and 19/20. Do not implement reports in Phase 17.

## 15. Architecture recommendation (details in ADR-012)

Evaluated: (A) `agent` presets only; (B) `knowledge` domain methodology; (C) `rule-engine` domain metadata; (D) a new service.

**Recommended: a split of responsibilities across the existing components, no new service.**
- **Domain methodology data** (what is relevant to a domain, with provenance and status: houses, karakas, vargas, conflicts, NOT_EVALUABLE reasons) lives in `services/knowledge` (extending `content/domains.yaml`; outside `rules/`, so the Phase 6 hash and the Phase 12 version pins are untouched). It is data, never prose.
- **Deterministic evaluation of domain relevance** (which houses, lords, karakas, vargas, dasha and transit relations hold for this chart) is rule-engine work, because it is a fact-over-facts evaluation and the agent must not compute (ADR-001). Precedent: palm rules live in a separate ruleset with its own manifest and hash (`services/rule-engine/palm_rules/`, CONTRIBUTING). A **separate domain ruleset** with its own manifest keeps the Phase 6 ruleset hash `8d29a18c…77209` unchanged; the rule engine needs additive fact readers for varga placements, dasha and transit sections (the evidence modules exist; no shipped rule reads them).
- **Routing and narration** (intent to domain, evidence presets, narration schema, policy) lives in `services/agent` (ARCHITECTURE section 8): presets and prompt templates only, no calculation.
- **Contracts** in `packages/contracts` (additive, new module).
- **Verification**: Phase 16 verifies domain claims through the existing claim contract; the verifier must be able to resolve the new domain evidence (a small additive Phase 17 change to `services/verification`, which the owner has not yet closed).
- **Rejected**: (D) a new service (ADR-003/008 boundary cost, no need); (A) alone (it would force deterministic relevance into the agent, breaking ADR-001); (C) alone or in the Phase 6 ruleset (hash corruption; the palm precedent says separate); (B) alone (knowledge never evaluates rules).

## 16. Contracts (design only; names are provisional)

Common to all: `schema_version`, `contract_version`, `domain` (the `LifeDomain` id), `taxonomy_version`, `knowledge_version`, `ruleset_hash` (domain ruleset), `chart_ref` (the Phase 6 bundle hash), `methodology_profile` (source profile id; never merged), `uncertainty_flags`, `status` with a typed reason code, `provenance` (source, edition, location, verification level).
- **`LifeDomain`**: enum or registry entry: id, label, `taxonomy_status` (the matrix status), definition reference, policy class. Not an extension of the agent `Intent` (which stays a coarse router; a mapping Intent to candidate domains is data).
- **`DomainDefinition`** (knowledge data, not a request): houses, karakas, vargas, each with source profile, location, direct or derived, status, and conflicts.
- **`DomainAnalysisRequest`**: domain, bundle references (chart, optional dasha, transit, varga sections by hash), `as_of`, language, profile selection, subject age class (for the minors gate), and policy flags. No birth data and no sex unless the owner decides.
- **`DomainEvidencePlan`**: the ordered list of required facts, each marked `AVAILABLE_NOW`, `NEEDS_SECTION`, `PHASE_18_DEPENDENCY` or `NOT_EVALUABLE(reason)`.
- **`DomainEvidence`**: typed records (`FACT`, `RULE`, `RELATION` (lord/occupant/aspect/karaka relation to a domain house), `STATUS`) with chart, house, planet, varga, dasha-period and transit-snapshot references and the exact source profile.
- **`DomainInterpretation`**: structured tags only (domain, signification, effect class, source profile, rule ids, conflicting profiles), never prose; any wording belongs to the knowledge store and the agent.
- **`DomainAnalysisResult`**: the above plus per-domain status, `not_evaluable` list with reasons, conflicts per profile, versions and a content hash; the Phase 15 agent consumes it as evidence records of the existing five classes; Phase 16 verifies claims that cite it.

## 17. Canonical pipeline

```
Intent (coarse) -> LifeDomain (data mapping) -> DomainDefinition (knowledge data)
  -> evidence plan (what the definition requires)
  -> AVAILABLE NOW: D1 chart facts, house lords/occupants/aspects, planet dignity,
       existing Phase 6 rule results (51 rules), Phase 12 significations,
       divisional charts (astro-engine computes them)
  -> NEEDS A PHASE 17 SECTION (research done, mapping data and readers to be built):
       varga placements as evidence; domain relation facts; the domain ruleset
  -> NEEDS PHASE 18: the Dasha API and Transit API tools that obtain dasha/transit facts
       for a user and date (a section already inside a supplied bundle may be read)
  -> NOT_EVALUABLE: every domain/house/karaka pair no source read states
  -> DomainAnalysisResult (structured) -> Phase 15 narration (UNVERIFIED) -> Phase 16 verification
```

## 18. Owner decision package

| # | Decision | Recommended | Evidence and reason | Alternatives | Consequence | Blocking |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 27 domains vs source-supported plus NOT_EVALUABLE | Build all 27 as taxonomy entries; analyse only those with a source-backed mapping; report the rest `NOT_EVALUABLE` with reasons | 7 of 27 supported, 11 partial, 9 not evaluable; the project's own rule is not to invent mappings | Wait until all sources are read; drop unsupported domains | Honest "complete" system; some domains return no analysis until research | Yes |
| 2 | Canonical taxonomy | The Phases.md 27 plus the features.md additions (Parents, Siblings, Income, Higher education, Entrepreneurship, General patterns) as aliases or sub-domains; Health and Major life transitions excluded | features.md and Phases.md differ; Intent has 14 | Phases.md only; features.md only | A single registry avoids a third taxonomy | Yes |
| 3 | Domain to varga mappings | Adopt BPHS Ch. 7 v. 1-8 as profile `BPHS_SAN_7_1_8` exactly as worded; keep Phaladeepika V (Navamsa for livelihood) as a second profile; correct the standards wording for D4, D9, D12 | image-verified; D4 "property" unsupported | Add modern mappings as labelled engineering conventions | The varga choice is source-traceable | Yes |
| 4 | Dasha ownership | Phase 17 reads only a dasha section already in the bundle; the tool and API are Phase 18; adopt "occupant, owner, aspector of the domain house" only as a labelled engineering profile if the owner agrees | only Phaladeepika X.13 is stated (marriage); Adh. XIX-XX unread | Pull the tools into Phase 17 (scope creep); wait for reading | Domain results show dasha as `PHASE_18_DEPENDENCY` when absent | Yes |
| 5 | Transit ownership | Same split as dasha; Phaladeepika XVI.31-35 is the source | image-verified | same | same | Yes |
| 6 | Architecture location | The split in section 15 (knowledge data, separate domain ruleset in the rule-engine, agent presets, contracts, verification resolution) | ADR-001, the palm precedent, ARCHITECTURE section 8 | Agent-only presets; a new service | Touches four components additively; Phase 6 hash stays pinned | Yes |
| 7 | Reports ownership | Not Phase 17; Phase 17 supplies the report-ready result | five documents disagree | Phase 17 builds report assembly | Clears the placeholder wording | No (for Phase 17 build) |
| 8 | Children and minors | Block love, GF/BF, marriage, spouse and children domains unless the subject age class is adult (18); decide a separate rule for childhood, school and college | CM-04; "age-appropriate controls" is undefined | Allow with a disclaimer | Needs an age-class input, owned by Phase 18 profiles | Yes |
| 9 | Fertility, pregnancy, paternity | Refuse as for palmistry, and do not encode "no offspring", "loss of children" or legitimacy statements, until counsel reviews | the source text contains them; policy is silent | Allow with a disclaimer | Children domain is limited to structural significations | Yes |
| 10 | Finance | Interpretation with the professional-advice disclaimer; no amounts, ages or investment advice; "Investments" `NOT_EVALUABLE` | BPHS amounts; no source for investments | Allow investment-flavoured readings | Narrow but safe | No |
| 11 | Health | Not a Phase 17 domain; any later Health domain follows features.md (interpretation only), excludes death and longevity | not in the 27 | Include health with disclaimer | Avoids the disease statements | No |
| 12 | Vastu | Keep `DEFERRED` and `RESEARCH_PENDING`; amend the "stays with Phase 17" wording to "owned by Phase 17 when research exists" | no source read; no building data | Start Vastu research now | None for Phase 17 build | No |
| 13 | Phase 16 closure | Confirm the three items in SUMMARY section 50 C before Phase 17 relies on the verifier | closure still pending | Proceed with Phase 16 open | Phase 17 modifies the verifier resolution | Yes (for the verifier change) |

Additional decisions the research raised: whether to encode derogatory or fear statements (no, by the precedent of MU-10, CM-10: recommended); the subject's sex (not collected: recommended to keep it uncollected and mark spouse analysis that needs it `NOT_EVALUABLE`); the rule tag `marriage.spouse_longevity` (recommended: do not narrate).

## 19. Implementation readiness

| Requirement | Class |
| --- | --- |
| Domain taxonomy registry | OWNER_DECISION_REQUIRED (decisions 1, 2) |
| House mappings for Education, Career, Finance, Wealth, Marriage, Family, Siblings, Children (policy-gated), and the partial ones (Parents with DC-01, Spirituality at the 9th and 12th), each carrying its status | READY_FOR_IMPLEMENTATION as data, once decisions 1 to 3 are made |
| Karaka mappings (table in section 5) | READY_FOR_IMPLEMENTATION as data |
| Varga mapping, BPHS Ch. 7 | READY_FOR_IMPLEMENTATION as data after decision 3 |
| Varga evidence section in the bundle | OWNER_DECISION_REQUIRED (decision 6; additive rule-engine change) |
| Domain relevance of dasha beyond marriage | RESEARCH_PENDING (Phaladeepika XIX, XX; BPHS Vol II) and OWNER_DECISION_REQUIRED (decision 4) |
| Dasha and transit tools and APIs | PHASE_18_DEPENDENCY |
| Reading an already supplied dasha or transit section | OWNER_DECISION_REQUIRED (decisions 4, 5) |
| Domain rules (combinations) for any domain | RESEARCH_PENDING (BPHS Ch. 12 to 24, 41 and others unread) |
| Existing-rule domain tagging | READY_FOR_IMPLEMENTATION for the rules in the matrix (a metadata-only change to a separate domain ruleset, not to the Phase 6 files) once decision 6 is made |
| Children, fertility, minors, health | OWNER_DECISION_REQUIRED and LEGAL_REVIEW_REQUIRED |
| Foreign education, Corporate life, Startup, Birth, Childhood, School, College, Personal life, GF/BF, Investments | NOT_EVALUABLE |
| Vastu | RESEARCH_PENDING (DEFERRED) |
| Reports | OWNER_DECISION_REQUIRED (decision 7) |
| Hindi and Hinglish wording | CALIBRATION_REQUIRED (unchanged limitation) |

**OVERALL STATUS: BLOCKED — OWNER DECISION REQUIRED.** The research needed to start the structural layer (taxonomy, houses, karakas, vargas, existing rules) is done and source-backed; the decisions above fix its scope, location and policy gates. Rule-level combinations and domain-relevant dasha remain `RESEARCH_PENDING` and are not needed for the structural layer.

NO PHASE 17 IMPLEMENTATION WAS PERFORMED.
