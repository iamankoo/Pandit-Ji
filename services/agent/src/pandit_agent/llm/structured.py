"""Structured (JSON) output: registered schemas, strict parsing, validation after generation.

The runtime may constrain decoding to a schema (vLLM does), but that is an optimisation, not the
guarantee: the guarantee is that the text is parsed strictly and validated against the registered
schema *after* generation, and that anything else becomes an explicit typed failure. No fence
stripping, no "repair", no coercion: a malformed or non-conforming answer is never turned into a
valid-looking result.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from pandit_contracts.llm import LLMErrorCode

from pandit_agent.llm.errors import LLMFailure

ANSWER_WITH_EVIDENCE_REFS_V1 = "pj.answer_with_evidence_refs.v1"

_BUILTIN_SCHEMAS: dict[str, dict[str, Any]] = {
    ANSWER_WITH_EVIDENCE_REFS_V1: {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["answer", "evidence_refs"],
        "properties": {
            "answer": {"type": "string", "minLength": 1},
            "evidence_refs": {"type": "array", "items": {"type": "string", "minLength": 1}},
        },
    }
}


class SchemaRegistry:
    """Output schemas a caller may ask for by id. Later phases register their own."""

    def __init__(self) -> None:
        self._schemas: dict[str, dict[str, Any]] = {}
        for schema_id, schema in _BUILTIN_SCHEMAS.items():
            self.register(schema_id, schema)

    def register(self, schema_id: str, schema: dict[str, Any]) -> None:
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            raise LLMFailure(
                LLMErrorCode.UNSUPPORTED_OUTPUT_SCHEMA, f"invalid JSON Schema: {exc.message}"
            ) from exc
        self._schemas[schema_id] = schema

    def get(self, schema_id: str) -> dict[str, Any]:
        try:
            return self._schemas[schema_id]
        except KeyError as exc:
            raise LLMFailure(
                LLMErrorCode.UNSUPPORTED_OUTPUT_SCHEMA, f"unknown output schema {schema_id!r}"
            ) from exc

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._schemas))


def _reject_constant(name: str) -> Any:
    raise ValueError(f"non-standard JSON constant {name}")


def parse_and_validate(text: str, schema: dict[str, Any]) -> dict[str, Any] | list[Any]:
    """Strictly parse ``text`` as JSON and validate it. Raises a typed failure otherwise."""
    try:
        value = json.loads(text, parse_constant=_reject_constant)
    except ValueError as exc:
        raise LLMFailure(
            LLMErrorCode.MALFORMED_STRUCTURED_OUTPUT,
            "the output is not valid JSON",
            retryable=True,
        ) from exc
    if not isinstance(value, dict | list):
        raise LLMFailure(
            LLMErrorCode.MALFORMED_STRUCTURED_OUTPUT,
            "the output is JSON but not an object or array",
            retryable=True,
        )
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        where = "/".join(str(p) for p in first.path) or "(root)"
        raise LLMFailure(
            LLMErrorCode.SCHEMA_MISMATCH,
            f"the output does not match the schema at {where}: {first.validator}",
            retryable=True,
        )
    return value


def string_leaves(value: Any) -> Iterator[str]:
    """Every string value in a parsed document (keys are schema-controlled, values are not)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from string_leaves(item)
    elif isinstance(value, list):
        for item in value:
            yield from string_leaves(item)
