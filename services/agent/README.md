# agent

Agent Orchestrator (`docs/architecture/adr/ADR-003-agent-service-boundary.md`). Canonical service name — do not rename to `ai-agent`.

**Responsible for**: intent/domain detection, planning, invoking `astro-engine`/`rule-engine`/`knowledge`, evidence assembly, invoking the AI Reasoner, invoking `verification`, conversation/memory access, and the `voice`/`reports` subpackages (see `docs/ARCHITECTURE.md` §"Agent Orchestrator Architecture").

**Not responsible for**: computing any astrology fact, or releasing a response that bypasses mandatory verification.

## Subpackages

- `pandit_agent.voice` — STT/TTS turn-taking (Phase 20); an empty placeholder
- `pandit_agent.reports` — report assembly (Phase 17/20); an empty placeholder
- `pandit_agent.llm` — the self-hosted LLM capability (Phase 14, 2026-10-03; `docs/ARCHITECTURE.md` §36, ADR-009). The `LLMProvider` interface (`generate(LLMRequest) -> LLMResponse`, `health()`), the model manifest and loader, the model's pinned chat template, controlled context assembly, structured output with post-generation validation, an output policy scan, readiness states, typed errors, structured logging without content, a vLLM HTTP runtime (self-hosted, allow-listed hosts only) and a scripted test runtime for CI. Assets: `llm/` (see `llm/README.md`). It contains no planner or narration, and no client for any hosted model API.
- `pandit_agent.orchestration` — agent orchestration and narration (Phase 15, 2026-10-03; `docs/ARCHITECTURE.md` §37, ADR-010). `AgentOrchestrator.run(AgentRequest) -> NarrationResponse`: request screening and prompt-injection handling, deterministic intent and domain detection, a bounded static planner, a closed allow-list of typed evidence tools (adapters for the Phase 13 `PalmEvidenceBundle` and the Phase 6 astrology `EvidenceBundle`), deterministic context assembly with recorded trimming, an explicit Phase 14 `LLMRequest` (trusted task instruction, typed evidence, typed restrictions, user text only as the user message), structured narration whose claims carry structured evidence references, provenance and uncertainty copied from the evidence and an `UNVERIFIED` state for Phase 16, localized disclaimers and refusals, bounded in-session memory (labels only), typed errors and content-free logging. It uses `LLMProvider` only: no second provider, no hosted model, no fallback. **It does not verify claims (Phase 16), compute any fact, persist user data (Phase 18) or touch images.**

## Status

Phase 3: package boundary, config, health check, placeholders. Phase 14: the LLM capability. Phase 15: the orchestration and narration layer above. Not built: verification (Phase 16); persistent memory and upload, storage and consent (Phase 18); adapters for dasha, transit, compatibility and knowledge-retrieval evidence; combined-domain requests; voice and reports. The real model is **not** downloaded or run by this repository (`MODEL_DOWNLOAD_REQUIRED`, `HARDWARE_REQUIRED`) and every Phase 15 test ran against the scripted test runtime; narration quality, Hindi and Hinglish quality, intent accuracy, safety recall and latency are unevaluated (`CALIBRATION_REQUIRED`).

## Using the orchestrator

```python
from pandit_agent.llm.service import create_service
from pandit_agent.llm.settings import LLMSettings
from pandit_agent.orchestration import (
    AgentOrchestrator,
    PalmBundleTool,
    ToolRegistry,
    narration_schema_registry,
)

llm = create_service(LLMSettings(), schemas=narration_schema_registry())  # Phase 14 service
llm.start()
agent = AgentOrchestrator(llm, ToolRegistry([PalmBundleTool(palm_evidence_bundle)]))
response = agent.run(agent_request)  # a NarrationResponse; check response.status
```

## Local development

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```
