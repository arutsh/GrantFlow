from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from app.services.excel_extraction_service import run_excel_extraction
from app.services.prompt_loader import LoadedPrompt
from app.services.provider import ResolvedModel

_AUDIT = "app.services.excel_extraction_service.write_audit_log"
_PROMPT = "app.services.excel_extraction_service.load_prompt"

_FAKE_PROMPT = LoadedPrompt(
    name="excel_budget_extraction",
    version="v1",
    system_prompt="extract lines",
    user_template="{{ rows_json }}",
)


def _resolved(model, provider="anthropic", model_name="claude-test") -> ResolvedModel:
    return ResolvedModel(model=model, provider_name=provider, model_name=model_name)


def _test_model() -> TestModel:
    return TestModel(
        custom_output_args={
            "local_currency": "EUR",
            "local_currency_confidence": 0.9,
            "lines": [
                {
                    "category_name": "Personnel",
                    "description": "Salaries",
                    "local_amount": 1000.0,
                    "confidence": 0.9,
                    "extra_fields": None,
                }
            ],
            "column_map": {"category_col": 0, "description_col": 1, "amount_col": 2},
        }
    )


class TestRunExcelExtraction:
    @pytest.mark.anyio
    async def test_returns_structured_result_and_writes_audit_log(self):
        with (
            patch(_PROMPT, AsyncMock(return_value=_FAKE_PROMPT)),
            patch(_AUDIT, new=AsyncMock()) as mock_audit,
        ):
            result = await run_excel_extraction(
                rows=[["Salaries", "1000"]],
                resolved=_resolved(_test_model()),
                funding_source="byok",
                customer_id="cust-1",
                user_id="user-1",
            )

        assert result.local_currency == "EUR"
        assert result.lines[0].category_name == "Personnel"
        mock_audit.assert_awaited_once()
        assert mock_audit.call_args.kwargs["funding_source"] == "byok"
        assert mock_audit.call_args.kwargs["success"] is True
        assert mock_audit.call_args.kwargs["provider"] == "anthropic"

    @pytest.mark.anyio
    async def test_platform_funding_source_reaches_audit_log(self):
        with (
            patch(_PROMPT, AsyncMock(return_value=_FAKE_PROMPT)),
            patch(_AUDIT, new=AsyncMock()) as mock_audit,
        ):
            await run_excel_extraction(
                rows=[["Salaries", "1000"]],
                resolved=_resolved(_test_model()),
                funding_source="platform",
                customer_id="cust-1",
                user_id="user-1",
            )

        assert mock_audit.call_args.kwargs["funding_source"] == "platform"

    @pytest.mark.anyio
    async def test_model_failure_writes_audit_log_and_reraises(self):
        class _BoomModel(TestModel):
            pass

        boom = _BoomModel()

        with (
            patch(_PROMPT, AsyncMock(return_value=_FAKE_PROMPT)),
            patch(_AUDIT, new=AsyncMock()) as mock_audit,
            patch(
                "app.services.excel_extraction_service.Agent.run",
                AsyncMock(side_effect=RuntimeError("model exploded")),
            ),
            pytest.raises(RuntimeError),
        ):
            await run_excel_extraction(
                rows=[["Salaries", "1000"]],
                resolved=_resolved(boom),
                funding_source="byok",
                customer_id="cust-1",
                user_id="user-1",
            )

        assert mock_audit.call_args.kwargs["success"] is False
        assert "model exploded" in mock_audit.call_args.kwargs["error_message"]
