import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.chat_orchestrator import TurnResult
from tests.factories.chat import AIChatSessionFactory


def _frames(text: str) -> list[tuple[str, dict]]:
    """Parse an SSE body into ordered (event, data) pairs."""
    frames = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        frames.append((lines["event"], json.loads(lines["data"])))
    return frames


@contextmanager
def _happy_route(fake_session, turn):
    """Patch everything between the route and run_turn so a real SSE stream is produced."""
    # AsyncSessionLocal() is a sync call; `async with` enters it; `db` methods are awaited
    session_local = MagicMock()
    session_local.return_value.__aenter__.return_value = AsyncMock()
    with (
        patch("app.services.rate_limiter.check_and_increment", AsyncMock(return_value=(True, 0))),
        patch("app.api.chat_routes.AsyncSessionLocal", session_local),
        patch(
            "app.api.chat_routes.get_or_create_session", AsyncMock(return_value=fake_session)
        ) as mock_get_session,
        patch("app.api.chat_routes.load_message_history", AsyncMock(return_value=[])),
        patch("app.api.chat_routes.db_messages_to_pydantic_ai", MagicMock(return_value=[])),
        patch("app.api.chat_routes.save_turn", AsyncMock()) as mock_save_turn,
        patch("app.api.chat_routes.build_agent", MagicMock()),
        patch("app.services.chat_stream.run_turn", AsyncMock(return_value=turn)),
    ):
        yield mock_get_session, mock_save_turn


class TestStreamChat:

    def test_unavailable_when_no_provider(self, make_client):
        client = make_client(resolved=None)
        resp = client.post("/api/v1/ai/chat/stream", json={"message": "hi"})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert "X-Session-Id" not in resp.headers

    def test_rate_limiter(self, make_client):
        client = make_client(resolved=True)
        with patch(
            "app.services.rate_limiter.check_and_increment", AsyncMock(return_value=(False, 3600))
        ):
            resp = client.post("/api/v1/ai/chat/stream", json={"message": "hi"})
        assert resp.status_code == 429
        assert resp.headers["Retry-After"] == "3600"

    def test_stream_chat_success(self, make_client):
        client = make_client(resolved=True)
        fake_session = AIChatSessionFactory()
        turn = TurnResult(reply="Hello there!", new_messages=[], budget_id=None)

        with _happy_route(fake_session, turn) as (mock_get_session, mock_save_turn):
            resp = client.post("/api/v1/ai/chat/stream", json={"message": "hi"})

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert resp.headers["X-Session-Id"] == fake_session.id

        events = _frames(resp.text)
        assert [event for event, _ in events] == ["thinking", "text", "done"]
        assert events[1][1] == {"delta": "Hello there!"}
        assert events[2][1] == {"response": "Hello there!"}  # no budget_id key when None

        # once to load history, once inside _on_complete to persist the turn
        assert mock_get_session.await_count == 2
        mock_save_turn.assert_awaited_once()
        assert mock_save_turn.await_args.kwargs["user_text"] == "hi"
        assert mock_save_turn.await_args.kwargs["new_messages"] == []

    def test_stream_chat_tool_call_sequence(self, make_client):
        client = make_client(resolved=True)
        fake_session = AIChatSessionFactory()
        turn = TurnResult(
            reply="Budget created.",
            new_messages=[],
            budget_id="b-123",
            tool_name="create_budget",
            tool_output="ok",
        )

        with _happy_route(fake_session, turn):
            resp = client.post(
                "/api/v1/ai/chat/stream",
                json={"message": "create a budget", "context_budget_id": None, "page": "budgets"},
            )

        assert resp.status_code == 200
        events = _frames(resp.text)
        assert [event for event, _ in events] == [
            "thinking",
            "tool_call",
            "action_result",
            "text",
            "done",
        ]
        assert events[1][1] == {"tool_name": "create_budget"}
        assert events[2][1] == {"tool_name": "create_budget", "output": "ok"}
        assert events[3][1] == {"delta": "Budget created."}
        assert events[4][1] == {"response": "Budget created.", "budget_id": "b-123"}
