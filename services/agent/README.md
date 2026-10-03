# agent

Agent Orchestrator (`docs/architecture/adr/ADR-003-agent-service-boundary.md`). Canonical service name — do not rename to `ai-agent`.

**Responsible for**: intent/domain detection, planning, invoking `astro-engine`/`rule-engine`/`knowledge`, evidence assembly, invoking the AI Reasoner, invoking `verification`, conversation/memory access, and the `voice`/`reports` subpackages (see `docs/ARCHITECTURE.md` §"Agent Orchestrator Architecture").

**Not responsible for**: computing any astrology fact, or releasing a response that bypasses mandatory verification.

## Subpackages

- `pandit_agent.voice` — STT/TTS turn-taking (Phase 20); an empty placeholder
- `pandit_agent.reports` — report assembly (Phase 17/20); an empty placeholder
- `pandit_agent.llm` — the self-hosted LLM capability (Phase 14, 2026-10-03; `docs/ARCHITECTURE.md` §36, ADR-009). The `LLMProvider` interface (`generate(LLMRequest) -> LLMResponse`, `health()`), the model manifest and loader, the model's pinned chat template, controlled context assembly, structured output with post-generation validation, an output policy scan, readiness states, typed errors, structured logging without content, a vLLM HTTP runtime (self-hosted, allow-listed hosts only) and a scripted test runtime for CI. Assets: `llm/` (see `llm/README.md`). **It contains no planner, memory, tool selection, narration or verification**, and no client for any hosted model API.

## Status

Phase 3: package boundary, config, health check, placeholders. Phase 14: the LLM capability above. Still not here (`Phases.md` Phases 15 and 16): intent detection, planning, evidence assembly across services, narration, conversation memory and the call to `verification`. The model is **not** downloaded or run by this repository (`MODEL_DOWNLOAD_REQUIRED`, `HARDWARE_REQUIRED`); its language quality, structured-output reliability and latency are unevaluated (`CALIBRATION_REQUIRED`).

## Local development

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```
