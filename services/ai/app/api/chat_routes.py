import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.crud.chat_session import (
    db_messages_to_pydantic_ai,
    get_or_create_session,
    load_message_history,
    save_turn,
)
from app.db.session import AsyncSessionLocal
from app.services.chat_agent import ChatDeps, build_agent
from app.services.chat_orchestrator import TurnResult
from app.services.chat_stream import build_chat_sse_stream
from app.services.provider import ResolvedModel, get_resolved_model
from app.services.rate_limiter import check_and_increment
from app.utils.security import get_validated_user

router = APIRouter(prefix="/ai", tags=["AI Chat"])

_SSE_HEADERS = {
    "X-Accel-Buffering": "no",
    "X-RateLimit-Limit": str(settings.AI_RATE_LIMIT_PER_HOUR),
}


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    context_budget_id: str | None = None
    page: str | None = None


@router.post("/chat/stream")
async def stream_chat(
    body: ChatRequest,
    request: Request,
    valid_user=Depends(get_validated_user),
    resolved: ResolvedModel | None = Depends(get_resolved_model),
):
    user_id = str(valid_user["user_id"])
    customer_id = str(valid_user["customer_id"]) if valid_user.get("customer_id") else user_id
    token = valid_user.get("token", "")

    if resolved is None:

        async def _unavailable():
            yield (
                'event: unavailable\ndata: {"message": "No AI provider is configured for your '
                'organisation. Ask your admin to add an API key under Settings → AI."}\n\n'
            )

        return StreamingResponse(
            _unavailable(), media_type="text/event-stream", headers=_SSE_HEADERS
        )

    allowed, retry_after = await check_and_increment(customer_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(retry_after), **_SSE_HEADERS},
        )

    http_client: httpx.AsyncClient = request.app.state.http_client

    async with AsyncSessionLocal() as db:
        session = await get_or_create_session(
            session_id=body.session_id,
            customer_id=customer_id,
            user_id=user_id,
            db=db,
        )
        session_id = str(session.id)
        history_rows = await load_message_history(session_id, db)
        message_history = db_messages_to_pydantic_ai(history_rows)
        await db.commit()

    agent = build_agent(resolved)
    deps = ChatDeps(
        http=http_client,
        customer_id=customer_id,
        user_id=user_id,
        token=token,
        budget_service_url=settings.BUDGET_SERVICE_URL,
    )

    async def _on_complete(turn_result: TurnResult):
        async with AsyncSessionLocal() as db:
            fresh_session = await get_or_create_session(
                session_id=session_id,
                customer_id=customer_id,
                user_id=user_id,
                db=db,
            )
            await save_turn(
                session=fresh_session,
                user_text=body.message,
                new_messages=turn_result.new_messages,
                db=db,
            )

    return StreamingResponse(
        build_chat_sse_stream(
            agent=agent,
            message=body.message,
            deps=deps,
            message_history=message_history,
            context_budget_id=body.context_budget_id,
            on_complete=_on_complete,
            page=body.page,
        ),
        media_type="text/event-stream",
        headers={**_SSE_HEADERS, "X-Session-Id": session_id},
    )
