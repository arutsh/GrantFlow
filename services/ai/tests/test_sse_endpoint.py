import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from app.api.parse_routes import get_validated_user
from app.services.prompt_loader import LoadedPrompt
from app.services.provider import ResolvedModel, get_resolved_model
from tests.factories.user import make_valid_user


MOCK_PROMPT = LoadedPrompt(
    name="parse_budget",
    version="v1",
    system_prompt="You are a structured extractor.",
    user_template="{{ text }}",
)

_VALID_OUTPUT = {
    "budget_name": "Staff Grant",
    "external_funder_name": "City Foundation",
    "duration_months": 12,
    "lines": [
        {
            "category_name": "Personnel",
            "description": "Program coordinator",
            "amount": 50000.0,
            "extra_fields": None,
        }
    ],
}

_LOAD_PROMPT = "app.services.parse_service.load_prompt"
_AUDIT = "app.services.parse_service.write_audit_log"
_RATE = "app.services.rate_limiter.check_and_increment"
_AGENT = "app.services.parse_service.Agent"


def _make_resolved(provider_name="ollama", model_name="llama3.2"):
    resolved = MagicMock(spec=ResolvedModel)
    resolved.provider_name = provider_name
    resolved.model_name = model_name
    resolved.model = MagicMock()
    return resolved


def _make_agent_mock(output_data):
    """Return a mock Agent class whose instances return a fake RunResult."""
    from pydantic_ai.messages import ModelMessagesTypeAdapter  # noqa: F401 — just for type

    usage = MagicMock(input_tokens=10, output_tokens=20)

    run_result = MagicMock()
    run_result.data = output_data
    run_result.output = output_data
    run_result.usage = usage

    agent_instance = MagicMock()
    agent_instance.run = AsyncMock(return_value=run_result)

    agent_cls = MagicMock(return_value=agent_instance)
    return agent_cls


def _setup(customer_id="sse-test-customer"):
    app.dependency_overrides[get_validated_user] = (
        lambda: make_valid_user(customer_id=customer_id)
    )
    return TestClient(app)


def _teardown():
    app.dependency_overrides = {}


class TestSSEEndpoint:
    def setup_method(self):
        self.client = _setup()

    def teardown_method(self):
        _teardown()

    def test_response_content_type_is_event_stream(self):
        from app.schemas.ai_schema import LLMBudgetOutput

        app.dependency_overrides[get_resolved_model] = lambda: _make_resolved()
        with (
            patch(_LOAD_PROMPT, new=AsyncMock(return_value=MOCK_PROMPT)),
            patch(_AUDIT, new=AsyncMock()),
            patch(_RATE, new=AsyncMock(return_value=(True, 0))),
            patch(_AGENT, _make_agent_mock(LLMBudgetOutput(**_VALID_OUTPUT))),
        ):
            response = self.client.get("/api/v1/ai/parse-budget/stream?text=test")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    def test_progress_events_emitted_before_done(self):
        from app.schemas.ai_schema import LLMBudgetOutput

        app.dependency_overrides[get_resolved_model] = lambda: _make_resolved()
        with (
            patch(_LOAD_PROMPT, new=AsyncMock(return_value=MOCK_PROMPT)),
            patch(_AUDIT, new=AsyncMock()),
            patch(_RATE, new=AsyncMock(return_value=(True, 0))),
            patch(_AGENT, _make_agent_mock(LLMBudgetOutput(**_VALID_OUTPUT))),
        ):
            response = self.client.get("/api/v1/ai/parse-budget/stream?text=test")

        lines = response.text.splitlines()
        progress_indices = [i for i, line in enumerate(lines) if line == "event: progress"]
        done_index = next(i for i, line in enumerate(lines) if line == "event: done")
        assert len(progress_indices) >= 1
        assert all(i < done_index for i in progress_indices)

    def test_done_event_contains_valid_json(self):
        from app.schemas.ai_schema import LLMBudgetOutput

        app.dependency_overrides[get_resolved_model] = lambda: _make_resolved()
        with (
            patch(_LOAD_PROMPT, new=AsyncMock(return_value=MOCK_PROMPT)),
            patch(_AUDIT, new=AsyncMock()),
            patch(_RATE, new=AsyncMock(return_value=(True, 0))),
            patch(_AGENT, _make_agent_mock(LLMBudgetOutput(**_VALID_OUTPUT))),
        ):
            response = self.client.get("/api/v1/ai/parse-budget/stream?text=test")

        assert "event: done" in response.text
        lines = response.text.splitlines()
        done_data = next(lines[i + 1] for i, line in enumerate(lines) if line == "event: done")
        payload = json.loads(done_data[len("data: "):])
        assert payload["budget_name"] == "Staff Grant"
        assert payload["ai_available"] is True
        assert payload["prompt_version"] == "v1"

    def test_unavailable_event_when_prompt_load_fails(self):
        app.dependency_overrides[get_resolved_model] = lambda: _make_resolved()
        with (
            patch(_LOAD_PROMPT, new=AsyncMock(side_effect=ValueError("no prompt"))),
            patch(_RATE, new=AsyncMock(return_value=(True, 0))),
        ):
            response = self.client.get("/api/v1/ai/parse-budget/stream?text=test")

        assert response.status_code == 200
        assert "event: unavailable" in response.text

    def test_unavailable_event_when_no_provider_key(self):
        app.dependency_overrides[get_resolved_model] = lambda: None
        with patch(_RATE, new=AsyncMock(return_value=(True, 0))):
            response = self.client.get("/api/v1/ai/parse-budget/stream?text=test")

        assert response.status_code == 200
        assert "event: unavailable" in response.text

    def test_audit_log_written_with_prompt_version_and_provider(self):
        from app.schemas.ai_schema import LLMBudgetOutput

        mock_audit = AsyncMock()
        app.dependency_overrides[get_resolved_model] = (
            lambda: _make_resolved(provider_name="ollama")
        )
        with (
            patch(_LOAD_PROMPT, new=AsyncMock(return_value=MOCK_PROMPT)),
            patch(_AUDIT, mock_audit),
            patch(_RATE, new=AsyncMock(return_value=(True, 0))),
            patch(_AGENT, _make_agent_mock(LLMBudgetOutput(**_VALID_OUTPUT))),
        ):
            self.client.get("/api/v1/ai/parse-budget/stream?text=test")

        mock_audit.assert_called_once()
        kwargs = mock_audit.call_args.kwargs
        assert kwargs["prompt_version"] == "v1"
        assert kwargs["provider"] == "ollama"

    def test_token_counts_populated_from_usage(self):
        from app.schemas.ai_schema import LLMBudgetOutput

        mock_audit = AsyncMock()
        app.dependency_overrides[get_resolved_model] = lambda: _make_resolved()
        with (
            patch(_LOAD_PROMPT, new=AsyncMock(return_value=MOCK_PROMPT)),
            patch(_AUDIT, mock_audit),
            patch(_RATE, new=AsyncMock(return_value=(True, 0))),
            patch(_AGENT, _make_agent_mock(LLMBudgetOutput(**_VALID_OUTPUT))),
        ):
            self.client.get("/api/v1/ai/parse-budget/stream?text=test")

        kwargs = mock_audit.call_args.kwargs
        assert kwargs["input_tokens"] == 10
        assert kwargs["output_tokens"] == 20
