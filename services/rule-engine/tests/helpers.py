"""Shared test helpers: minimal valid rule documents."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def rule_doc(**overrides: Any) -> dict[str, Any]:
    """A minimal valid rule document (Jupiter in a kendra from the Lagna)."""
    doc: dict[str, Any] = {
        "document_type": "rule",
        "rule_id": "TEST_SAN_JUPITER_KENDRA",
        "rule_version": "1",
        "astrology_system": "vedic_parashari",
        "school": "parashari",
        "profile": "TEST_SAN_JUPITER_KENDRA",
        "category": "yoga",
        "source": "Test Work",
        "source_id": "TEST_WORK",
        "source_edition": "Test edition",
        "translator": "Test translator",
        "source_location": "Ch. 1 v. 1",
        "source_version": "1",
        "source_tier": 2,
        "verification_level": "OCR-TRANSLATION",
        "standards_version": "1.4.0",
        "confidence": "MEDIUM",
        "status": "active",
        "priority": 100,
        "readings": [
            {
                "reading_id": "R1",
                "basis": "translation",
                "conditions": {
                    "op": "planet_house",
                    "planet": "jupiter",
                    "reference": "lagna",
                    "houses": [1, 4, 7, 10],
                },
            }
        ],
        "interpretation_tags": {
            "domain": ["general"],
            "signification": ["test.signal"],
            "effect_class": "supportive",
        },
    }
    for key, value in overrides.items():
        doc[key] = deepcopy(value)
    return doc


def manifest_doc(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "document_type": "ruleset",
        "ruleset_id": "TEST_RULESET",
        "ruleset_version": "1.0.0",
        "schema_version": 1,
        "standards_version": "1.4.0",
    }
    doc.update(overrides)
    return doc


def write_ruleset(root: Any, documents: dict[str, dict[str, Any]]) -> Any:
    """Write `{relative path: document}` as YAML under `root` and return it."""
    import yaml

    for relative, document in documents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return root


class StubDerived:
    """Derived facts for evaluator tests: natures and relationships are given."""

    def __init__(
        self,
        natures: dict[str, str] | None = None,
        relations: dict[tuple[str, str, str], str] | None = None,
        moolatrikona: dict[str, bool] | None = None,
    ) -> None:
        self._moolatrikona = moolatrikona or {}
        self._natures = natures or {}
        self._relations = relations or {}

    def natural_nature(self, body: Any) -> Any:
        from pandit_rule_engine.conditions import NatureValue
        from pandit_rule_engine.vocab import Reason

        value = self._natures.get(body.value, "benefic")
        if value in ("benefic", "malefic"):
            return NatureValue(value)
        return NatureValue(value, Reason.READING_AMBIGUOUS, f"nature.{body.value}")

    def moolatrikona(self, body: Any) -> Any:
        from pandit_rule_engine.conditions import MoolatrikonaValue

        return MoolatrikonaValue(self._moolatrikona.get(body.value, False))

    def relationship(self, basis: str, a: Any, b: Any) -> Any:
        from pandit_rule_engine.conditions import RelationValue

        return RelationValue(self._relations.get((basis, a.value, b.value), "equal"))


def evaluate_doc(
    doc: dict[str, Any],
    facts: Any,
    derived: Any = None,
    rule_results: Any = None,
) -> Any:
    """Parse a rule document and evaluate it against `facts`."""
    from pandit_rule_engine.conditions import EvalContext
    from pandit_rule_engine.evaluator import evaluate_rule
    from pandit_rule_engine.schema import Rule

    rule = Rule.model_validate(doc)
    context = EvalContext(
        facts=facts, derived=derived or StubDerived(), rule_results=rule_results or {}
    )
    return evaluate_rule(context, rule)


def rules_dir() -> Any:
    """The repository's ruleset directory (`services/knowledge/rules`)."""
    from pathlib import Path

    return Path(__file__).resolve().parents[2] / "knowledge" / "rules"
