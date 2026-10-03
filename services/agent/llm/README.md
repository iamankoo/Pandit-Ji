# services/agent/llm: model manifests and pinned assets (Phase 14)

Data assets for `pandit_agent.llm` (`docs/ARCHITECTURE.md` section 36, ADR-009). Small text files only: **model weights are never committed** (`.gitignore` excludes `models/`, `*.safetensors`, `*.gguf`; a test asserts no weight-like file is in the tree).

| Path | What it is |
| --- | --- |
| `manifests/qwen3-8b.json` | The selected model: pinned revision, SHA-256 of every artifact, licence record, tokenizer and chat-template hashes, context figures, runtime, quantization, hardware class, provenance. `production_eligible: false` with named blockers. |
| `manifests/mock-deterministic-test.json` | A test fixture for the scripted runtime. Not a model; it can never be production eligible and is refused unless `allow_test_fixture` is set. |
| `templates/qwen3_chatml.jinja` | The chat template published with the model at the pinned revision (hash in the manifest). A template that does not hash to the manifest value is refused. |

## Status (honest)
- IMPLEMENTED: manifest validation, hash verification of a local model directory, chat-template pinning, the vLLM HTTP runtime (tested against a protocol fake), the scripted runtime for CI.
- MODEL_DOWNLOAD_REQUIRED and HARDWARE_REQUIRED: the weights have not been downloaded and no server has been run by this repository. No quality, latency or capacity figure exists.
- OPTIONAL_LOCAL_TEST (skipped in CI): `PANDIT_LLM_REAL_VLLM_URL` (a real server test) and `PANDIT_LLM_TOKENIZER_DIR` (a tokenizer cross-check).
- LEGAL_REVIEW_REQUIRED: the licence was read, not counsel-reviewed (`LEGAL_REGULATIONS.md`).

## Acquiring the weights (explicit, never automatic)
Nothing in the code or in CI downloads a model. An operator does it once, on the host that will serve it:

1. Download exactly the pinned revision (commands are the host's documented ones and were not run by this repository):
   `hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218 --local-dir services/agent/llm/models/qwen3-8b`
   (`huggingface-cli download` is the older name of the same command). The directory is git-ignored.
2. Point the service at it so its hashes are verified at load: `AGENT_LLM_MODEL_DIR=services/agent/llm/models/qwen3-8b` (verification is on by default; `AGENT_LLM_VERIFY_ARTIFACTS=false` skips it and the health detail then says the hashes were not verified). Any size or SHA-256 mismatch is `MODEL_LOAD_FAILURE`; a missing file is `MODEL_UNAVAILABLE`.
3. Serve it with vLLM on a private address, with the served name equal to the manifest's model id (documented flags, not run here):
   `vllm serve services/agent/llm/models/qwen3-8b --served-model-name Qwen/Qwen3-8B --host 127.0.0.1 --port 8000`
   A GPU of the 24 GB class or more is an estimate from the 16.4 GB of bfloat16 weights, not a measurement.
4. Configure the agent (prefix `AGENT_LLM_`): `ENDPOINT_URL` (default `http://127.0.0.1:8000`), `ALLOWED_HOSTS` (default `localhost,127.0.0.1,::1`; a non-loopback host must be listed on purpose), `SERVED_MODEL_NAME`, `MANIFEST_NAME`.

Replacing the model is a new manifest plus its chat-template file; the service code does not change. Fine-tuned derivatives must be separately versioned and reproducible and are not part of Phase 14. No user data is used to train anything.

## Tests
`python -m pytest -q` in `services/agent` runs everything that needs no GPU and no weights (196 tests at the time of writing). The two optional local tests are skipped without their environment variables and the skip reason says why.
