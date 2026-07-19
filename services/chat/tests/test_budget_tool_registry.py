from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.budget_tool_registry import BudgetToolRegistry

pytestmark = pytest.mark.anyio


def _http_with_response(method: str, response: httpx.Response) -> MagicMock:
    http = MagicMock()
    setattr(http, method, AsyncMock(return_value=response))
    return http


def _response(
    status_code: int, json_body: dict, request_url: str = "http://budget/x"
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code, json=json_body, request=httpx.Request("GET", request_url)
    )


class TestListTools:
    def test_budgets_page_returns_curated_four(self):
        registry = BudgetToolRegistry(MagicMock(), "http://budget/api/v1")
        tools = registry.list_tools("budgets")
        assert {t.name for t in tools} == {
            "create_budget",
            "add_budget_line",
            "update_budget",
            "get_budget_summary",
        }

    def test_no_page_returns_no_tools(self):
        registry = BudgetToolRegistry(MagicMock(), "http://budget/api/v1")
        assert registry.list_tools(None) == []

    def test_tool_schemas_never_contain_a_budget_id(self):
        registry = BudgetToolRegistry(MagicMock(), "http://budget/api/v1")
        for tool in registry.list_tools("budgets"):
            assert "budget_id" not in tool.parameters.get("properties", {})


class TestTargetedTools:
    def test_targeted_set_excludes_create(self):
        assert BudgetToolRegistry.targeted_tools == {
            "add_budget_line",
            "update_budget",
            "get_budget_summary",
        }

    def test_creating_tools_and_resource_id_param(self):
        assert BudgetToolRegistry.creating_tools == {"create_budget"}
        assert BudgetToolRegistry.resource_id_param == "budget_id"


class TestCallCreateBudget:
    async def test_success_returns_budget_id(self):
        http = _http_with_response(
            "post", _response(200, {"id": "budget-1", "name": "USAID Grant"})
        )
        registry = BudgetToolRegistry(http, "http://budget/api/v1")

        result = await registry.call_tool(
            "create_budget",
            {"budget_name": "USAID Grant", "external_funder_name": "USAID"},
            token="tok",
        )

        assert result.success is True
        assert result.created_resource_id == "budget-1"
        http.post.assert_awaited_once()
        assert http.post.await_args.kwargs["json"] == {
            "name": "USAID Grant",
            "external_funder_name": "USAID",
        }
        assert http.post.await_args.kwargs["headers"] == {"Authorization": "Bearer tok"}

    async def test_success_message_never_embeds_the_raw_id(self):
        """specs/chat-url-context.md: "the raw id SHALL NOT be rendered in the
        chat transcript" — this message becomes the assistant's chat bubble."""
        http = _http_with_response(
            "post", _response(200, {"id": "budget-1", "name": "USAID Grant"})
        )
        registry = BudgetToolRegistry(http, "http://budget/api/v1")

        result = await registry.call_tool(
            "create_budget",
            {"budget_name": "USAID Grant", "external_funder_name": "USAID"},
            token="tok",
        )

        assert "budget-1" not in result.message

    async def test_domain_rejection_relayed_not_raised(self):
        http = _http_with_response("post", _response(422, {"detail": "Funding source is required"}))
        registry = BudgetToolRegistry(http, "http://budget/api/v1")

        result = await registry.call_tool(
            "create_budget", {"budget_name": "X", "external_funder_name": "Y"}, token="tok"
        )

        assert result.success is False
        assert "Failed to create budget" in result.message


class TestCallAddBudgetLine:
    async def test_injects_budget_id_from_params(self):
        http = _http_with_response("post", _response(200, {"id": "line-1"}))
        registry = BudgetToolRegistry(http, "http://budget/api/v1")

        result = await registry.call_tool(
            "add_budget_line",
            {"category_name": "Travel", "amount": 500, "budget_id": "budget-1"},
            token="tok",
        )

        assert result.success is True
        assert http.post.await_args.kwargs["json"]["budget_id"] == "budget-1"
        assert http.post.await_args.kwargs["json"]["description"] == "Travel"


class TestCallUpdateBudget:
    async def test_patches_only_provided_fields(self):
        http = _http_with_response("patch", _response(200, {}))
        registry = BudgetToolRegistry(http, "http://budget/api/v1")

        await registry.call_tool(
            "update_budget", {"name": "New Name", "budget_id": "budget-1"}, token="tok"
        )

        payload = http.patch.await_args.kwargs["json"]
        assert payload == {"name": "New Name"}


class TestCallGetBudgetSummary:
    async def test_summarizes_lines(self):
        body = {
            "name": "USAID Grant",
            "lines": [{"description": "Travel", "amount": 500}],
        }
        http = _http_with_response("get", _response(200, body))
        registry = BudgetToolRegistry(http, "http://budget/api/v1")

        result = await registry.call_tool(
            "get_budget_summary", {"budget_id": "budget-1"}, token="tok"
        )

        assert result.success is True
        assert "USAID Grant" in result.message
        assert "1 lines" in result.message
