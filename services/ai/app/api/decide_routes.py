"""Stateless decision endpoint — specs/ai-decide/spec.md.

The only way domain-facing services (chat, and whatever comes after it)
obtain LLM reasoning. Holds no conversation state and makes no outbound
calls to any domain service — BYOK provider resolution and rate limiting
are the only things this route does beyond calling decide_service.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic_ai.exceptions import AgentRunError

from app.core.logging import get_logger
from app.services.decide_service import decide
from app.services.provider import ResolvedModel, get_resolved_model
from app.services.rate_limiter import enforce_rate_limit
from app.utils.security import get_validated_user, resolve_customer_id
from shared.ai_client.schemas import DecideRequest, ToolCall

logger = get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Decide"])


@router.post("/decide")
async def decide_route(
    body: DecideRequest,
    valid_user=Depends(get_validated_user),
    resolved: ResolvedModel | None = Depends(get_resolved_model),
):
    customer_id = resolve_customer_id(valid_user)
    user_id = str(valid_user["user_id"])

    if resolved is None:
        raise HTTPException(status_code=503, detail={"code": "no_provider"})

    await enforce_rate_limit(customer_id)

    try:
        decision = await decide(
            resolved_model=resolved,
            message=body.message,
            history=body.conversation_history,
            tools=body.available_tools,
            domain_context=body.domain_context,
            customer_id=customer_id,
            user_id=user_id,
        )
    except AgentRunError as exc:
        logger.error("decide_model_error", customer_id=customer_id, error=str(exc))
        raise HTTPException(status_code=502, detail={"code": "model_error"}) from exc

    if isinstance(decision, ToolCall):
        return {"decision": {"type": "tool_call", "name": decision.name, "params": decision.params}}
    return {"decision": {"type": "reply", "text": decision.text}}
