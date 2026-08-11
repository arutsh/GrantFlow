import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.budget_client import get_financial_record_refs


def _client_returning(budgets: list, reports: list) -> MagicMock:
    """A fake httpx.AsyncClient whose .get() responds based on the
    requested path — matches the two calls get_financial_record_refs makes
    (one for budgets, one for reports)."""

    def _make_response(payload):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=payload)
        return resp

    async def _get(path, *args, **kwargs):
        if "budgets" in path:
            return _make_response(budgets)
        return _make_response(reports)

    client = MagicMock()
    client.get = AsyncMock(side_effect=_get)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class TestGetFinancialRecordRefs:
    def test_combines_budgets_and_reports(self):
        client = _client_returning(
            budgets=[{"id": "b1", "name": "Budget 1", "type": "budget"}],
            reports=[{"id": "r1", "name": "Report 1", "type": "report"}],
        )
        with patch(
            "app.services.budget_client.httpx.AsyncClient", return_value=client
        ) as mock_async_client:
            result = asyncio.run(get_financial_record_refs("user-1", "fake-token"))

        assert {"id": "b1", "name": "Budget 1", "type": "budget"} in result
        assert {"id": "r1", "name": "Report 1", "type": "report"} in result
        assert len(result) == 2
        # The by-creator endpoints are self-service only (403 unless the
        # token's subject matches user_id) — the caller's own token must be
        # forwarded, or every export would 403 against budget-service.
        assert mock_async_client.call_args.kwargs["headers"] == {
            "Authorization": "Bearer fake-token"
        }

    def test_budget_service_unreachable_degrades_to_empty_list(self):
        client = MagicMock()
        client.get = AsyncMock(side_effect=ConnectionError("budget service down"))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.budget_client.httpx.AsyncClient", return_value=client):
            result = asyncio.run(get_financial_record_refs("user-1", "fake-token"))

        assert result == []
