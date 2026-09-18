# astro-engine

Deterministic astronomical and chart calculation engine. Canonical service name — do not rename to `astrology-engine`.

**Responsible for**: planetary positions, houses/ascendant, divisional charts, dignity/combustion/retrograde, ashtakvarga, dashas, transits, panchang, muhurta, compatibility scoring, numerology (see `docs/ARCHITECTURE.md` §"Astrology Engine Architecture", `docs/ASTROLOGY_STANDARDS.md`).

**Not responsible for**: interpretation, rule evaluation, narration, HTTP, or any dependency on `agent`/`rule-engine`/`knowledge`/`verification`.

## Phase 3 status

Foundation only: package boundary, config, health check. No calculation logic — that begins in `Phases.md` Phase 4.

## Local development

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```
