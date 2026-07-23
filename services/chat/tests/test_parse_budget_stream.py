"""Tests for build_parse_budget_sse_stream — ports services/budget's retired
test_ai_stream_proxy.py scenarios onto the new chat-hosted parse flow.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.parse_budget_stream import build_parse_budget_sse_stream
from shared.ai_client import ParseDone, ParseError, ParseProgress, ParseUnavailable

pytestmark = pytest.mark.anyio

BUDGET_URL = "http://budget/api/v1"


def _http_with_post(response: httpx.Response) -> MagicMock:
    http = MagicMock()
    http.post = AsyncMock(return_value=response)
    return http


def _response(status_code: int, json_body: dict, request_url: str = "http://budget/x"):
    return httpx.Response(
        status_code=status_code, json=json_body, request=httpx.Request("POST", request_url)
    )


async def _events(*items):
    for item in items:
        yield item


def _frames(text: str) -> list[tuple[str, dict]]:
    frames = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        frames.append((lines["event"], json.loads(lines["data"])))
    return frames


async def _collect_text(events, http, token="tok") -> str:
    chunks = [
        chunk
        async for chunk in build_parse_budget_sse_stream(
            events, http=http, budget_service_url=BUDGET_URL, token=token
        )
    ]
    return "".join(chunks)


class TestProgressAndErrorPassthrough:
    async def test_progress_passthrough(self):
        text = await _collect_text(_events(ParseProgress(status="Parsing...")), MagicMock())

        assert _frames(text) == [("progress", {"status": "Parsing..."})]

    async def test_error_passthrough(self):
        text = await _collect_text(_events(ParseError(message="Parse failed")), MagicMock())

        assert _frames(text) == [("error", {"message": "Parse failed"})]

    async def test_unavailable_passthrough(self):
        text = await _collect_text(_events(ParseUnavailable()), MagicMock())

        assert _frames(text) == [("unavailable", {})]


class TestDoneCreatesBudget:
    async def test_done_creates_budget_and_emits_created(self):
        http = _http_with_post(_response(200, {"id": "budget-1"}))
        done = ParseDone(budget_name="Field Trip", external_funder_name="ACME", lines=[])

        text = await _collect_text(_events(done), http, token="tok")

        frames = _frames(text)
        assert [event for event, _ in frames] == ["progress", "created"]
        assert frames[0][1] == {"status": "Creating budget..."}
        assert frames[1][1] == {"budget_id": "budget-1"}

        http.post.assert_awaited_once()
        url, kwargs = http.post.call_args
        assert url[0] == f"{BUDGET_URL}/budgets/with-lines"
        assert kwargs["headers"] == {"Authorization": "Bearer tok"}
        assert kwargs["json"]["budget_name"] == "Field Trip"
        assert kwargs["json"]["external_funder_name"] == "ACME"

    async def test_missing_funder_name_defaults_to_empty_string(self):
        http = _http_with_post(_response(200, {"id": "budget-2"}))
        done = ParseDone(budget_name="Trip", external_funder_name=None, lines=[])

        await _collect_text(_events(done), http)

        assert http.post.call_args.kwargs["json"]["external_funder_name"] == ""

    async def test_done_with_creation_failure_emits_error(self):
        http = MagicMock()
        http.post = AsyncMock(side_effect=Exception('boom "quoted"'))
        done = ParseDone(budget_name="Trip", lines=[])

        text = await _collect_text(_events(done), http)

        frames = _frames(text)
        assert [event for event, _ in frames] == ["progress", "error"]
        assert frames[1][1]["message"] == "Failed to create budget"
        assert frames[1][1]["detail"] == 'boom "quoted"'

    async def test_malformed_2xx_body_reported_as_failure(self):
        """A 2xx with a body that isn't valid JSON (e.g. a proxy error page)
        must be reported as a failure, not silently treated as success."""
        http = _http_with_post(
            httpx.Response(
                200, content=b"<html>not json</html>", request=httpx.Request("POST", "http://x")
            )
        )
        done = ParseDone(budget_name="Trip", lines=[])

        text = await _collect_text(_events(done), http)

        assert [event for event, _ in _frames(text)] == ["progress", "error"]

    async def test_upstream_4xx_reported_as_failure(self):
        http = _http_with_post(_response(422, {"detail": "Invalid budget"}))
        done = ParseDone(budget_name="Trip", lines=[])

        text = await _collect_text(_events(done), http)

        assert [event for event, _ in _frames(text)] == ["progress", "error"]


class TestMultipleEvents:
    async def test_progress_then_done_sequence(self):
        http = _http_with_post(_response(200, {"id": "budget-3"}))
        text = await _collect_text(
            _events(
                ParseProgress(status="Parsing..."),
                ParseProgress(status="Building budget preview..."),
                ParseDone(budget_name="Trip", lines=[]),
            ),
            http,
        )

        assert [event for event, _ in _frames(text)] == [
            "progress",
            "progress",
            "progress",
            "created",
        ]
