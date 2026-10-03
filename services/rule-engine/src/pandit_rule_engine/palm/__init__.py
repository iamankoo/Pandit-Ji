"""Palm ruleset support (Phase 13): a ruleset separate from the Phase 6 Vedic ruleset.

The palm rules live in ``services/rule-engine/palm_rules/`` (never under the Vedic rules
directory), have their own manifest and version, and are loaded and evaluated only by this
package. See `docs/ASTROLOGY_STANDARDS.md` PM-12, PM-20, PM-25 to PM-29 and ADR-008.
"""

from pandit_rule_engine.palm.evaluator import evaluate_palm_rules, evaluate_rule
from pandit_rule_engine.palm.loader import PalmRuleset, PalmRulesetLoadError, load_palm_ruleset

__all__ = [
    "PalmRuleset",
    "PalmRulesetLoadError",
    "evaluate_palm_rules",
    "evaluate_rule",
    "load_palm_ruleset",
]
