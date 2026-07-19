import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.orchestrator import TurnResult
from shared.ai_client import AiRateLimitedError, AiUnavailableError
from tests.factories.conversation import ConversationFactory


def _frames(text: str) -> list[tuple[str, dict]]:
    frames = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        frames.append((lines["event"], json.loads(lines["data"])))
    return frames


def _session_local(fake_conversation):
    session_local = MagicMock()
    session_local.return_value.__aenter__.return_value = AsyncMock()
    return session_local


class TestStreamChat:
    def test_rejects_missing_body(self, make_client):
        client = make_client()
        resp = client.post("/api/v1/chat/stream", json={})
        assert resp.status_code == 422

    def test_unavailable_when_ai_has_no_provider(self, make_client):
        client = make_client()
        fake_conversation = ConversationFactory()
        with (
            patch("app.api.chat_routes.AsyncSessionLocal", _session_local(fake_conversation)),
            patch(
                "app.api.chat_routes.get_or_create_conversation",
                AsyncMock(return_value=fake_conversation),
            ),
            patch("app.api.chat_routes.load_history", AsyncMock(return_value=[])),
            patch("app.api.chat_routes.run_turn", AsyncMock(side_effect=AiUnavailableError())),
        ):
            resp = client.post("/api/v1/chat/stream", json={"message": "hi"})

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert resp.headers["X-Conversation-Id"] == str(fake_conversation.id)
        events = _frames(resp.text)
        assert [event for event, _ in events] == ["unavailable"]

    def test_rate_limited_returns_429(self, make_client):
        client = make_client()
        fake_conversation = ConversationFactory()
        with (
            patch("app.api.chat_routes.AsyncSessionLocal", _session_local(fake_conversation)),
            patch(
                "app.api.chat_routes.get_or_create_conversation",
                AsyncMock(return_value=fake_conversation),
            ),
            patch("app.api.chat_routes.load_history", AsyncMock(return_value=[])),
            patch(
                "app.api.chat_routes.run_turn",
                AsyncMock(side_effect=AiRateLimitedError(retry_after=120)),
            ),
        ):
            resp = client.post("/api/v1/chat/stream", json={"message": "hi"})

        assert resp.status_code == 429
        assert resp.headers["Retry-After"] == "120"

    def test_unexpected_exception_yields_error_event_not_500(self, make_client):
        client = make_client()
        fake_conversation = ConversationFactory()
        with (
            patch("app.api.chat_routes.AsyncSessionLocal", _session_local(fake_conversation)),
            patch(
                "app.api.chat_routes.get_or_create_conversation",
                AsyncMock(return_value=fake_conversation),
            ),
            patch("app.api.chat_routes.load_history", AsyncMock(return_value=[])),
            patch("app.api.chat_routes.run_turn", AsyncMock(side_effect=RuntimeError("boom"))),
        ):
            resp = client.post("/api/v1/chat/stream", json={"message": "hi"})

        assert resp.status_code == 200
        events = _frames(resp.text)
        assert [event for event, _ in events] == ["error"]

    def test_reply_only_turn_sequence(self, make_client):
        client = make_client()
        fake_conversation = ConversationFactory()
        turn = TurnResult(reply="Hello there!")
        with (
            patch("app.api.chat_routes.AsyncSessionLocal", _session_local(fake_conversation)),
            patch(
                "app.api.chat_routes.get_or_create_conversation",
                AsyncMock(return_value=fake_conversation),
            ),
            patch("app.api.chat_routes.load_history", AsyncMock(return_value=[])),
            patch("app.api.chat_routes.run_turn", AsyncMock(return_value=turn)),
            patch("app.api.chat_routes.save_turn", AsyncMock()) as mock_save_turn,
        ):
            resp = client.post("/api/v1/chat/stream", json={"message": "hi"})

        assert resp.status_code == 200
        assert resp.headers["X-Conversation-Id"] == str(fake_conversation.id)
        events = _frames(resp.text)
        assert [event for event, _ in events] == ["thinking", "text", "done"]
        assert events[1][1] == {"delta": "Hello there!"}
        assert events[2][1] == {"response": "Hello there!"}
        mock_save_turn.assert_awaited_once()

    def test_tool_executing_turn_sequence(self, make_client):
        client = make_client()
        fake_conversation = ConversationFactory()
        turn = TurnResult(
            reply="Budget created.",
            tool_name="create_budget",
            tool_params={"budget_name": "USAID Grant"},
            tool_result="Budget created.",
            created_resource_id="budget-1",
        )
        with (
            patch("app.api.chat_routes.AsyncSessionLocal", _session_local(fake_conversation)),
            patch(
                "app.api.chat_routes.get_or_create_conversation",
                AsyncMock(return_value=fake_conversation),
            ),
            patch("app.api.chat_routes.load_history", AsyncMock(return_value=[])),
            patch("app.api.chat_routes.run_turn", AsyncMock(return_value=turn)),
            patch("app.api.chat_routes.save_turn", AsyncMock()),
        ):
            resp = client.post(
                "/api/v1/chat/stream",
                json={"message": "create a budget", "context_id": None, "page": "budgets"},
            )

        events = _frames(resp.text)
        assert [event for event, _ in events] == [
            "thinking",
            "tool_call",
            "action_result",
            "text",
            "done",
        ]
        assert events[1][1] == {"tool_name": "create_budget"}
        assert events[4][1] == {"response": "Budget created.", "budget_id": "budget-1"}


class TestListConversations:
    def test_returns_only_own_conversations(self, make_client):
        client = make_client()
        rows = ConversationFactory.create_batch(2)
        with (
            patch("app.api.chat_routes.list_conversations", AsyncMock(return_value=rows)),
            patch("app.api.chat_routes.AsyncSessionLocal", _session_local(None)),
        ):
            resp = client.get("/api/v1/chat/conversations")

        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestGetConversationMessages:
    def test_404_when_conversation_not_found_or_foreign(self, make_client):
        client = make_client()
        with (
            patch("app.api.chat_routes.get_conversation_messages", AsyncMock(return_value=None)),
            patch("app.api.chat_routes.AsyncSessionLocal", _session_local(None)),
        ):
            resp = client.get("/api/v1/chat/conversations/some-id/messages")

        assert resp.status_code == 404
