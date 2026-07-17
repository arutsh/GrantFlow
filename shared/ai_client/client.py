import asyncio

import httpx

from shared.ai_client.errors import AiClientError, AiRateLimitedError, AiUnavailableError
from shared.ai_client.schemas import AiDecision, ChatTurn, Reply, ToolCall, ToolDef


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
        payload = {
            "message": message,
            "conversation_history": [turn.model_dump() for turn in history],
            "available_tools": [tool.model_dump() for tool in tools],
            "domain_context": domain_context,
        }
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
