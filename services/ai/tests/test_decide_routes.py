from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_ai.exceptions import UnexpectedModelBehavior

from shared.ai_client.schemas import Reply, ToolCall


def _body(**overrides) -> dict:
    body = {
        "message": "create a budget",
        "conversation_history": [],
        "available_tools": [],
        "domain_context": None,
    }
    body.update(overrides)
    return body


class TestDecideRoute:
    def test_unavailable_when_no_provider(self, make_client):
        client = make_client(resolved=None)
        resp = client.post("/api/v1/ai/decide", json=_body())
        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "no_provider"

    def test_uses_platform_model_when_fallback_enabled(self, make_client):
        from app.services.provider import ResolvedModel

        client = make_client(resolved=None)
        platform_model = ResolvedModel(model=MagicMock(), provider_name="anthropic", model_name="x")
        decision = Reply(text="Hi there")
        with (
            patch(
                "app.api.decide_routes.resolve_with_platform_fallback",
                new=AsyncMock(return_value=platform_model),
            ),
            patch(
                "app.services.rate_limiter.check_and_increment", AsyncMock(return_value=(True, 0))
            ),
            patch("app.api.decide_routes.decide", AsyncMock(return_value=decision)),
        ):
            resp = client.post("/api/v1/ai/decide", json=_body())
        assert resp.status_code == 200

    def test_fails_closed_when_fallback_not_enabled(self, make_client):
        client = make_client(resolved=None)
        with patch(
            "app.api.decide_routes.resolve_with_platform_fallback",
            new=AsyncMock(return_value=None),
        ):
            resp = client.post("/api/v1/ai/decide", json=_body())
        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "no_provider"

    def test_rate_limited(self, make_client):
        client = make_client(resolved=True)
        with patch(
            "app.services.rate_limiter.check_and_increment", AsyncMock(return_value=(False, 120))
        ):
            resp = client.post("/api/v1/ai/decide", json=_body())
        assert resp.status_code == 429
        assert resp.headers["Retry-After"] == "120"

    def test_tool_call_decision(self, make_client):
        client = make_client(resolved=True)
        decision = ToolCall(name="create_budget", params={"budget_name": "USAID Grant"})
        with (
            patch(
                "app.services.rate_limiter.check_and_increment", AsyncMock(return_value=(True, 0))
            ),
            patch("app.api.decide_routes.decide", AsyncMock(return_value=decision)),
        ):
            resp = client.post("/api/v1/ai/decide", json=_body())

        assert resp.status_code == 200
        assert resp.json() == {
            "decision": {
                "type": "tool_call",
                "name": "create_budget",
                "params": {"budget_name": "USAID Grant"},
            }
        }

    def test_model_error_returns_502(self, make_client):
        client = make_client(resolved=True)
        with (
            patch(
                "app.services.rate_limiter.check_and_increment", AsyncMock(return_value=(True, 0))
            ),
            patch(
                "app.api.decide_routes.decide",
                AsyncMock(side_effect=UnexpectedModelBehavior("tool exceeded max retries")),
            ),
        ):
            resp = client.post("/api/v1/ai/decide", json=_body())

        assert resp.status_code == 502
        assert resp.json()["detail"]["code"] == "model_error"

    def test_reply_decision(self, make_client):
        client = make_client(resolved=True)
        decision = Reply(text="What's the funder name?")
        with (
            patch(
                "app.services.rate_limiter.check_and_increment", AsyncMock(return_value=(True, 0))
            ),
            patch("app.api.decide_routes.decide", AsyncMock(return_value=decision)),
        ):
            resp = client.post("/api/v1/ai/decide", json=_body())

        assert resp.status_code == 200
        assert resp.json() == {"decision": {"type": "reply", "text": "What's the funder name?"}}
