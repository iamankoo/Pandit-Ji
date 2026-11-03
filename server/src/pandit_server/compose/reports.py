"""Report composition. A report contains only deterministic structure and **verified** claims.

For each requested domain it records the domain's structured result (support, status, typed
reasons, policy flags) and, when the language model is available and the domain is evaluable, the
claims that survived Phase 16 verification. Unverifiable or insufficient claims are stripped and
never presented as verified; a not-evaluable or policy-blocked domain is reported as such, with no
narration and no generic text.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from pandit_agent.orchestration import AgentConfig
from pandit_agent.orchestration.domain import classify_life_domain
from pandit_contracts.agent import AgentRequest, Domain
from pandit_contracts.domain import DomainStatus, LifeDomain

from pandit_server.compose import chat as pipeline
from pandit_server.compose import engines
from pandit_server.container import Container
from pandit_server.db.models import BirthProfile, Report, User

VALID_DOMAINS = frozenset(d.value for d in LifeDomain)


def _prompt(domain: LifeDomain) -> str:
    return f"Tell me about my {domain.value.replace('_', ' ').lower()}"


def generate_report(container: Container, report_id: uuid.UUID) -> None:
    with container.db.session() as session:
        report = session.get(Report, report_id)
        if report is None:
            return
        profile = session.get(BirthProfile, report.profile_id)
        user = session.get(User, report.user_id)
        if profile is None or user is None:
            return
        spec = dict(report.domains)
        domains = [LifeDomain(name) for name in spec["domains"]]
        language: str = spec.get("language", "EN")
        adult: bool | None = spec.get("subject_adult_confirmed")
        kundli_json, _ = engines.kundli_for(container, profile)
        dasha_json, _ = engines.dasha_for(container, profile, 3)
        sections: list[dict[str, Any]] = []
        versions: dict[str, Any] = {}
        for domain in domains:
            evidence = pipeline.build_evidence(
                kundli_json=kundli_json,
                dasha_json=dasha_json,
                message=_prompt(domain),
                adult_confirmed=adult,
                analysis_id=f"rep-{report.id.hex[:12]}-{domain.value.lower()}"[:64],
                forced_domain=domain,
            )
            result = evidence.domain_result
            assert result is not None
            versions = {
                "knowledge_version": result.versions.knowledge_version,
                "ruleset": result.versions.ruleset_ref,
            }
            narration: dict[str, Any] = {"state": "not_applicable", "claims": []}
            if result.status is DomainStatus.EVALUATED:
                narration = _narrate(container, evidence, domain, language)
            sections.append(
                {
                    "domain": domain.value,
                    "support": result.support.value,
                    "status": result.status.value,
                    "reasons": [r.code.value for r in result.reasons],
                    "policy_flags": [p.value for p in result.policy_flags],
                    "evidence_count": len(result.facts) + len(result.rules),
                    "narration": narration,
                }
            )
        report.content = {
            "profile_id": str(profile.id),
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "versions": {**versions, **engines.engine_versions()},
            "sections": sections,
            "verification": {"released": "verified_claims_only"},
            "disclaimer": "Traditional interpretation; not a prediction, guarantee or advice.",
        }
        report.status = "ready"


def _narrate(
    container: Container, evidence: pipeline.Evidence, domain: LifeDomain, language: str
) -> dict[str, Any]:
    prompt = _prompt(domain)
    if classify_life_domain(prompt) is not domain:
        return {"state": "unavailable", "reason": "no_routing_for_domain", "claims": []}
    try:
        llm = container.llm()
    except Exception:  # noqa: BLE001 - the model being unavailable never fails a report
        return {"state": "unavailable", "reason": "llm_unavailable", "claims": []}
    outcome = pipeline.run_verified_chat(
        llm=llm,
        evidence=evidence,
        request=AgentRequest(
            request_id=uuid.uuid4().hex,
            language=pipeline.language_of(language),
            user_text=prompt,
            domain=Domain.ASTROLOGY,
        ),
        max_regenerations=container.settings.chat_max_regenerations,
        config=AgentConfig(max_evidence_items=container.settings.chat_max_evidence_items),
    )
    if outcome.claims:
        return {
            "state": "verified",
            "claims": outcome.claims,
            "release_action": outcome.final_action,
            "attempts": len(outcome.attempts),
        }
    return {
        "state": "unavailable",
        "reason": outcome.error_code or "no_verified_content",
        "claims": [],
    }
