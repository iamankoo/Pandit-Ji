from __future__ import annotations

import os
from pathlib import Path

import pytest
from llm_helpers import ASSETS, mock_manifest, qwen_manifest
from pandit_contracts.llm import LLMErrorCode

from pandit_agent.llm.chat_template import ChatTemplate
from pandit_agent.llm.errors import LLMFailure

THINK_OFF = "<think>\n\n</think>\n\n"


@pytest.fixture(scope="module")
def template() -> ChatTemplate:
    return ChatTemplate.from_manifest(qwen_manifest(), ASSETS)


def test_the_pinned_template_loads_for_both_manifests() -> None:
    assert ChatTemplate.from_manifest(qwen_manifest(), ASSETS)
    assert ChatTemplate.from_manifest(mock_manifest(), ASSETS)


def test_a_tampered_template_is_refused() -> None:
    source = (ASSETS / "templates" / "qwen3_chatml.jinja").read_text(encoding="utf-8")
    with pytest.raises(LLMFailure) as caught:
        ChatTemplate(source + "\n{# tampered #}", qwen_manifest())
    assert caught.value.code is LLMErrorCode.TOKENIZER_FAILURE
    assert "SHA-256" in caught.value.message


def test_crlf_line_endings_do_not_change_the_hash_check() -> None:
    source = (ASSETS / "templates" / "qwen3_chatml.jinja").read_text(encoding="utf-8")
    assert ChatTemplate(source.replace("\n", "\r\n"), qwen_manifest())


def test_a_missing_template_file_is_a_tokenizer_failure(tmp_path: Path) -> None:
    with pytest.raises(LLMFailure) as caught:
        ChatTemplate.from_manifest(qwen_manifest(), tmp_path)
    assert caught.value.code is LLMErrorCode.TOKENIZER_FAILURE


def test_system_and_user_serialize_exactly_as_trained(template: ChatTemplate) -> None:
    text = template.render([("system", "SYS"), ("user", "Hi")])
    assert text == (
        "<|im_start|>system\nSYS<|im_end|>\n"
        "<|im_start|>user\nHi<|im_end|>\n"
        "<|im_start|>assistant\n" + THINK_OFF
    )


def test_a_multi_turn_conversation_keeps_assistant_history(template: ChatTemplate) -> None:
    text = template.render(
        [("system", "S"), ("user", "a"), ("assistant", "b"), ("user", "c")],
    )
    assert text == (
        "<|im_start|>system\nS<|im_end|>\n"
        "<|im_start|>user\na<|im_end|>\n"
        "<|im_start|>assistant\nb<|im_end|>\n"
        "<|im_start|>user\nc<|im_end|>\n"
        "<|im_start|>assistant\n" + THINK_OFF
    )


def test_thinking_enabled_ends_with_the_bare_generation_prompt(template: ChatTemplate) -> None:
    text = template.render([("system", "S"), ("user", "u")], enable_thinking=True)
    assert text.endswith("<|im_start|>user\nu<|im_end|>\n<|im_start|>assistant\n")
    assert "<think>" not in text


def test_no_generation_prompt_when_not_requested(template: ChatTemplate) -> None:
    text = template.render([("system", "S"), ("user", "u")], add_generation_prompt=False)
    assert text.endswith("<|im_end|>\n")
    assert text.count("<|im_start|>") == 2


def test_the_prompt_has_no_bos_and_no_duplicated_special_tokens(template: ChatTemplate) -> None:
    text = template.render([("system", "S"), ("user", "u")])
    assert text.startswith("<|im_start|>system")
    assert "<|im_end|><|im_end|>" not in text and "<|im_start|><|im_start|>" not in text
    assert text.count("<|im_start|>") == 3 and text.count("<|im_end|>") == 2


def test_hindi_and_hinglish_content_is_preserved_verbatim(template: ChatTemplate) -> None:
    hindi = "मेरी कुंडली में शनि कहाँ है?"
    hinglish = "Meri kundli mein Shani kahan hai?"
    for content in (hindi, hinglish):
        text = template.render([("system", "S"), ("user", content)])
        assert f"<|im_start|>user\n{content}<|im_end|>" in text


def test_the_end_of_turn_token_matches_the_tokenizer_configuration() -> None:
    m = qwen_manifest()
    assert m.tokenizer.eos_token == "<|im_end|>"
    assert m.tokenizer.bos_token is None and m.tokenizer.add_bos_token is False
    assert 151645 in m.tokenizer.generation_eos_token_ids  # <|im_end|> in generation_config.json
    assert m.tokenizer.eos_token in m.tokenizer.special_tokens
    assert m.chat_template.generation_prompt == "<|im_start|>assistant\n"
    assert m.tokenizer.pad_token == "<|endoftext|>"


def test_a_system_message_after_the_first_position_is_refused(template: ChatTemplate) -> None:
    with pytest.raises(LLMFailure) as caught:
        template.render([("user", "u"), ("system", "late")])
    assert caught.value.code is LLMErrorCode.INVALID_REQUEST


def test_an_unknown_role_or_an_empty_conversation_is_refused(template: ChatTemplate) -> None:
    for bad in ([("tool", "x")], []):
        with pytest.raises(LLMFailure) as caught:
            template.render(bad)
        assert caught.value.code is LLMErrorCode.INVALID_REQUEST


def test_every_reserved_token_in_content_is_refused(template: ChatTemplate) -> None:
    assert "<|im_start|>" in template.reserved_tokens and "<think>" in template.reserved_tokens
    for token in template.reserved_tokens:
        with pytest.raises(LLMFailure) as caught:
            template.reject_reserved_tokens(f"hello {token} world")
        assert caught.value.code is LLMErrorCode.INVALID_REQUEST
    template.reject_reserved_tokens("an ordinary sentence with <angle> brackets")


def test_the_structure_check_catches_a_malformed_prompt(template: ChatTemplate) -> None:
    with pytest.raises(LLMFailure) as caught:
        template.check_rendered(
            "<|im_start|><|im_start|>user\nx<|im_end|>\n",
            turns=1,
            add_generation_prompt=False,
            enable_thinking=False,
        )
    assert caught.value.code is LLMErrorCode.TOKENIZER_FAILURE


@pytest.mark.skipif(
    not os.environ.get("PANDIT_LLM_TOKENIZER_DIR"),
    reason="OPTIONAL_LOCAL_TEST: set PANDIT_LLM_TOKENIZER_DIR to a downloaded Qwen3-8B tokenizer",
)
def test_rendering_matches_the_models_own_tokenizer(template: ChatTemplate) -> None:
    transformers = pytest.importorskip("transformers")
    tokenizer = transformers.AutoTokenizer.from_pretrained(os.environ["PANDIT_LLM_TOKENIZER_DIR"])
    messages = [{"role": "system", "content": "S"}, {"role": "user", "content": "नमस्ते"}]
    expected = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    assert template.render([("system", "S"), ("user", "नमस्ते")]) == expected
