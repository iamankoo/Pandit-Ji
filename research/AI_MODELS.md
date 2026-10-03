# Research — Self-Hosted AI Models

Core intelligence should not require hosted OpenAI/Gemini-style APIs.

Separate roles:
- planner/agent
- astrology reasoning
- multilingual response
- embeddings
- palm vision
- STT
- TTS

Evaluate open-weight families such as Qwen, Llama and Mistral by benchmark, not brand.

Test English, Hindi, Hinglish, chart-grounded QA, evidence adherence, hallucination, safety, long context, latency, memory and cost.

Promotion requires no critical regression, chart-fact fidelity, evidence fidelity, multilingual/safety regression pass and deterministic test-suite pass.

## Phase 14 verification record (2026-10-03)

Purpose: record how the Phase 14 model and runtime were chosen, with the evidence read, so the choice can be audited and replaced. This is a compatibility and licence verification, **not a quality evaluation**: no benchmark was run, no output was judged, and nothing below ranks the candidates.

### Method
Facts marked *primary* were read from the model host's metadata API, the model files at a pinned revision, or the vendor's release post on 2026-10-03. Facts marked *secondary* come from third-party articles surfaced by search and were **not** verified; they are listed so the gap is visible and none is relied on.

### Candidates checked (metadata read from the host API; revision = commit id at read time)
| Model | Licence tag | Access | Hindi evidence | Revision read |
| --- | --- | --- | --- | --- |
| Qwen/Qwen3-8B | apache-2.0 (primary; LICENSE file read) | ungated | Hindi named in the release post's language list (primary) | b968826d9c46dd6066d109eabc6255188de91218 |
| meta-llama/Llama-3.1-8B-Instruct | llama3.1, "Llama 3.1 Community License" (primary tag; licence text not read) | gated, manual acceptance | Hindi is in the model's language tags (primary) | 0e9e39f249a16976918f6564b8830bc894c89659 |
| mistralai/Mistral-Nemo-Instruct-2407 | apache-2.0 (primary tag; licence text not read) | ungated | the host's language tags list nine languages without Hindi (primary); a press summary names Hindi (secondary): **unresolved** | 04d8a90549d23fc6bd7f642064003592df51e9b3 |
| google/gemma-3-12b-it | gemma, the vendor's own terms (primary tag; terms not read) | gated, manual acceptance | the host metadata carries no language tags (primary); a secondary article claims 140+ languages: not verified | 96b6f1eccf38110c56df3a15bffe176da04bfd80 |

Newer releases named by secondary articles (for example further Qwen, Gemma, Llama and Mistral generations) were **not** checked and are neither accepted nor rejected here.

### Criteria and what was verified for the selected model (Qwen3-8B at the pinned revision)
- **Licence and access**: Apache-2.0, LICENSE file hashed (`832dd9e0…`), ungated, no use-scale clause in the licence text. Counsel has not reviewed it (`LEGAL_REVIEW_REQUIRED`).
- **Provenance**: 12 files with SHA-256 (the weight files' values are the host's LFS object ids; the small files were hashed locally); revision pinned; weights never in git.
- **Languages**: Hindi is named; Hinglish (romanised Hindi mixed with English) is not named anywhere read. Quality in English, Hindi and Hinglish is **unevaluated**.
- **Context**: the model card states 32,768 natively and 131,072 with YaRN; `config.json` has `max_position_embeddings` 40960. Both are recorded; the operational limit is 32,768 with YaRN off.
- **Chat template**: ChatML (`<|im_start|>`, `<|im_end|>`), vendored from `tokenizer_config.json` at the pinned revision, hash pinned; `enable_thinking` supported by the template; no BOM token.
- **Runtime**: the model card recommends vLLM 0.8.5 or later; the package index showed vLLM 0.19.1 (Apache-2.0, Python 3.10 to 3.13) on 2026-10-03. vLLM's documentation lists `response_format` with a JSON Schema as the current structured-output request field; the older `guided_json` field was removed in 0.12.0. The server was **not** run.
- **Hardware**: five bfloat16 weight files total 16,381,516,776 bytes; a single GPU with 24 GB VRAM or more is an estimate, not a measurement. No quantised variant was verified.
- **Tool calling and long context**: the template supports tool calls and the model card describes tool-calling use; Phase 14 uses neither (Phase 15 decides).

### Why this combination was implemented
The project's locked direction is PyTorch, Transformers-style checkpoints and vLLM serving (`TECH_STACK.md`, ADR-002). Of the candidates read, this is the one whose licence text, ungated access, pinned file hashes, Hindi language listing, chat template and runtime compatibility were all verified from primary sources in this session. That is the selection basis: verified fit to the recorded requirements, not a claim that it is the strongest model. Replacing it is a new manifest and a new chat-template file with no code change to the service.

### Not done (stated plainly)
No benchmark, no Hindi or Hinglish quality measurement, no structured-output reliability measurement, no latency or throughput measurement on a GPU, no fine-tuning, and no check of larger sizes. The evaluation plan of the first section (English, Hindi, Hinglish, chart-grounded QA, evidence adherence, hallucination, safety, long context, latency, memory) remains `CALIBRATION_REQUIRED`, and a model is promoted only on its results.

### Sources
- https://huggingface.co/api/models/Qwen/Qwen3-8B and the files at revision b968826d9c46dd6066d109eabc6255188de91218
- https://huggingface.co/Qwen/Qwen3-8B (model card) and https://qwenlm.github.io/blog/qwen3/ (release post)
- https://huggingface.co/api/models/meta-llama/Llama-3.1-8B-Instruct
- https://huggingface.co/api/models/mistralai/Mistral-Nemo-Instruct-2407
- https://huggingface.co/api/models/google/gemma-3-12b-it
- https://pypi.org/pypi/vllm/json and https://docs.vllm.ai/en/latest/features/structured_outputs/
