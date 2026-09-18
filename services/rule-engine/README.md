# rule-engine

Structured astrology rules and deterministic rule evaluation. Canonical service name — do not rename to `ai-agent`-style or otherwise.

**Responsible for**: turning `astro-engine` facts into yoga/dosha detections and tagged interpretive evidence, evidence collection, contradiction/conflict analysis between rules (see `docs/ARCHITECTURE.md` §"Rule Engine Architecture", `docs/ASTROLOGY_STANDARDS.md` §"Yoga / Dosha standards").

**Not responsible for**: computing chart facts itself (consumes them from `astro-engine`), or producing user-facing natural language (structured tags + facts only — phrasing is `agent`'s job).

## Phase 3 status

Foundation only: package boundary, config, health check. No rule schema/evaluator/content yet — that begins in `Phases.md` Phase 6.

## Local development

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```
