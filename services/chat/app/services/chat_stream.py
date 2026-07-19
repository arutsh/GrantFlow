"""SSE adapter: replays an already-resolved TurnResult as the GrandFlow wire
format (specs/chat-streaming/spec.md).

The turn itself (ai/decide call + guards + dispatch) is resolved by
orchestrator.run_turn() *before* this generator starts — see chat_routes.py
for why (AiRateLimitedError needs to become an HTTP 429, which is only
possible before the StreamingResponse is constructed). By the time this
generator runs, nothing here can fail except the DB write in `on_complete`.
"""

import json
from typing import AsyncIterator, Awaitable, Callable

from app.core.logging import get_logger
from app.services.orchestrator import TurnResult

logger = get_logger(__name__)


def _sse(event: str, data: dict | None = None) -> str:
    return f"event: {event}\ndata: {json.dumps(data or {})}\n\n"


async def build_chat_sse_stream(
    turn_result: TurnResult,
    on_complete: Callable[[TurnResult], Awaitable[None]],
) -> AsyncIterator[str]:
    try:
        yield _sse("thinking")

        if turn_result.tool_name:
            yield _sse("tool_call", {"tool_name": turn_result.tool_name})
            yield _sse(
                "action_result",
                {"tool_name": turn_result.tool_name, "output": turn_result.tool_result},
            )

        # Persist before showing the reply: if this raises, we fall to the
        # except below and the client only ever sees `error` — never a reply
        # that then silently fails to save (turn would look successful to
        # the user but vanish from history).
        await on_complete(turn_result)

        yield _sse("text", {"delta": turn_result.reply})

        done_data: dict = {"response": turn_result.reply}
        if turn_result.created_resource_id:
            done_data["budget_id"] = turn_result.created_resource_id
        yield _sse("done", done_data)

    except Exception as exc:
        logger.error("chat_stream_error", error=str(exc))
        yield _sse("error", {"message": "An error occurred. Please try again."})
