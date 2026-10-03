"""The model's own chat template, pinned by hash, rendered exactly as the model was trained.

No generic prompt format is invented: the Jinja template text published with the model (at the
pinned revision) is vendored under ``services/agent/llm/templates/`` and its SHA-256 is recorded
in the manifest. A template that does not hash to the manifest value is refused. Rendering uses
the same sandboxed Jinja settings the model's tooling uses (``trim_blocks``, ``lstrip_blocks``).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from jinja2 import TemplateError
from jinja2.ext import loopcontrols
from jinja2.sandbox import ImmutableSandboxedEnvironment
from pandit_contracts.llm import LLMErrorCode

from pandit_agent.llm.errors import LLMFailure
from pandit_agent.llm.manifest import ModelManifest, normalized_sha256

_THINK_OFF = "<think>\n\n</think>\n\n"


def _tojson(value: Any, ensure_ascii: bool = False, **kwargs: Any) -> str:
    return json.dumps(value, ensure_ascii=ensure_ascii, **kwargs)


class ChatTemplate:
    def __init__(self, source: str, manifest: ModelManifest) -> None:
        if normalized_sha256(source) != manifest.chat_template.sha256:
            raise LLMFailure(
                LLMErrorCode.TOKENIZER_FAILURE,
                "chat template does not match the SHA-256 pinned in the manifest",
            )
        if manifest.tokenizer.eos_token not in source:
            raise LLMFailure(
                LLMErrorCode.TOKENIZER_FAILURE,
                "the chat template does not use the manifest's end-of-turn token",
            )
        env = ImmutableSandboxedEnvironment(
            trim_blocks=True, lstrip_blocks=True, extensions=[loopcontrols]
        )
        env.filters["tojson"] = _tojson
        try:
            self._template = env.from_string(source.replace("\r\n", "\n"))
        except TemplateError as exc:
            raise LLMFailure(
                LLMErrorCode.TOKENIZER_FAILURE, f"template does not compile: {exc}"
            ) from exc
        self._manifest = manifest

    @classmethod
    def from_manifest(cls, manifest: ModelManifest, assets_dir: Path) -> ChatTemplate:
        path = assets_dir / manifest.chat_template.file
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise LLMFailure(
                LLMErrorCode.TOKENIZER_FAILURE, f"cannot read the chat template: {exc}"
            ) from exc
        return cls(source, manifest)

    @property
    def reserved_tokens(self) -> tuple[str, ...]:
        tok = self._manifest.tokenizer
        return tuple(dict.fromkeys((*tok.special_tokens, *tok.reserved_added_tokens)))

    def render(
        self,
        messages: Sequence[tuple[str, str]],
        *,
        add_generation_prompt: bool = True,
        enable_thinking: bool = False,
    ) -> str:
        """Render ``(role, content)`` pairs. The first pair may be the system message."""
        roles = [role for role, _ in messages]
        if not messages or any(r not in {"system", "user", "assistant"} for r in roles):
            raise LLMFailure(LLMErrorCode.INVALID_REQUEST, "unsupported message roles")
        if "system" in roles[1:]:
            raise LLMFailure(LLMErrorCode.INVALID_REQUEST, "a system message may only come first")
        try:
            text = self._template.render(
                messages=[{"role": r, "content": c} for r, c in messages],
                add_generation_prompt=add_generation_prompt,
                enable_thinking=enable_thinking,
            )
        except TemplateError as exc:
            raise LLMFailure(
                LLMErrorCode.TOKENIZER_FAILURE, f"template failed to render: {exc}"
            ) from exc
        self.check_rendered(
            text,
            turns=len(messages),
            add_generation_prompt=add_generation_prompt,
            enable_thinking=enable_thinking,
        )
        return text

    def check_rendered(
        self, text: str, *, turns: int, add_generation_prompt: bool, enable_thinking: bool
    ) -> None:
        """Assert the rendered prompt has the trained structure and no duplicated tokens."""
        tok = self._manifest.tokenizer
        start, end = "<|im_start|>", tok.eos_token
        expected_starts = turns + (1 if add_generation_prompt else 0)
        problems: list[str] = []
        if text.count(start) != expected_starts:
            problems.append(
                f"expected {expected_starts} turn-start tokens, found {text.count(start)}"
            )
        if text.count(end) != turns:
            problems.append(f"expected {turns} end-of-turn tokens, found {text.count(end)}")
        for token in (start, end):
            if token + token in text:
                problems.append(f"duplicated special token {token}")
        if tok.bos_token and text.startswith(tok.bos_token):
            problems.append("a BOS token was added although the tokenizer adds none")
        if add_generation_prompt:
            tail = self._manifest.chat_template.generation_prompt
            if not enable_thinking and self._manifest.chat_template.supports_enable_thinking:
                tail += _THINK_OFF
            if not text.endswith(tail):
                problems.append("the prompt does not end with the generation prompt")
        if problems:
            raise LLMFailure(LLMErrorCode.TOKENIZER_FAILURE, "; ".join(problems))

    def reject_reserved_tokens(self, text: str) -> None:
        """User-supplied text must not contain control tokens: the server would parse them."""
        for token in self.reserved_tokens:
            if token in text:
                raise LLMFailure(
                    LLMErrorCode.INVALID_REQUEST,
                    "content contains a reserved model token and was refused",
                )
