"""A script heuristic for the requested language.

It checks the *script* of the output (Devanagari or Latin), nothing more. It cannot tell English
from romanised Hindi, and it says nothing about fluency, correctness or register. Real quality
needs an evaluation dataset and human review (``docs/ARCHITECTURE.md`` section 36). The result is
informational: a FAIL is reported on the response, it is not turned into a failure.
"""

from __future__ import annotations

from collections.abc import Iterable

from pandit_contracts.llm import LanguageCheck, LLMLanguage

_DEVANAGARI = range(0x0900, 0x0980)
_DEVANAGARI_MAX_IN_LATIN_MODES = 0.05
_DEVANAGARI_MIN_IN_HINDI = 0.30
_LATIN_MIN_IN_HINGLISH = 0.50


def _is_latin_letter(ch: str) -> bool:
    return ch.isalpha() and ord(ch) < 0x250


def script_ratios(texts: Iterable[str]) -> tuple[float, float, int]:
    """(devanagari share, latin share, letter count) over every letter in ``texts``."""
    letters = devanagari = latin = 0
    for text in texts:
        for ch in text:
            if not ch.isalpha():
                continue
            letters += 1
            if ord(ch) in _DEVANAGARI:
                devanagari += 1
            elif _is_latin_letter(ch):
                latin += 1
    if letters == 0:
        return 0.0, 0.0, 0
    return devanagari / letters, latin / letters, letters


def check_language(language: LLMLanguage, texts: Iterable[str]) -> LanguageCheck:
    devanagari, latin, letters = script_ratios(texts)
    if letters == 0:
        return LanguageCheck.NOT_CHECKED
    if language is LLMLanguage.HI:
        ok = devanagari >= _DEVANAGARI_MIN_IN_HINDI
    elif language is LLMLanguage.HINGLISH:
        ok = devanagari <= _DEVANAGARI_MAX_IN_LATIN_MODES and latin >= _LATIN_MIN_IN_HINGLISH
    else:
        ok = devanagari <= _DEVANAGARI_MAX_IN_LATIN_MODES
    return LanguageCheck.PASS if ok else LanguageCheck.FAIL
