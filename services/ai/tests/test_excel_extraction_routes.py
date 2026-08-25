from unittest.mock import AsyncMock, patch

from pydantic_ai.exceptions import UnexpectedModelBehavior

from shared.ai_client.schemas import (
    ExcelExtractionColumnMap,
    ExcelExtractionLine,
    ExcelExtractionResult,
)
from tests.factories.provider import ResolvedModelFactory


def _body(**overrides) -> dict:
    body = {"rows": [["Salaries", "1000"], ["Travel", "200"]]}
    body.update(overrides)
    return body


def _result() -> ExcelExtractionResult:
    return ExcelExtractionResult(
        local_currency="EUR",
        local_currency_confidence=0.9,
        lines=[
            ExcelExtractionLine(
                category_name="Personnel",
                description="Salaries",
                local_amount=1000.0,
                confidence=0.9,
            )
        ],
        column_map=ExcelExtractionColumnMap(category_col=0, description_col=0, amount_col=1),
    )


class TestExtractBudgetExcelRoute:
    def test_byok_path_does_not_touch_platform_rate_limit(self, make_client):
        client = make_client(resolved=True)
        with (
            patch(
                "app.api.excel_extraction_routes.run_excel_extraction",
                AsyncMock(return_value=_result()),
            ) as mock_run,
            patch("app.api.excel_extraction_routes.enforce_rate_limit") as mock_rate_limit,
        ):
            resp = client.post("/api/v1/ai/extract-budget-excel", json=_body())

        assert resp.status_code == 200
        assert resp.json()["local_currency"] == "EUR"
        mock_rate_limit.assert_not_called()
        assert mock_run.call_args.kwargs["funding_source"] == "byok"

    def test_falls_back_to_platform_funded_model_when_no_provider_key(self, make_client):
        client = make_client(resolved=None)
        platform_model = ResolvedModelFactory()
        with (
            patch(
                "app.api.excel_extraction_routes.resolve_platform_funded_model",
                return_value=platform_model,
            ),
            patch(
                "app.api.excel_extraction_routes.enforce_rate_limit", AsyncMock(return_value=None)
            ) as mock_rate_limit,
            patch(
                "app.api.excel_extraction_routes.run_excel_extraction",
                AsyncMock(return_value=_result()),
            ) as mock_run,
        ):
            resp = client.post("/api/v1/ai/extract-budget-excel", json=_body())

        assert resp.status_code == 200
        mock_rate_limit.assert_called_once()
        assert mock_rate_limit.call_args.kwargs["scope"] == "excel-import-platform"
        assert mock_run.call_args.kwargs["funding_source"] == "platform"
        assert mock_run.call_args.kwargs["resolved"] is platform_model

    def test_no_provider_and_no_platform_key_returns_503(self, make_client):
        client = make_client(resolved=None)
        with patch(
            "app.api.excel_extraction_routes.resolve_platform_funded_model", return_value=None
        ):
            resp = client.post("/api/v1/ai/extract-budget-excel", json=_body())

        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "no_provider"

    def test_platform_funded_rate_limit_enforced(self, make_client):
        from fastapi import HTTPException

        client = make_client(resolved=None)
        platform_model = ResolvedModelFactory()
        with (
            patch(
                "app.api.excel_extraction_routes.resolve_platform_funded_model",
                return_value=platform_model,
            ),
            patch(
                "app.api.excel_extraction_routes.enforce_rate_limit",
                AsyncMock(
                    side_effect=HTTPException(
                        status_code=429, detail="rate limited", headers={"Retry-After": "60"}
                    )
                ),
            ),
        ):
            resp = client.post("/api/v1/ai/extract-budget-excel", json=_body())

        assert resp.status_code == 429
        assert resp.headers["Retry-After"] == "60"

    def test_model_error_returns_502(self, make_client):
        client = make_client(resolved=True)
        with patch(
            "app.api.excel_extraction_routes.run_excel_extraction",
            AsyncMock(side_effect=UnexpectedModelBehavior("tool exceeded max retries")),
        ):
            resp = client.post("/api/v1/ai/extract-budget-excel", json=_body())

        assert resp.status_code == 502
        assert resp.json()["detail"]["code"] == "model_error"
