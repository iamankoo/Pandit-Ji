"""Phase 17 domain ruleset support (ADR-012): a ruleset separate from the Phase 6 Vedic ruleset.

The domain rules live in ``services/rule-engine/domain_rules/`` (never under the Vedic rules
directory), have their own manifest, version and content hash, and are loaded and evaluated only
by this package. See `docs/ASTROLOGY_STANDARDS.md` LD-01 to LD-27.
"""

from pandit_rule_engine.domain.evaluator import EVALUATOR_VERSION, evaluate_domain
from pandit_rule_engine.domain.inputs import VargaPlacements, varga_from_kundli
from pandit_rule_engine.domain.loader import (
    ALLOWED_VARGA_DOMAINS,
    DomainRuleset,
    DomainRulesetLoadError,
    load_domain_ruleset,
)

__all__ = [
    "ALLOWED_VARGA_DOMAINS",
    "EVALUATOR_VERSION",
    "DomainRuleset",
    "DomainRulesetLoadError",
    "VargaPlacements",
    "evaluate_domain",
    "load_domain_ruleset",
    "varga_from_kundli",
]
