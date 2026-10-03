"""Shared helpers for the LLM tests.

Every service built here uses the scripted ``MockRuntime`` unless a test says otherwise. The mock
is a deterministic test double, not a language model: nothing here says anything about real model
quality.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pandit_contracts.llm import (
    EvidenceItem,
    GenerationConfig,
    LLMContext,
    LLMLanguage,
    LLMMessage,
    LLMRequest,
    MessageRole,
    OutputMode,
    OutputSpec,
)
from pandit_contracts.palm_policy import ProhibitedCategory

from pandit_agent.llm.chat_template import ChatTemplate
from pandit_agent.llm.manifest import ModelManifest, load_manifest
from pandit_agent.llm.mock_runtime import MockRuntime, Scripted
from pandit_agent.llm.service import LLMService
from pandit_agent.llm.settings import LLMSettings, generation_profile
from pandit_agent.llm.structured import SchemaRegistry

ASSETS = Path(__file__).resolve().parents[1] / "llm"
MANIFESTS = ASSETS / "manifests"
MOCK_MANIFEST = "mock-deterministic-test.json"
QWEN_MANIFEST = "qwen3-8b.json"
MOCK_MODEL_ID = "pandit-mock-deterministic"
QWEN_MODEL_ID = "Qwen/Qwen3-8B"


def settings(**over: Any) -> LLMSettings:
    base: dict[str, Any] = {
        "assets_dir": ASSETS,
        "manifest_name": MOCK_MANIFEST,
        "allow_test_fixture": True,
    }
    base.update(over)
    return LLMSettings(**base)


def mock_manifest() -> ModelManifest:
    return load_manifest(MANIFESTS / MOCK_MANIFEST)


def qwen_manifest() -> ModelManifest:
    return load_manifest(MANIFESTS / QWEN_MANIFEST)


def manifest_dict(name: str = QWEN_MANIFEST) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((MANIFESTS / name).read_text(encoding="utf-8"))
    return data


def write_manifest(tmp_path: Path, data: dict[str, Any], name: str = "m.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def make_service(
    script: Sequence[Scripted] = (),
    *,
    start: bool = True,
    runtime: MockRuntime | None = None,
    manifest: ModelManifest | None = None,
    schemas: SchemaRegistry | None = None,
    **settings_over: Any,
) -> tuple[LLMService, MockRuntime]:
    rt = runtime if runtime is not None else MockRuntime(script)
    mf = manifest if manifest is not None else mock_manifest()
    cfg = settings(**settings_over)
    service = LLMService(cfg, mf, ChatTemplate.from_manifest(mf, ASSETS), rt, schemas=schemas)
    if start:
        service.start()
    return service, rt


def gen(**over: Any) -> GenerationConfig:
    base = generation_profile("deterministic").model_dump()
    base.update({"max_new_tokens": 64}, **over)
    return GenerationConfig(**base)


def request(
    text: str = "What does my chart say?",
    *,
    language: LLMLanguage = LLMLanguage.EN,
    request_id: str = "req-1",
    model_id: str = MOCK_MODEL_ID,
    evidence: Sequence[EvidenceItem] = (),
    restrictions: Sequence[ProhibitedCategory] = (),
    schema_id: str | None = None,
    generation: GenerationConfig | None = None,
    history: Sequence[LLMMessage] = (),
) -> LLMRequest:
    context = (
        LLMContext(context_version="ctx-1", items=tuple(evidence), restrictions=tuple(restrictions))
        if evidence or restrictions
        else None
    )
    output = OutputSpec(mode=OutputMode.JSON, schema_id=schema_id) if schema_id else OutputSpec()
    return LLMRequest(
        request_id=request_id,
        model_id=model_id,
        language=language,
        messages=(*history, LLMMessage(role=MessageRole.USER, content=text)),
        context=context,
        generation=generation or gen(),
        output=output,
    )


def fact(evidence_id: str = "F1", content: str = "fact_type=HAND_SIDE; value=LEFT") -> EvidenceItem:
    return EvidenceItem(evidence_id=evidence_id, kind="PALM_FACT", content=content)
