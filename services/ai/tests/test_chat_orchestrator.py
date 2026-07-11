"""Tests for chat_orchestrator.run_turn — the code that decides, in code, not
in the model, whether a classified turn has enough information to act.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.chat_intent_schema import (
    AddLineIntent,
    ClarifyIntent,
    CreateBudgetIntent,
    GetSummaryIntent,
    UpdateBudgetIntent,
)
from app.services.chat_orchestrator import run_turn


class _FakeResult:
    def __init__(self, output):
        self.output = output

    def new_messages(self):
        return ["msg"]


class _FakeAgent:
    def __init__(self, output):
        self._output = output

    async def run(self, message, message_history=None):
        return _FakeResult(self._output)


class TestCreateBudgetIntent:
    @pytest.mark.anyio
    async def test_missing_required_field_asks_without_calling_service(self):
        turn = CreateBudgetIntent(
            intent="create_budget", budget_name=None, message_to_user="What's the funder?"
        )
        with patch("app.services.chat_orchestrator.create_budget", AsyncMock()) as mock_create:
            result = await run_turn(_FakeAgent(turn), "hi", None, [], context_budget_id=None)
        mock_create.assert_not_called()
        assert result.reply == "What's the funder?"
        assert result.budget_id is None
        assert result.tool_name is None

    @pytest.mark.anyio
    async def test_all_fields_present_calls_service_and_sets_active_budget(self):
        turn = CreateBudgetIntent(
            intent="create_budget",
            budget_name="UNTF 2026",
            external_funder_name="UNTF",
            duration_months=12,
            message_to_user="Creating it now.",
        )
        with patch(
            "app.services.chat_orchestrator.create_budget",
            AsyncMock(return_value=(True, "Budget created.", "budget-123")),
        ) as mock_create:
            result = await run_turn(_FakeAgent(turn), "hi", None, [], context_budget_id=None)
        mock_create.assert_called_once()
        assert result.budget_id == "budget-123"
        assert result.tool_name == "create_budget"
        assert result.reply == "Budget created."

    @pytest.mark.anyio
    async def test_service_failure_keeps_prior_context_budget_id(self):
        turn = CreateBudgetIntent(
            intent="create_budget",
            budget_name="X",
            external_funder_name="Y",
            message_to_user="Creating it now.",
        )
        with patch(
            "app.services.chat_orchestrator.create_budget",
            AsyncMock(return_value=(False, "Failed to create budget.", None)),
        ):
            result = await run_turn(
                _FakeAgent(turn), "hi", None, [], context_budget_id="existing-id"
            )
        assert result.budget_id == "existing-id"


class TestAddLineIntent:
    @pytest.mark.anyio
    async def test_no_active_budget_refuses_without_calling_service(self):
        turn = AddLineIntent(
            intent="add_line", category_name="Travel", amount=100.0, message_to_user="Adding it."
        )
        with patch("app.services.chat_orchestrator.add_budget_line", AsyncMock()) as mock_add:
            result = await run_turn(_FakeAgent(turn), "hi", None, [], context_budget_id=None)
        mock_add.assert_not_called()
        assert "no budget in progress" in result.reply.lower()

    @pytest.mark.anyio
    async def test_missing_amount_asks_without_calling_service(self):
        turn = AddLineIntent(
            intent="add_line",
            category_name="Travel",
            amount=None,
            message_to_user="How much is the travel line?",
        )
        with patch("app.services.chat_orchestrator.add_budget_line", AsyncMock()) as mock_add:
            result = await run_turn(_FakeAgent(turn), "hi", None, [], context_budget_id="b-1")
        mock_add.assert_not_called()
        assert result.reply == "How much is the travel line?"

    @pytest.mark.anyio
    async def test_fields_present_calls_service_with_context_budget_id(self):
        turn = AddLineIntent(
            intent="add_line",
            category_name="Personnel",
            description="Coordinator fee",
            amount=3000.0,
            message_to_user="Adding it now.",
        )
        with patch(
            "app.services.chat_orchestrator.add_budget_line",
            AsyncMock(return_value=(True, "Line added.")),
        ) as mock_add:
            result = await run_turn(_FakeAgent(turn), "hi", None, [], context_budget_id="b-1")
        mock_add.assert_called_once_with(None, "b-1", "Coordinator fee", 3000.0, "Personnel")
        assert result.tool_name == "add_budget_line"
        assert result.budget_id == "b-1"


class TestUpdateBudgetAndSummary:
    @pytest.mark.anyio
    async def test_update_with_no_active_budget_refuses(self):
        turn = UpdateBudgetIntent(
            intent="update_budget", name="New Name", message_to_user="Updating it."
        )
        with patch("app.services.chat_orchestrator.update_budget", AsyncMock()) as mock_update:
            result = await run_turn(_FakeAgent(turn), "hi", None, [], context_budget_id=None)
        mock_update.assert_not_called()
        assert "no budget in progress" in result.reply.lower()

    @pytest.mark.anyio
    async def test_summary_with_no_active_budget_refuses(self):
        turn = GetSummaryIntent(intent="get_summary", message_to_user="Sure, one sec.")
        with patch("app.services.chat_orchestrator.get_budget_summary", AsyncMock()) as mock_get:
            result = await run_turn(_FakeAgent(turn), "hi", None, [], context_budget_id=None)
        mock_get.assert_not_called()
        assert "no budget in progress" in result.reply.lower()


class TestClarifyIntent:
    @pytest.mark.anyio
    async def test_relays_message_to_user_verbatim(self):
        turn = ClarifyIntent(intent="clarify", message_to_user="Did you mean a new budget?")
        result = await run_turn(_FakeAgent(turn), "hi", None, [], context_budget_id="b-1")
        assert result.reply == "Did you mean a new budget?"
        assert result.tool_name is None
        assert result.budget_id == "b-1"
