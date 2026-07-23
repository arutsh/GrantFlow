import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.crud.conversation import (
    get_conversation_messages,
    get_or_create_conversation,
    list_conversations,
    load_history,
    save_turn,
    to_chat_turns,
)
from app.db.session import AsyncSessionLocal
from app.schemas.chat import (
    ChatStreamRequest,
    ConversationOut,
    MessageOut,
    ParseBudgetStreamRequest,
)
from app.services.chat_stream import build_chat_sse_stream
from app.services.orchestrator import TurnResult, run_turn
from app.services.parse_budget_stream import build_parse_budget_sse_stream
from shared.ai_client import AiRateLimitedError, AiUnavailableError
from shared.security.dependencies import get_validated_user

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

_SSE_HEADERS = {"X-Accel-Buffering": "no"}


def _resolve_customer_id(valid_user: dict) -> str:
    customer_id = valid_user.get("customer_id")
    return str(customer_id) if customer_id else str(valid_user["user_id"])


def _sse_frame(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _single_frame_stream(event: str, data: dict):
    yield _sse_frame(event, data)


@router.post("/stream")
async def stream_chat(
    body: ChatStreamRequest,
    request: Request,
    valid_user=Depends(get_validated_user),
):
    user_id = str(valid_user["user_id"])
    customer_id = _resolve_customer_id(valid_user)
    token = valid_user.get("token", "")

    async with AsyncSessionLocal() as db:
        conversation = await get_or_create_conversation(
            conversation_id=body.conversation_id,
            customer_id=customer_id,
            user_id=user_id,
            db=db,
        )
        conversation_id = str(conversation.id)
        history_rows = await load_history(conversation_id, db)
        history = to_chat_turns(history_rows)
        await db.commit()

    headers = {**_SSE_HEADERS, "X-Conversation-Id": conversation_id}

    try:
        turn_result = await run_turn(
            message=body.message,
            history=history,
            context_id=body.context_id,
            page=body.page,
            token=token,
            ai_client=request.app.state.ai_client,
            registry=request.app.state.tool_registry,
        )
    except AiUnavailableError:
        return StreamingResponse(
            _single_frame_stream(
                "unavailable",
                {
                    "message": "No AI provider is configured for your organisation. "
                    "Ask your admin to add an API key under Settings → AI."
                },
            ),
            media_type="text/event-stream",
            headers=headers,
        )
    except AiRateLimitedError as exc:
        raise HTTPException(
            status_code=429,
            detail="AI provider is rate limited. Try again later.",
            headers={"Retry-After": str(exc.retry_after)},
        )
    except Exception as exc:
        logger.exception(
            "chat_turn_error", conversation_id=conversation_id, error_type=type(exc).__name__
        )
        return StreamingResponse(
            _single_frame_stream("error", {"message": "An error occurred. Please try again."}),
            media_type="text/event-stream",
            headers=headers,
        )

    async def _on_complete(result: TurnResult):
        async with AsyncSessionLocal() as db:
            fresh_conversation = await get_or_create_conversation(
                conversation_id=conversation_id,
                customer_id=customer_id,
                user_id=user_id,
                db=db,
            )
            await save_turn(fresh_conversation, body.message, result, db)

    return StreamingResponse(
        build_chat_sse_stream(turn_result, _on_complete),
        media_type="text/event-stream",
        headers=headers,
    )


@router.post("/parse-budget/stream")
async def stream_parse_budget(
    body: ParseBudgetStreamRequest,
    request: Request,
    valid_user=Depends(get_validated_user),
):
    token = valid_user.get("token", "")
    events = request.app.state.ai_client.stream_parse_budget(body.text, token)

    # Primed here, before the StreamingResponse is created, for the same reason
    # /chat/stream resolves run_turn() eagerly: this is the point where the
    # upstream request is actually sent, so AiRateLimitedError can still become
    # a real HTTP 429 instead of arriving as an in-stream event.
    try:
        first_event = await events.__anext__()
    except StopAsyncIteration:
        first_event = None
    except AiRateLimitedError as exc:
        raise HTTPException(
            status_code=429,
            detail="AI provider is rate limited. Try again later.",
            headers={"Retry-After": str(exc.retry_after)},
        )
    except Exception as exc:
        logger.exception("parse_budget_prime_error", error_type=type(exc).__name__)
        return StreamingResponse(
            _single_frame_stream("error", {"message": "An error occurred. Please try again."}),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )

    async def _primed_events():
        if first_event is not None:
            yield first_event
        async for event in events:
            yield event

    return StreamingResponse(
        build_parse_budget_sse_stream(
            _primed_events(),
            http=request.app.state.http_client,
            budget_service_url=settings.BUDGET_SERVICE_URL,
            token=token,
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.get("/conversations")
async def list_conversations_route(
    valid_user=Depends(get_validated_user),
    limit: int = Query(50, ge=1, le=200),
) -> list[ConversationOut]:
    customer_id = _resolve_customer_id(valid_user)
    async with AsyncSessionLocal() as db:
        rows = await list_conversations(customer_id, db, limit=limit)
    return [ConversationOut.model_validate(row) for row in rows]


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages_route(
    conversation_id: str,
    valid_user=Depends(get_validated_user),
    limit: int = Query(200, ge=1, le=500),
) -> list[MessageOut]:
    customer_id = _resolve_customer_id(valid_user)
    async with AsyncSessionLocal() as db:
        rows = await get_conversation_messages(conversation_id, customer_id, db, limit=limit)
    if rows is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return [MessageOut.model_validate(row) for row in rows]
