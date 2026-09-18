# ADR-002: Self-hosted AI inference

Status: Locked (Phase 1)

## Context
Pandit Ji's product baseline (`features.md`, `docs/ASTROLOGY_STANDARDS.md` §"AI scope boundary") requires that core astrology reasoning not depend on external hosted proprietary LLM APIs (OpenAI, Gemini, or similar), to avoid per-token cost dependency, data-residency exposure of sensitive birth/palm data to a third party, and vendor lock-in on the product's core differentiator.

## Decision
Core intelligence (chart interpretation, prediction narration, agent planning, personalization, knowledge reasoning, core chatbot responses) runs on self-hosted, open-weight models (candidate families: Qwen, Llama, Mistral — not finalized in this ADR; see `research/AI_MODELS.md`). The `agent` service accesses the model exclusively through an `LLMProvider`/AI Reasoner interface (see `docs/ARCHITECTURE.md` §"AI Infrastructure"), never a hardcoded call to a specific model or vendor SDK.

## Consequences
- A hosted-API fallback may exist only as a **development-time stopgap** before self-hosted serving infrastructure is ready — never as the production/core dependency, and always behind the same interface so it can be removed without touching agent logic.
- Model selection, fine-tuning, and serving-stack choice (vLLM/Ollama/TGI, etc.) are deferred to Phase 13, not decided here.
- Sensitive data exposure to the model is bounded by the evidence-bundle pattern (ADR-001) and the Security Architecture's data-minimization rule (`docs/ARCHITECTURE.md` §"Security Architecture") — the model receives evidence necessary to answer, not raw unrelated user data.
