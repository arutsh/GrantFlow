"""Safety-net tests for POST /budgets/ai/stream (the budget→ai parse proxy).

This endpoint moves into the chat service in chunk 9 of the AI chat migration;
these tests pin its SSE contract (event passthrough, done→created handling,
split-frame buffering) so the port can be verified against the same suite.
"""

import json
import uuid
from unittest.mock import AsyncMock, patch

import httpx

URL = "/api/v1/budgets/ai/stream"
CREATE_SERVICE = "app.api.budget_routes.create_budget_with_lines_service"

DONE_PAYLOAD = {
    "budget_name": "Field Trip",
    "external_funder_name": "ACME",
    "duration_months": 12,
    "lines": [],
}


class FakeAIClient:
    """Stands in for httpx.AsyncClient(...) and everything the route does with it:
    the client context manager, .stream(...), the response context manager and
    response.aiter_text(). Records the request for assertions."""

    def __init__(self, chunks=None, connect_error=False):
        self.chunks = chunks or []
        self.connect_error = connect_error
        self.method = None
        self.url = None
        self.headers = None

    def __call__(self, *args, **kwargs):  # httpx.AsyncClient(timeout=...)
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def stream(self, method, url, headers=None):
        if self.connect_error:
            raise httpx.ConnectError("AI service down")
        self.method = method
        self.url = url
        self.headers = headers
        return self

    async def aiter_text(self):
        for chunk in self.chunks:
            yield chunk


def _frames(text: str) -> list[tuple[str, str]]:
    """Parse an SSE body into ordered (event, raw_data) pairs."""
    frames = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        frames.append((lines["event"], lines["data"]))
    return frames


def _post(client, fake_ai, text="create a budget"):
    with patch("app.api.budget_routes.httpx.AsyncClient", fake_ai):
        return client.post(URL, json={"text": text})


class TestAiStreamProxy:

    def test_progress_passthrough_and_upstream_request(self, make_client):
        client = make_client()
        fake_ai = FakeAIClient(chunks=['event: progress\ndata: {"status": "Parsing..."}\n\n'])

        resp = _post(client, fake_ai, text="a budget for a trip")

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert _frames(resp.text) == [("progress", '{"status": "Parsing..."}')]
        # upstream request: GET to the parse endpoint, text url-encoded, JWT forwarded
        assert fake_ai.method == "GET"
        assert "/ai/parse-budget/stream?text=a%20budget%20for%20a%20trip" in fake_ai.url
        assert fake_ai.headers == {"Authorization": f"Bearer {client.user['token']}"}

    def test_done_creates_budget_and_emits_created(self, make_client):
        client = make_client()
        budget_id = str(uuid.uuid4())
        fake_ai = FakeAIClient(chunks=[f"event: done\ndata: {json.dumps(DONE_PAYLOAD)}\n\n"])

        with patch(CREATE_SERVICE, AsyncMock(return_value={"id": budget_id})) as mock_create:
            resp = _post(client, fake_ai)

        events = _frames(resp.text)
        assert [event for event, _ in events] == ["progress", "created"]
        assert json.loads(events[0][1]) == {"status": "Creating budget..."}
        assert json.loads(events[1][1]) == {"budget_id": budget_id}
        mock_create.assert_awaited_once()
        request_arg = mock_create.await_args.args[0]
        assert request_arg.budget_name == "Field Trip"
        assert request_arg.external_funder_name == "ACME"

    def test_done_with_creation_failure_emits_error(self, make_client):
        client = make_client()
        fake_ai = FakeAIClient(chunks=[f"event: done\ndata: {json.dumps(DONE_PAYLOAD)}\n\n"])

        with patch(CREATE_SERVICE, AsyncMock(side_effect=Exception('boom "quoted"'))):
            resp = _post(client, fake_ai)

        events = _frames(resp.text)
        assert [event for event, _ in events] == ["progress", "error"]
        error = json.loads(events[1][1])
        assert error["message"] == "Failed to create budget"
        assert error["detail"] == "boom 'quoted'"  # double quotes sanitized

    def test_error_and_unavailable_passthrough(self, make_client):
        fake_ai = FakeAIClient(
            chunks=[
                'event: unavailable\ndata: {"message": "No AI provider is configured."}\n\n',
                'event: error\ndata: {"message": "Parse failed"}\n\n',
            ]
        )

        resp = _post(make_client(), fake_ai)

        assert _frames(resp.text) == [
            ("unavailable", '{"message": "No AI provider is configured."}'),
            ("error", '{"message": "Parse failed"}'),
        ]

    def test_connection_failure_emits_error(self, make_client):
        resp = _post(make_client(), FakeAIClient(connect_error=True))

        assert resp.status_code == 200
        assert resp.text == "event: error\ndata: Connection to AI service failed\n\n"

    def test_split_frames_are_reassembled(self, make_client):
        """The proxy hand-buffers SSE lines; frames split mid-line must survive."""
        fake_ai = FakeAIClient(
            chunks=[
                "event: prog",
                'ress\ndata: {"stat',
                'us": "Parsing..."}\n',
                "\n",
                'event: error\ndata: {"message": "Parse failed"}\n\n',
            ]
        )

        resp = _post(make_client(), fake_ai)

        assert _frames(resp.text) == [
            ("progress", '{"status": "Parsing..."}'),
            ("error", '{"message": "Parse failed"}'),
        ]
