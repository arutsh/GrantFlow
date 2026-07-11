"""SSE adapter: maps the turn-orchestrator's result to the GrandFlow wire format.

SSE event types emitted:
  thinking      — turn has started
  tool_call     — the orchestrator is about to call the budget service
  action_result — the budget-service call returned
  text          — the reply shown to the user
  done          — stream complete
  error         — unrecoverable error
  unavailable   — no AI provider configured

Each frame:  event: <type>\\ndata: <json>\\n\\n

Unlike the earlier tool-calling design, tool_call/action_result are no longer
driven by the model — the model only classifies intent (see chat_agent.py's
module docstring). They're emitted here, by code, only when the orchestrator
actually decided to call the budget service.

Design note: DB persistence happens inside the generator (after `event: done`)
so it stays within the StreamingResponse scope and doesn't need a shared state hack.
"""

import json
from typing import AsyncIterator, Awaitable, Callable

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage

from app.core.logging import get_logger
from app.schemas.chat_intent_schema import TurnIntent
from app.services.chat_agent import ChatDeps
from app.services.chat_orchestrator import TurnResult, run_turn

logger = get_logger(__name__)


def _sse(event: str, data: dict | None = None) -> str:
    return f"event: {event}\ndata: {json.dumps(data or {})}\n\n"


async def build_chat_sse_stream(
    agent: "Agent[None, TurnIntent]",
    message: str,
    deps: ChatDeps,
    message_history: list[ModelMessage],
    context_budget_id: str | None,
    on_complete: Callable[[TurnResult], Awaitable[None]],
    page: str | None = None,
) -> AsyncIterator[str]:
    """Run one turn and yield SSE frames.

    Args:
        agent: Freshly built PydanticAI intent-extraction agent for this request.
        message: The user's turn text.
        deps: Chat dependencies (httpx client, token, URLs) used by the REST helpers.
        message_history: Prior messages for this session loaded from DB.
        context_budget_id: The budget the client's current page is working on, if any.
        on_complete: Async callback called with the TurnResult after the turn
                     completes. Used by the route handler to persist messages —
                     runs before `event: done` so the connection stays open
                     during the write.
        page: Optional client hint about which part of the app the user is on.

    The `done` event carries `budget_id` when the turn acted on or created a
    budget — the client stores it and sends it back as context_budget_id on
    subsequent turns (the server keeps no budget state).
    """
    try:
        yield _sse("thinking")

        turn_result = await run_turn(agent, message, deps, message_history, context_budget_id, page)

        if turn_result.tool_name:
            yield _sse("tool_call", {"tool_name": turn_result.tool_name})
            yield _sse(
                "action_result",
                {"tool_name": turn_result.tool_name, "output": turn_result.tool_output},
            )

        yield _sse("text", {"delta": turn_result.reply})

        await on_complete(turn_result)

        done_data: dict = {"response": turn_result.reply}
        if turn_result.budget_id:
            done_data["budget_id"] = turn_result.budget_id
        yield _sse("done", done_data)

    except Exception as exc:
        logger.error("chat_stream_error", error=str(exc))
        yield _sse("error", {"message": "An error occurred. Please try again."})
