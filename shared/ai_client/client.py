import asyncio
import json
from typing import AsyncIterator
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from shared.ai_client.errors import AiClientError, AiRateLimitedError, AiUnavailableError
from shared.ai_client.schemas import (
    AiDecision,
    ChatTurn,
    DecideRequest,
    ParseDone,
    ParseError,
    ParseEvent,
    ParseProgress,
    ParseUnavailable,
    Reply,
    ToolCall,
    ToolDef,
)
from shared.ai_client.sse import iter_sse_frames


class AiClient:
    """Calls ai's stateless `POST /ai/decide` (per `specs/ai-decide/spec.md`).

    One `AiClient` (and its underlying httpx client) is meant to be built
    once and reused across requests — construction is not per-call.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 60,
        connect_retries: int = 2,
        backoff_seconds: float = 0.5,
        http: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.connect_retries = connect_retries
        self.backoff_seconds = backoff_seconds
        self.http = http if http is not None else httpx.AsyncClient(timeout=timeout)

    async def decide(
        self,
        message: str,
        history: list[ChatTurn],
        tools: list[ToolDef],
        domain_context: dict | None,
        user_token: str,
    ) -> AiDecision:
        try:
            payload = DecideRequest(
                message=message,
                conversation_history=history,
                available_tools=tools,
                domain_context=domain_context,
            ).model_dump()
        except ValidationError as exc:
            raise AiClientError(f"Invalid decide() request: {exc}") from exc
        headers = {"Authorization": f"Bearer {user_token}"}

        resp = await self._post_with_retry(payload, headers)

        if resp.status_code == 503:
            raise AiUnavailableError()
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "0"))
            raise AiRateLimitedError(retry_after=retry_after)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AiClientError(
                f"ai service returned {exc.response.status_code}: {exc.response.text[:200]}",
                status_code=exc.response.status_code,
            ) from exc

        decision = resp.json()["decision"]
        if decision["type"] == "tool_call":
            return ToolCall(name=decision["name"], params=decision["params"])
        return Reply(text=decision["text"])

    async def stream_parse_budget(self, text: str, user_token: str) -> AsyncIterator[ParseEvent]:
        """Stream ai's `GET /ai/parse-budget/stream` (specs/chat-parse-budget.md).

        Callers should prime this with one `await gen.__anext__()` before
        starting their own StreamingResponse — that's the point where the
        upstream request is actually sent and its status checked, so a 429
        still surfaces as `AiRateLimitedError` rather than arriving mid-stream
        (the same "resolve eagerly" reasoning as decide()/run_turn()).

        A connection failure degrades to a yielded `ParseError`, matching the
        old budget-hosted proxy's behavior exactly (a graceful in-stream
        error, not an exception) — unlike the 429/5xx cases above, which are
        real request-level failures the caller is expected to handle.
        """
        headers = {"Authorization": f"Bearer {user_token}"}
        url = f"{self.base_url}/ai/parse-budget/stream?text={quote(text)}"

        try:
            async with self.http.stream("GET", url, headers=headers) as resp:
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "0"))
                    raise AiRateLimitedError(retry_after=retry_after)
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise AiClientError(
                        f"ai service returned {exc.response.status_code}: "
                        f"{exc.response.text[:200]}",
                        status_code=exc.response.status_code,
                    ) from exc

                async for event, data in iter_sse_frames(resp.aiter_text()):
                    if event == "progress":
                        yield ParseProgress(**json.loads(data))
                    elif event == "done":
                        yield ParseDone.model_validate_json(data)
                    elif event == "unavailable":
                        yield ParseUnavailable()
                    elif event == "error":
                        yield ParseError(message=data)
        except httpx.ConnectError:
            yield ParseError(message="Connection to AI service failed")

    async def _post_with_retry(self, payload: dict, headers: dict) -> httpx.Response:
        attempt = 0
        while True:
            try:
                return await self.http.post(
                    f"{self.base_url}/ai/decide", json=payload, headers=headers
                )
            except httpx.ConnectError as exc:
                attempt += 1
                if attempt > self.connect_retries:
                    raise AiClientError(f"Could not connect to ai service: {exc}") from exc
                await asyncio.sleep(self.backoff_seconds * attempt)
            except httpx.RequestError as exc:
                # Read timeouts and other non-connect failures are not retried —
                # LLM calls are not cheap to repeat blindly.
                raise AiClientError(f"Request to ai service failed: {exc}") from exc
