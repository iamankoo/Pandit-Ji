"""Rule engine entry point (Phase 6): load a ruleset, evaluate a chart,
return an `EvidenceBundle`.

The engine consumes facts only. It never computes astronomy, performs no
network or file access during evaluation (the ruleset is loaded once, up
front), and produces the same bundle for the same chart, configuration,
ruleset hash and engine version.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pandit_rule_engine._version import __version__
from pandit_rule_engine.adapters import facts_from_kundli
from pandit_rule_engine.ashtakavarga_evidence import (
    AshtakavargaEvidence,
    ashtakavarga_evidence_from_facts,
)
from pandit_rule_engine.bundle import EvidenceBundle, build_bundle
from pandit_rule_engine.dasha_evidence import DashaEvidence, dasha_evidence_from_facts
from pandit_rule_engine.derived import TableDerivedFacts
from pandit_rule_engine.evaluator import evaluate_ruleset
from pandit_rule_engine.facts import ChartFacts
from pandit_rule_engine.loader import Ruleset, load_ruleset
from pandit_rule_engine.tables import Tables, build_tables
from pandit_rule_engine.transit_evidence import TransitEvidence, transit_evidence_from_facts


class RuleEngine:
    def __init__(self, ruleset: Ruleset) -> None:
        self.ruleset = ruleset
        self.tables: Tables = build_tables(ruleset.tables)

    @classmethod
    def from_directory(cls, rules_dir: Path) -> RuleEngine:
        return cls(load_ruleset(rules_dir))

    def evaluate(
        self,
        facts: ChartFacts,
        dasha: DashaEvidence | None = None,
        transit: TransitEvidence | None = None,
        ashtakavarga: AshtakavargaEvidence | None = None,
    ) -> EvidenceBundle:
        derived = TableDerivedFacts(facts, self.tables)
        results = evaluate_ruleset(self.ruleset, facts, derived)
        return build_bundle(
            ruleset=self.ruleset,
            facts=facts,
            results=results,
            derived_facts=derived.snapshot(),
            rule_engine_version=__version__,
            dasha=dasha,
            transit=transit,
            ashtakavarga=ashtakavarga,
        )

    def evaluate_kundli(
        self,
        kundli: Mapping[str, Any],
        dasha_facts: Mapping[str, Any] | None = None,
        transit_facts: Mapping[str, Any] | None = None,
        ashtakavarga_facts: Mapping[str, Any] | None = None,
        ashtakavarga_reduction_facts: Mapping[str, Any] | None = None,
    ) -> EvidenceBundle:
        """Evaluate a Phase 5 Kundli given in its JSON form. `dasha_facts` is an
        optional astro-engine `DashaFacts` (Phase 7), `transit_facts` an
        optional astro-engine `TransitFacts` (Phase 8), and `ashtakavarga_facts`
        an optional astro-engine `AshtakavargaFacts` for exactly one
        caller-selected profile (Phase 9 WP-A1), all in JSON form; they are
        recorded in the bundle, and no rule reads any of them yet.
        `ashtakavarga_reduction_facts` is an optional astro-engine
        `AshtakavargaReductionFacts` (WP-A2/A3) for the *same* profile and
        natal chart as `ashtakavarga_facts` -- it is ignored unless
        `ashtakavarga_facts` is also supplied, since reduction computation is
        opt-in and profile-scoped, never automatic."""
        dasha = None if dasha_facts is None else dasha_evidence_from_facts(dasha_facts)
        transit = None if transit_facts is None else transit_evidence_from_facts(transit_facts)
        ashtakavarga = (
            None
            if ashtakavarga_facts is None
            else ashtakavarga_evidence_from_facts(ashtakavarga_facts, ashtakavarga_reduction_facts)
        )
        return self.evaluate(facts_from_kundli(kundli), dasha, transit, ashtakavarga)
