"""Safety-net tests for POST /users/me/chat/stream (the users→ai chat proxy).

The proxy is retired in chunk 7 of the AI chat migration; until then these pin
its contract: body/JWT forwarding, verbatim SSE passthrough, X-Session-Id
propagation, upstream error relay, and 503 on connect failure.

Note: ChatStreamRequest omits `page`, so the proxy silently drops it today —
documented here, not fixed (the whole proxy is deleted in chunk 7).
"""

import json

import httpx
import pytest

URL = "/api/users/me/chat/stream"

SSE_BODY = (
    b"event: thinking\ndata: {}\n\n"
    b'event: text\ndata: {"delta": "Hello!"}\n\n'
    b'event: done\ndata: {"response": "Hello!"}\n\n'
)


@pytest.fixture
def captured():
    return []


def _ai_ok(captured, headers=None):
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            content=SSE_BODY,
            headers={"content-type": "text/event-stream", **(headers or {})},
        )

    return handler


class TestChatProxy:

    def test_forwards_body_and_jwt_streams_sse_back_verbatim(self, make_client, captured):
        client = make_client(handler=_ai_ok(captured, headers={"x-session-id": "sess-42"}))

        resp = client.post(URL, json={"message": "hi", "session_id": "sess-42"})

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert resp.headers["X-Session-Id"] == "sess-42"
        assert resp.content == SSE_BODY

        (ai_request,) = captured
        assert ai_request.method == "POST"
        assert str(ai_request.url).endswith("/ai/chat/stream")
        assert ai_request.headers["Authorization"] == f"Bearer {client.user['token']}"
        assert json.loads(ai_request.content) == {
            "message": "hi",
            "session_id": "sess-42",
            "context_budget_id": None,
        }

    def test_no_session_header_when_upstream_omits_it(self, make_client, captured):
        client = make_client(handler=_ai_ok(captured))

        resp = client.post(URL, json={"message": "hi"})

        assert resp.status_code == 200
        assert "X-Session-Id" not in resp.headers

    def test_upstream_error_status_and_body_are_relayed(self, make_client):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"detail": "Rate limit exceeded"})

        client = make_client(handler=handler)

        resp = client.post(URL, json={"message": "hi"})

        assert resp.status_code == 429
        assert "Rate limit exceeded" in resp.json()["detail"]

    def test_connect_error_returns_503(self, make_client):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("AI service down", request=request)

        client = make_client(handler=handler)

        resp = client.post(URL, json={"message": "hi"})

        assert resp.status_code == 503
        assert resp.json()["detail"] == "AI service is unavailable"
