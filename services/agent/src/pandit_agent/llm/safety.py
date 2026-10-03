"""Output policy validation: the second layer behind the structured restrictions.

Hard product boundaries are not left to a natural-language instruction. The request carries the
restricted categories as typed values (the Phase 13 ``ProhibitedCategory`` vocabulary); the
prompt tells the model about them, **and** the generated text is scanned here against the same
closed lexicon the palm rules and knowledge use. A match in a restricted category is a typed
``POLICY_VIOLATION`` failure and the text is not returned.

Limits, stated plainly:

* the lexicon is English only. Hindi (Devanagari) and Hinglish (romanised) output is **not**
  covered by this scan: it is a known gap (``LEGAL_REVIEW_REQUIRED`` / ``CALIBRATION_REQUIRED``),
  not a claim of safety;
* a word list is a safety net, not proof that a text is acceptable;
* a prompt instruction does not guarantee compliance, which is why this layer exists.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from pandit_contracts.llm import LLMErrorCode
from pandit_contracts.palm_policy import ProhibitedCategory, find_prohibited

from pandit_agent.llm.errors import LLMFailure


def palm_restrictions() -> tuple[ProhibitedCategory, ...]:
    """Every Phase 13 prohibited category: the restriction set for any palmistry request."""
    return tuple(ProhibitedCategory)


def check_output(texts: Iterable[str], restrictions: Sequence[ProhibitedCategory]) -> None:
    """Raise ``POLICY_VIOLATION`` if any text hits a restricted category."""
    if not restrictions:
        return
    restricted = set(restrictions)
    hit: set[str] = set()
    for text in texts:
        for match in find_prohibited(text):
            if match.category in restricted:
                hit.add(match.category.value)
    if hit:
        raise LLMFailure(
            LLMErrorCode.POLICY_VIOLATION,
            "the generated text touches a restricted category: " + ", ".join(sorted(hit)),
        )
