# agent

Agent Orchestrator (`docs/architecture/adr/ADR-003-agent-service-boundary.md`). Canonical service name — do not rename to `ai-agent`.

**Responsible for**: intent/domain detection, planning, invoking `astro-engine`/`rule-engine`/`knowledge`, evidence assembly, invoking the AI Reasoner, invoking `verification`, conversation/memory access, and the `voice`/`reports` subpackages (see `docs/ARCHITECTURE.md` §"Agent Orchestrator Architecture").

**Not responsible for**: computing any astrology fact, or releasing a response that bypasses mandatory verification.

## Subpackages

- `pandit_agent.voice` — STT/TTS turn-taking (Phase 20)
- `pandit_agent.reports` — report assembly (Phase 17/20)

Both are empty placeholders in Phase 3.

## Phase 3 status

Foundation only: package boundary, config, health check, subpackage placeholders. No planning/orchestration/LLM logic yet — that begins in `Phases.md` Phase 15.

## Local development

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```
