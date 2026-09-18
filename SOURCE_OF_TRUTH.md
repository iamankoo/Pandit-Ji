# Pandit Ji — Source of Truth

## Authority order
1. Explicitly locked project-owner decisions
2. `features.md` — WHAT
3. `Phases.md` — HOW/WHEN; sole execution roadmap
4. `docs/ARCHITECTURE.md` — technical structure
5. `docs/ASTROLOGY_STANDARDS.md` — calculation/interpretation standards (locked canonical location; there is exactly one standards document, no separate `docs/calculation-standards.md`)
6. `TECH_STACK.md` — locked technology-stack choices (there is exactly one technology-stack document; derived from and must not contradict `docs/ARCHITECTURE.md`)
7. `PRODUCT_POLICIES.md`
8. `LEGAL_REGULATIONS.md`
9. Research documents
10. Code/configuration

## Conflict rule
Never silently resolve contradictions. Record them, resolve in the higher-authority document, update dependents, and add a changelog entry.

## Truth pipeline
User input → normalized data → deterministic calculation engine → structured facts → rule engine → evidence bundle → AI explanation → verification → response.

The LLM is not the source of astronomical/astrological calculation truth.

## Research hierarchy
Astronomy: official ephemeris/data → primary standards → peer-reviewed literature → technical references.
Traditional astrology: recognized classical texts → established translations/commentaries → documented school methodology → reputable secondary references.
Law/platform policy: government/statutory source → official platform policy → official legal documentation → secondary commentary.

## Claim classes
CALCULATION_FACT; ASTROLOGICAL_RULE; TRADITIONAL_INTERPRETATION; RESEARCH_EVIDENCE; PRODUCT_POLICY; LEGAL_REQUIREMENT; COMPETITOR_OBSERVATION; AI_EXPLANATION.
