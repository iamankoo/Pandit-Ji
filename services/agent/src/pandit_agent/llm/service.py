"""``LLMService``: LLMRequest in, LLMResponse out. The language layer, nothing more.

Flow per request: readiness and model checks -> language and schema checks -> controlled prompt
assembly -> the model's own chat template -> the runtime -> (structured output) strict parse and
schema validation -> output policy scan -> language-script heuristic -> response with provenance.

Every expected failure becomes a FAILED response with a typed error; nothing falls back to another
model or to any hosted API; nothing is retried except malformed structured output at non-zero
temperature (retrying greedy decoding would repeat the same answer). The model never changes a
fact: it only receives the evidence it is given and returns text.
"""

from __future__ import annotations

import importlib.metadata
import platform
import time
from typing import Any

from pandit_contracts.llm import (
    FinishReason,
    LLMErrorCode,
    LLMHealth,
    LLMRequest,
    LLMResponse,
    LLMStatus,
    ModelProvenance,
    OutputMode,
    Readiness,
    ResponseMetrics,
    TokenUsage,
)
from pandit_shared.logging import bind_request_id

from pandit_agent.llm.chat_template import ChatTemplate
from pandit_agent.llm.context import assemble
from pandit_agent.llm.errors import LLMFailure
from pandit_agent.llm.language import check_language
from pandit_agent.llm.loader import ModelLoader, ReadinessTracker
from pandit_agent.llm.manifest import ModelManifest, load_manifest
from pandit_agent.llm.observability import PerformanceRecorder, log_event
from pandit_agent.llm.runtime import LLMRuntime, RuntimeCall
from pandit_agent.llm.safety import check_output
from pandit_agent.llm.settings import LLMSettings
from pandit_agent.llm.structured import SchemaRegistry, parse_and_validate, string_leaves
from pandit_agent.llm.vllm_runtime import VLLMServerRuntime

_DEPENDENCIES = ("jinja2", "jsonschema", "pydantic", "pandit-contracts", "pandit-agent")


def _dependency_versions() -> tuple[tuple[str, str], ...]:
    versions: list[tuple[str, str]] = [("python", platform.python_version())]
    for name in _DEPENDENCIES:
        try:
            versions.append((name, importlib.metadata.version(name)))
        except importlib.metadata.PackageNotFoundError:
            versions.append((name, "unknown"))
    return tuple(sorted(versions))


def _strip_reasoning(text: str) -> str:
    """Drop a leading reasoning block: reasoning is not evidence and is never returned."""
    if "</think>" in text:
        return text.rsplit("</think>", 1)[-1].lstrip("\n")
    if text.lstrip().startswith("<think>"):
        raise LLMFailure(
            LLMErrorCode.GENERATION_FAILURE, "the output ended inside an unfinished reasoning block"
        )
    return text


