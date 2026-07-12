from unittest.mock import AsyncMock, patch


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
            "app.api.chat_routes.check_and_increment", AsyncMock(return_value=(False, 3600))
        ):
            resp = client.post("/api/v1/ai/chat/stream", json={"message": "hi"})
        assert resp.status_code == 429
        assert resp.headers["Retry-After"] == "3600"
