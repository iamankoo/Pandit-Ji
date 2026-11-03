"""A scripted language-model test double built on the Phase 14 service and its test runtime.

It is a deterministic stand-in (not a model, no weights, no hosted API) used only in tests. Nothing
in these tests says anything about real-model quality: real Qwen3-8B inference has not been run.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pandit_agent.llm.mock_runtime import MockRuntime
from pandit_agent.llm.service import create_service
from pandit_agent.llm.settings import LLMSettings
from pandit_agent.orchestration import narration_schema_registry

CAREER_RULE = "DOM_CAREER_HOUSE_10_P11"
GOOD_TEXT = "The tenth house of the chart is traditionally relevant to career."


def claim(text: str, ids: list[str], ctype: str = "TRADITIONAL_INTERPRETATION") -> dict[str, Any]:
    return {"text": text, "claim_type": ctype, "evidence_ids": ids}


def narration(*claims: dict[str, Any]) -> str:
    return json.dumps({"sections": [{"heading": "Reading", "claims": list(claims)}]})


GOOD = narration(claim(GOOD_TEXT, [CAREER_RULE]))


def scripted_llm(script: list[str]) -> tuple[Callable[[], Any], MockRuntime]:
    runtime = MockRuntime(script)

    def factory() -> Any:
        settings = LLMSettings(
            manifest_name="mock-deterministic-test.json", allow_test_fixture=True
        )
        service = create_service(settings, runtime, schemas=narration_schema_registry())
        service.start()
        return service

    return factory, runtime
