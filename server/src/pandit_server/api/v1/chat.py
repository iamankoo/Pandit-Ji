"""AI chat: the approved pipeline end to end (Phase 15 agent -> Phase 16 verifier -> bounded
regeneration), over the caller's own birth profile. The model is the locked self-hosted Qwen3-8B on
vLLM behind the Phase 14 service; there is no hosted fallback. If it is unavailable the answer is a
typed ``503 llm_unavailable``.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from pandit_agent.orchestration import AgentConfig
from pandit_contracts.agent import AgentRequest, Domain

from pandit_server.api.v1.profiles import owned_profile
from pandit_server.compose import chat as pipeline
from pandit_server.compose import engines
from pandit_server.compose.profiles import require_birth_time
from pandit_server.container import Container
from pandit_server.db.models import BirthProfile, Conversation, Message, User
from pandit_server.deps import ContainerDep, SessionDep, UserDep, limited
from pandit_server.errors import ApiError
from pandit_server.platform_services import record_audit
from pandit_server.schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


def llm_or_503(container: Container) -> Any:
    try:
        return container.llm()
    except Exception as exc:  # noqa: BLE001 - any failure to build the provider is "unavailable"
        container.metrics.inc("llm_unavailable_total")
        raise ApiError(
            503, "llm_unavailable", "The language model is currently unavailable."
        ) from exc


def answer(
    container: Container,
    profile: BirthProfile,
    body: ChatRequest,
    request_id: str,
) -> pipeline.ChatOutcome:
    """Run the full pipeline for one message (also used by the WebSocket and report jobs)."""
    require_birth_time(profile)
    kundli_json, _ = engines.kundli_for(container, profile)
    dasha_json, _ = engines.dasha_for(container, profile, 3)
    evidence = pipeline.build_evidence(
        kundli_json=kundli_json,
        dasha_json=dasha_json,
        message=body.message,
        adult_confirmed=body.subject_adult_confirmed,
        analysis_id=request_id[:64],
    )
    llm = llm_or_503(container)
    outcome = pipeline.run_verified_chat(
        llm=llm,
        evidence=evidence,
        request=AgentRequest(
            request_id=request_id[:64],
            language=pipeline.language_of(body.language),
            user_text=body.message,
            domain=Domain.ASTROLOGY,
        ),
        max_regenerations=container.settings.chat_max_regenerations,
        config=AgentConfig(max_evidence_items=container.settings.chat_max_evidence_items),
    )
    metrics = container.metrics
    metrics.inc("chat_requests_total", status=outcome.status)
    for attempt in outcome.attempts:
        metrics.inc("verification_actions_total", action=attempt.action)
        for status, count in attempt.counts.items():
            metrics.inc("verification_claims_total", count, status=status)
    metrics.inc("regenerations_total", max(0, len(outcome.attempts) - 1))
    return outcome


def outcome_payload(
    outcome: pipeline.ChatOutcome, conversation_id: uuid.UUID | None
) -> dict[str, Any]:
    return {
        "status": outcome.status,
        "language_user_message": outcome.user_message,
        "claims": outcome.claims,
        "disclaimers": outcome.disclaimers,
        "life_domain": outcome.life_domain,
        "versions": outcome.versions,
        "verification": {
            "release_action": outcome.final_action,
            "report_hash": outcome.report_hash,
            "attempts": [
                {
                    "action": a.action,
                    "claim_status_counts": a.counts,
                    "agent_status": a.agent_status,
                }
                for a in outcome.attempts
            ],
            "released": "verified_claims_only",
        },
        "error_code": outcome.error_code,
        "conversation_id": str(conversation_id) if conversation_id else None,
    }


@router.post("", dependencies=[Depends(limited("expensive"))])
def post_chat(
    body: ChatRequest,
    request: Request,
    user: UserDep,
    session: SessionDep,
    container: ContainerDep,
) -> Any:
    if body.profile_id is None:
        raise ApiError(422, "profile_required", "Choose a birth profile for this question.")
    profile = owned_profile(session, user, body.profile_id)
    request_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
    outcome = answer(container, profile, body, request_id)
    conversation_id = _remember(session, user, body, outcome)
    record_audit(
        session,
        subject=user.subject,
        action="chat.request",
        resource_type="conversation",
        resource_id=str(conversation_id) if conversation_id else None,
        request_id=request_id,
        outcome=outcome.status,
    )
    payload = outcome_payload(outcome, conversation_id)
    if outcome.status == "failed":
        if outcome.error_code in {"LLM_UNAVAILABLE", "LLM_TIMEOUT", "LLM_FAILURE"}:
            raise ApiError(503, "llm_unavailable", "The language model is currently unavailable.")
        raise ApiError(
            502,
            "generation_failed",
            "No verified answer could be produced; please try again.",
            details={"reason": outcome.error_code},
        )
    return payload


def _remember(
    session: SessionDep, user: User, body: ChatRequest, outcome: pipeline.ChatOutcome
) -> uuid.UUID | None:
    """Persist the verified answer only for a user who consented to memory; never the question."""
    if not user.memory_consent:
        return None
    conversation = None
    if body.conversation_id is not None:
        conversation = session.get(Conversation, body.conversation_id)
        if conversation is not None and conversation.user_id != user.id:
            conversation = None
    if conversation is None:
        conversation = Conversation(user_id=user.id, language=body.language)
        session.add(conversation)
        session.flush()
    session.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content={"claims": outcome.claims, "status": outcome.status},
        )
    )
    return conversation.id
