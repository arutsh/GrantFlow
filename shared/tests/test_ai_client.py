"""Tests for shared/ai_client per specs/ai-client/spec.md.

Uses httpx.MockTransport to exercise real httpx exception behavior (connect
errors vs read timeouts) rather than mocking AsyncClient directly.
"""

import httpx
import pytest

from shared.ai_client.client import AiClient
from shared.ai_client.errors import AiClientError, AiRateLimitedError, AiUnavailableError
from shared.ai_client.schemas import ChatTurn, Reply, ToolCall, ToolDef


def _client(handler, **kwargs) -> AiClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    return AiClient(base_url="http://ai-svc", http=http, **kwargs)


def _history() -> list[ChatTurn]:
    return [ChatTurn(role="user", content="hi")]


def _tools() -> list[ToolDef]:
    return [ToolDef(name="create_budget", description="Create a budget", parameters={})]


class TestDecisionParsing:
    @pytest.mark.anyio
    async def test_tool_call_parsed(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "decision": {
                        "type": "tool_call",
                        "name": "create_budget",
                        "params": {"budget_name": "USAID Grant"},
                    }
                },
            )

        client = _client(handler)
        result = await client.decide("make a budget", _history(), _tools(), None, "tok")

        assert isinstance(result, ToolCall)
        assert result.name == "create_budget"
        assert result.params == {"budget_name": "USAID Grant"}

    @pytest.mark.anyio
    async def test_reply_parsed(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"decision": {"type": "reply", "text": "What's the funder name?"}}
            )

        client = _client(handler)
        result = await client.decide("make a budget", _history(), _tools(), None, "tok")

        assert isinstance(result, Reply)
        assert result.text == "What's the funder name?"


class TestErrorMapping:
    @pytest.mark.anyio
    async def test_503_raises_unavailable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"detail": {"code": "no_provider"}})

        client = _client(handler)
        with pytest.raises(AiUnavailableError):
            await client.decide("hi", [], [], None, "tok")

    @pytest.mark.anyio
    async def test_429_raises_rate_limited_with_retry_after(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, headers={"Retry-After": "120"})

        client = _client(handler)
        with pytest.raises(AiRateLimitedError) as exc_info:
            await client.decide("hi", [], [], None, "tok")

        assert exc_info.value.retry_after == 120

    @pytest.mark.anyio
    async def test_other_status_raises_ai_client_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        client = _client(handler)
        with pytest.raises(AiClientError):
            await client.decide("hi", [], [], None, "tok")


class TestRetryBehavior:
    @pytest.mark.anyio
    async def test_connect_error_retried_then_succeeds(self):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            if calls["n"] == 1:
                raise httpx.ConnectError("boom", request=request)
            return httpx.Response(200, json={"decision": {"type": "reply", "text": "ok"}})

        client = _client(handler, connect_retries=2, backoff_seconds=0)
        result = await client.decide("hi", [], [], None, "tok")

        assert isinstance(result, Reply)
        assert calls["n"] == 2

    @pytest.mark.anyio
    async def test_connect_error_exhausts_retries(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

        client = _client(handler, connect_retries=1, backoff_seconds=0)
        with pytest.raises(AiClientError):
            await client.decide("hi", [], [], None, "tok")

    @pytest.mark.anyio
    async def test_read_timeout_not_retried(self):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            raise httpx.ReadTimeout("timed out", request=request)

        client = _client(handler, connect_retries=2, backoff_seconds=0)
        with pytest.raises(AiClientError):
            await client.decide("hi", [], [], None, "tok")

        assert calls["n"] == 1
