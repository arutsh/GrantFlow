from unittest.mock import AsyncMock

import pytest

from app.services.orchestrator import run_turn
from app.services.tool_registry import ToolResult
from shared.ai_client import Reply, ToolCall

pytestmark = pytest.mark.anyio


def _ai_client(decision):
    client = AsyncMock()
    client.decide = AsyncMock(return_value=decision)
    return client


def _registry(
    tools=None,
    call_result=None,
    *,
    targeted_tools=frozenset({"add_budget_line", "update_budget", "get_budget_summary"}),
    resource_id_param="budget_id",
    creating_tools=frozenset({"create_budget"}),
    no_active_resource_message="There's no budget in progress in this conversation yet.",
):
    registry = AsyncMock()
    registry.list_tools = lambda page: tools or []
    registry.call_tool = AsyncMock(return_value=call_result)
    registry.targeted_tools = targeted_tools
    registry.resource_id_param = resource_id_param
    registry.creating_tools = creating_tools
    registry.no_active_resource_message = no_active_resource_message
    return registry


class TestReplyOnlyTurn:
    async def test_returns_reply_with_no_tool(self):
        ai_client = _ai_client(Reply(text="What's the funder name?"))
        registry = _registry()

        result = await run_turn(
            message="create a budget",
            history=[],
            context_id=None,
            page="budgets",
            token="tok",
            ai_client=ai_client,
            registry=registry,
        )

        assert result.reply == "What's the funder name?"
        assert result.tool_name is None
        registry.call_tool.assert_not_awaited()


class TestContextGuard:
    async def test_targeted_tool_without_context_id_is_blocked(self):
        ai_client = _ai_client(
            ToolCall(name="add_budget_line", params={"category_name": "Travel", "amount": 100})
        )
        registry = _registry()

        result = await run_turn(
            message="add a line",
            history=[],
            context_id=None,
            page="budgets",
            token="tok",
            ai_client=ai_client,
            registry=registry,
        )

        assert "no budget in progress" in result.reply
        assert result.tool_name is None
        registry.call_tool.assert_not_awaited()

    async def test_create_budget_never_requires_context_id(self):
        ai_client = _ai_client(
            ToolCall(
                name="create_budget",
                params={"budget_name": "USAID Grant", "external_funder_name": "USAID"},
            )
        )
        registry = _registry(
            call_result=ToolResult(success=True, message="created", created_resource_id="b-1")
        )

        result = await run_turn(
            message="create a budget",
            history=[],
            context_id=None,
            page="budgets",
            token="tok",
            ai_client=ai_client,
            registry=registry,
        )

        assert result.tool_name == "create_budget"
        assert result.created_resource_id == "b-1"


class TestParamValidation:
    async def test_missing_required_param_yields_clarifying_reply(self):
        ai_client = _ai_client(ToolCall(name="create_budget", params={"budget_name": "X"}))
        registry = _registry()

        result = await run_turn(
            message="create a budget",
            history=[],
            context_id=None,
            page="budgets",
            token="tok",
            ai_client=ai_client,
            registry=registry,
        )

        assert "more information" in result.reply
        assert result.tool_name is None
        registry.call_tool.assert_not_awaited()

    async def test_add_budget_line_without_description_yields_clarifying_reply(self):
        """description is a required field precisely so a model that omits it gets
        asked to clarify, rather than the tool silently mislabeling the line."""
        ai_client = _ai_client(
            ToolCall(name="add_budget_line", params={"category_name": "MISC", "amount": 500})
        )
        registry = _registry()

        result = await run_turn(
            message="add a line",
            history=[],
            context_id="ctx-1",
            page="budgets",
            token="tok",
            ai_client=ai_client,
            registry=registry,
        )

        assert "more information" in result.reply
        registry.call_tool.assert_not_awaited()


class TestResourceIdInjection:
    async def test_model_supplied_id_is_ignored_context_id_wins(self):
        ai_client = _ai_client(
            ToolCall(
                name="add_budget_line",
                params={
                    "category_name": "Travel",
                    "amount": 100,
                    "description": "Travel line",
                    "budget_id": "model-guessed-id",
                },
            )
        )
        registry = _registry(call_result=ToolResult(success=True, message="added"))

        await run_turn(
            message="add a line",
            history=[],
            context_id="real-context-id",
            page="budgets",
            token="tok",
            ai_client=ai_client,
            registry=registry,
        )

        dispatched_params = registry.call_tool.await_args.args[1]
        assert dispatched_params["budget_id"] == "real-context-id"

    async def test_injected_param_name_comes_from_the_registry_not_hardcoded(self):
        """Orchestrator must stay domain-agnostic: a hypothetical reports registry
        using resource_id_param="report_id" needs zero orchestrator.py changes."""
        ai_client = _ai_client(
            ToolCall(name="add_line_item", params={"description": "Travel", "amount": 100})
        )
        registry = _registry(
            call_result=ToolResult(success=True, message="added"),
            targeted_tools=frozenset({"add_line_item"}),
            resource_id_param="report_id",
            creating_tools=frozenset({"create_report"}),
            no_active_resource_message="There's no report in progress in this conversation yet.",
        )
        # TOOL_PARAM_MODELS only knows budget tool names, so patch in a permissive
        # stand-in for this one hypothetical report tool rather than touching it.
        from app.schemas.tools import TOOL_PARAM_MODELS
        from pydantic import BaseModel

        class AddLineItemParams(BaseModel):
            description: str
            amount: float

        TOOL_PARAM_MODELS["add_line_item"] = AddLineItemParams
        try:
            await run_turn(
                message="add a line",
                history=[],
                context_id="report-context-id",
                page="reports",
                token="tok",
                ai_client=ai_client,
                registry=registry,
            )
        finally:
            del TOOL_PARAM_MODELS["add_line_item"]

        dispatched_params = registry.call_tool.await_args.args[1]
        assert dispatched_params["report_id"] == "report-context-id"
        assert "budget_id" not in dispatched_params


class TestSuccessfulDispatch:
    async def test_tool_result_populates_turn_result(self):
        ai_client = _ai_client(ToolCall(name="get_budget_summary", params={}))
        registry = _registry(call_result=ToolResult(success=True, message="Budget: 3 lines."))

        result = await run_turn(
            message="summarise",
            history=[],
            context_id="ctx-1",
            page="budgets",
            token="tok",
            ai_client=ai_client,
            registry=registry,
        )

        assert result.tool_name == "get_budget_summary"
        assert result.tool_result == "Budget: 3 lines."
        assert result.reply == "Budget: 3 lines."
        assert result.created_resource_id is None