class LLMService:
    def __init__(
        self,
        settings: LLMSettings,
        manifest: ModelManifest,
        template: ChatTemplate,
        runtime: LLMRuntime,
        *,
        schemas: SchemaRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._manifest = manifest
        self._template = template
        self._runtime = runtime
        self._schemas = schemas if schemas is not None else SchemaRegistry()
        self._tracker = ReadinessTracker()
        self._perf = PerformanceRecorder()
        self._loader = ModelLoader(
            manifest,
            runtime,
            self._tracker,
            model_dir=settings.model_dir,
            verify_artifacts=settings.verify_artifacts,
        )
        self._dependencies = _dependency_versions()

    # -- lifecycle -------------------------------------------------------------------------

    def start(self) -> LLMHealth:
        """Load the model. A failure is reported in the health state, it does not raise."""
        state = self._loader.load()
        if state is Readiness.MODEL_READY and self._tracker.load_ms is not None:
            self._perf.record_load(self._tracker.load_ms)
        log_event(
            event="model_load",
            model_id=self._manifest.model_id,
            model_version=self._manifest.model_revision,
            runtime=self._runtime.name,
            is_real_model=self._runtime.is_real_model,
            state=state.value,
            error_code=self._tracker.last_error.value if self._tracker.last_error else None,
            load_ms=self._tracker.load_ms,
        )
        return self.health()

    def health(self) -> LLMHealth:
        detail: str | None = None
        if self._tracker.state is Readiness.MODEL_READY and not self._tracker.artifacts_verified:
            detail = "ready; artifact hashes were not verified by this process"
        elif self._tracker.last_error is not None:
            detail = f"last load error: {self._tracker.last_error.value}"
        return LLMHealth(
            state=self._tracker.state,
            runtime=self._runtime.name,
            is_real_model=self._runtime.is_real_model,
            model_id=self._manifest.model_id,
            model_load_ms=self._tracker.load_ms,
            last_error=self._tracker.last_error,
            detail=detail,
        )

    def performance(self) -> dict[str, float | int | None]:
        return self._perf.snapshot()

    # -- generation ------------------------------------------------------------------------

    def generate(self, request: LLMRequest) -> LLMResponse:
        started = time.perf_counter()
        request_hash = request.request_hash()
        bind_request_id(request.request_id)
        try:
            response = self._generate(request, request_hash, started)
        except LLMFailure as failure:
            latency = (time.perf_counter() - started) * 1000.0
            response = LLMResponse(
                request_id=request.request_id,
                request_hash=request_hash,
                status=LLMStatus.FAILED,
                metrics=ResponseMetrics(latency_ms=latency),
                provenance=self._provenance(),
                generation_config_version=request.generation.config_version,
                error=failure.to_error(),
            )
        finally:
            bind_request_id(None)
        self._log_response(request, response)
        return response

    def _generate(self, request: LLMRequest, request_hash: str, started: float) -> LLMResponse:
        if self._tracker.state is not Readiness.MODEL_READY:
            raise LLMFailure(
                LLMErrorCode.MODEL_UNAVAILABLE,
                f"the model is not ready (state {self._tracker.state.value})",
            )
        if request.model_id != self._manifest.model_id:
            raise LLMFailure(
                LLMErrorCode.MODEL_UNAVAILABLE,
                "the requested model is not the loaded model (no silent model switch)",
            )
        if request.language not in self._manifest.languages.supported_interface_modes:
            raise LLMFailure(LLMErrorCode.UNSUPPORTED_LANGUAGE, "the language is not supported")

        gen = request.generation
        schema: dict[str, Any] | None = None
        if request.output.mode is OutputMode.JSON:
            assert request.output.schema_id is not None  # guaranteed by the contract
            schema = self._schemas.get(request.output.schema_id)

        assembled = assemble(
            request,
            self._template,
            max_context_chars=self._settings.max_context_chars,
            output_schema=schema,
        )
        prompt = self._template.render(assembled.messages, enable_thinking=gen.enable_thinking)
        prompt_tokens = self._runtime.count_tokens(prompt)
        if (
            prompt_tokens is not None
            and prompt_tokens + gen.max_new_tokens > self._manifest.context.operational_limit_tokens
        ):
            raise LLMFailure(
                LLMErrorCode.CONTEXT_TOO_LARGE,
                "the prompt plus the allowed output exceeds the operational context limit",
            )

        retry = schema is not None and gen.temperature > 0.0
        max_attempts = 1 + (self._settings.structured_retries if retry else 0)
        last_failure: LLMFailure | None = None
        attempts = 0
        for _ in range(max_attempts):
            attempts += 1
            result = self._runtime.generate(RuntimeCall(prompt, gen, schema))
            if result.finish_reason is FinishReason.ERROR:
                raise LLMFailure(LLMErrorCode.GENERATION_FAILURE, "the runtime reported an error")
            text = _strip_reasoning(result.text)
            if schema is None:
                if not text.strip():
                    raise LLMFailure(LLMErrorCode.GENERATION_FAILURE, "the model returned no text")
                structured = None
                break
            try:
                if result.finish_reason is FinishReason.LENGTH:
                    raise LLMFailure(
                        LLMErrorCode.MALFORMED_STRUCTURED_OUTPUT,
                        "the structured output was cut off at the token limit",
                        retryable=True,
                    )
                structured = parse_and_validate(text, schema)
                break
            except LLMFailure as failure:
                last_failure = failure
        else:
            assert last_failure is not None
            raise last_failure

        texts = list(string_leaves(structured)) if structured is not None else [text]
        restrictions = request.context.restrictions if request.context else ()
        check_output(texts, restrictions)
        language_check = check_language(request.language, texts)

        latency = (time.perf_counter() - started) * 1000.0
        completion = result.completion_tokens
        tps = completion / (latency / 1000.0) if completion and latency > 0 else None
        self._perf.record_request(latency, result.first_token_ms, tps)
        return LLMResponse(
            request_id=request.request_id,
            request_hash=request_hash,
            status=LLMStatus.OK,
            text=text,
            structured=structured,
            finish_reason=result.finish_reason,
            usage=TokenUsage(
                prompt_tokens=result.prompt_tokens
                if result.prompt_tokens is not None
                else prompt_tokens,
                completion_tokens=completion,
            ),
            metrics=ResponseMetrics(
                latency_ms=latency, first_token_ms=result.first_token_ms, tokens_per_second=tps
            ),
            provenance=self._provenance(),
            prompt_version=assembled.prompt_version,
            generation_config_version=gen.config_version,
            attempts=attempts,
            language_check=language_check,
        )

    # -- helpers ---------------------------------------------------------------------------

    def _provenance(self) -> ModelProvenance:
        m = self._manifest
        return ModelProvenance(
            manifest_id=m.manifest_id,
            model_id=m.model_id,
            model_revision=m.model_revision,
            artifact_sha256=m.artifact_hashes,
            tokenizer_config_sha256=m.tokenizer.tokenizer_config_sha256,
            chat_template_sha256=m.chat_template.sha256,
            runtime=self._runtime.name,
            runtime_version=self._runtime.version,
            is_real_model=self._runtime.is_real_model,
            quantization=m.quantization,
            dependency_versions=self._dependencies,
        )

    def _log_response(self, request: LLMRequest, response: LLMResponse) -> None:
        log_event(
            event="generate",
            request_id=response.request_id,
            request_hash=response.request_hash,
            model_id=self._manifest.model_id,
            model_version=self._manifest.model_revision,
            runtime=self._runtime.name,
            is_real_model=self._runtime.is_real_model,
            status=response.status.value,
            error_code=response.error.code.value if response.error else None,
            latency_ms=round(response.metrics.latency_ms, 3) if response.metrics else None,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            finish_reason=response.finish_reason.value if response.finish_reason else None,
            prompt_version=response.prompt_version,
            attempts=response.attempts,
            language=request.language.value,
        )


def create_service(
    settings: LLMSettings,
    runtime: LLMRuntime | None = None,
    *,
    schemas: SchemaRegistry | None = None,
) -> LLMService:
    """Build a service from settings. It never downloads anything and never picks a hosted API.

    A scripted test runtime must be passed explicitly and only works with a test-fixture manifest
    when ``allow_test_fixture`` is set; the production path builds a ``VLLMServerRuntime`` on an
    allow-listed endpoint.
    """
    assets = settings.resolved_assets_dir
    manifest = load_manifest(assets / "manifests" / settings.manifest_name)
    if manifest.test_fixture and not settings.allow_test_fixture:
        raise LLMFailure(
            LLMErrorCode.INVALID_CONFIGURATION,
            "a test-fixture manifest is refused unless allow_test_fixture is set",
        )
    template = ChatTemplate.from_manifest(manifest, assets)
    if runtime is None:
        if manifest.runtime.name != "vllm":
            raise LLMFailure(
                LLMErrorCode.INVALID_CONFIGURATION,
                "only the vllm runtime can be built from settings; pass a runtime explicitly",
            )
        runtime = VLLMServerRuntime(
            settings.endpoint_url,
            settings.allowed_host_set,
            served_model_name=settings.served_model_name,
        )
    if not runtime.name.startswith(manifest.runtime.name):
        raise LLMFailure(
            LLMErrorCode.INVALID_CONFIGURATION,
            f"runtime {runtime.name!r} does not match the manifest's runtime",
        )
    return LLMService(settings, manifest, template, runtime, schemas=schemas)
