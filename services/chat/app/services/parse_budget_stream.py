"""SSE adapter for POST /chat/parse-budget/stream (specs/chat-parse-budget.md).

Consumes ai's parse stream via `AiClient.stream_parse_budget`, then on a
completed parse calls budget's public `POST /budgets/with-lines`, re-emitting
the same `progress`/`created`/`error`/`unavailable` events the frontend
already speaks — this is a drop-in replacement for the old budget-hosted
proxy, not a new contract.
"""

import json
from typing import AsyncIterator

import httpx

from app.core.logging import get_logger
from shared.ai_client import ParseDone, ParseError, ParseEvent, ParseProgress, ParseUnavailable
from shared.schemas.budget_with_lines_schema import CreateBudgetWithLinesRequest

logger = get_logger(__name__)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def build_parse_budget_sse_stream(
    events: AsyncIterator[ParseEvent],
    *,
    http: httpx.AsyncClient,
    budget_service_url: str,
    token: str,
) -> AsyncIterator[str]:
    async for event in events:
        if isinstance(event, ParseProgress):
            yield _sse("progress", {"status": event.status})
        elif isinstance(event, ParseUnavailable):
            yield _sse("unavailable", {})
        elif isinstance(event, ParseError):
            yield _sse("error", {"message": event.message})
        elif isinstance(event, ParseDone):
            yield _sse("progress", {"status": "Creating budget..."})
            async for frame in _create_budget(event, http, budget_service_url, token):
                yield frame


async def _create_budget(
    parsed: ParseDone, http: httpx.AsyncClient, budget_service_url: str, token: str
) -> AsyncIterator[str]:
    try:
        payload = CreateBudgetWithLinesRequest(
            budget_name=parsed.budget_name,
            external_funder_name=parsed.external_funder_name or "",
            duration_months=parsed.duration_months,
            lines=parsed.lines,
        )
        resp = await http.post(
            f"{budget_service_url.rstrip('/')}/budgets/with-lines",
            json=payload.model_dump(mode="json"),
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        yield _sse("created", {"budget_id": str(data["id"])})
    except Exception as exc:
        logger.error("parse_budget_creation_failed", error=str(exc))
        yield _sse("error", {"message": "Failed to create budget", "detail": str(exc)[:200]})
