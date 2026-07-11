"""Tests for the budget REST helpers used by chat_orchestrator.py.

Each helper: success path returns (True, message[, id]); budget service error
returns (False, message) — never raises.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
import httpx

from app.services.chat_agent import (
    ChatDeps,
    create_budget,
    update_budget,
    add_budget_line,
    get_budget_summary,
)


def _make_deps(http_client: httpx.AsyncClient) -> ChatDeps:
    return ChatDeps(
        http=http_client,
        customer_id="cust-1",
        user_id="user-1",
        token="tok",
        budget_service_url="http://budget-svc/api/v1",
    )


def _http_client(status: int = 200, json_body: dict | None = None) -> httpx.AsyncClient:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status
    response.json.return_value = json_body or {}
    if status >= 400:
        response.text = f"error {status}"
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "", request=MagicMock(), response=response
        )
    else:
        response.raise_for_status.return_value = None

    client = AsyncMock(spec=httpx.AsyncClient)
    client.post.return_value = response
    client.patch.return_value = response
    client.get.return_value = response
    return client


class TestCreateBudget:
    @pytest.mark.anyio
    async def test_success_returns_id(self):
        client = _http_client(200, {"id": "budget-abc"})
        ok, msg, budget_id = await create_budget(
            _make_deps(client),
            budget_name="USAID Grant",
            external_funder_name="USAID",
            duration_months=12,
        )
        assert ok is True
        assert budget_id == "budget-abc"
        assert "USAID Grant" in msg

    @pytest.mark.anyio
    async def test_service_error_returns_message_not_raises(self):
        client = _http_client(400)
        ok, msg, budget_id = await create_budget(
            _make_deps(client),
            budget_name="X",
            external_funder_name="Y",
        )
        assert ok is False
        assert budget_id is None
        assert "Failed" in msg


class TestUpdateBudget:
    @pytest.mark.anyio
    async def test_success_returns_confirmation(self):
        client = _http_client(200, {})
        ok, msg = await update_budget(_make_deps(client), budget_id="b-1", name="New Name")
        assert ok is True
        assert "b-1" in msg

    @pytest.mark.anyio
    async def test_no_fields_returns_message(self):
        client = _http_client(200, {})
        ok, msg = await update_budget(_make_deps(client), budget_id="b-1")
        assert ok is False
        assert "No fields" in msg

    @pytest.mark.anyio
    async def test_404_returns_error_message(self):
        client = _http_client(404)
        ok, msg = await update_budget(_make_deps(client), budget_id="missing", name="X")
        assert ok is False
        assert "Failed" in msg


class TestAddBudgetLine:
    @pytest.mark.anyio
    async def test_success_returns_line_id(self):
        client = _http_client(200, {"id": "line-xyz"})
        ok, msg = await add_budget_line(
            _make_deps(client),
            budget_id="b-1",
            description="Travel",
            amount=2000.0,
            category_name="Travel",
        )
        assert ok is True
        assert "line-xyz" in msg

    @pytest.mark.anyio
    async def test_service_error_returns_message(self):
        client = _http_client(422)
        ok, msg = await add_budget_line(
            _make_deps(client),
            budget_id="b-1",
            description="X",
            amount=100.0,
            category_name="Misc",
        )
        assert ok is False
        assert "Failed" in msg


class TestGetBudgetSummary:
    @pytest.mark.anyio
    async def test_success_returns_summary(self):
        client = _http_client(
            200,
            {
                "name": "My Grant",
                "lines": [
                    {"description": "Staff", "amount": 5000},
                    {"description": "Travel", "amount": 2000},
                ],
            },
        )
        ok, msg = await get_budget_summary(_make_deps(client), budget_id="b-1")
        assert ok is True
        assert "My Grant" in msg
        assert "7000" in msg

    @pytest.mark.anyio
    async def test_404_returns_error_message(self):
        client = _http_client(404)
        ok, msg = await get_budget_summary(_make_deps(client), budget_id="missing")
        assert ok is False
        assert "Could not" in msg
