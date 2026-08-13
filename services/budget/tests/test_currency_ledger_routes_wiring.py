"""Route-level wiring checks for funding_receipt_routes.py and
currency_conversion_routes.py's business-context span attributes, matching
test_report_routes.py's TestReportRoutesWiring convention. (Service-layer
ledger tests live in test_currency_ledger.py; this file is route-level
only.) Both routers only expose create endpoints (no update/delete)."""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4


class TestFundingReceiptRoutesWiring:
    def test_create_route_sets_span_attributes(self, make_client):
        client = make_client()
        budget_id = uuid4()
        receipt_id = uuid4()
        with (
            patch(
                "app.api.funding_receipt_routes.record_receipt_service",
                return_value=SimpleNamespace(id=receipt_id),
            ),
            patch("app.api.funding_receipt_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.post(
                "/api/v1/funding-receipts/",
                json={
                    "budget_id": str(budget_id),
                    "amount": 1000.0,
                    "received_at": "2026-01-01",
                },
            )
        mock_set_span_attrs.assert_any_call(budget_id=budget_id)
        mock_set_span_attrs.assert_any_call(funding_receipt_id=receipt_id)


class TestCurrencyConversionRoutesWiring:
    def test_create_route_sets_span_attributes(self, make_client):
        client = make_client()
        budget_id = uuid4()
        conversion_id = uuid4()
        with (
            patch(
                "app.api.currency_conversion_routes.record_conversion_service",
                return_value=SimpleNamespace(id=conversion_id),
            ),
            patch(
                "app.api.currency_conversion_routes.set_span_attributes"
            ) as mock_set_span_attrs,
        ):
            client.post(
                "/api/v1/currency-conversions/",
                json={
                    "budget_id": str(budget_id),
                    "donor_amount": 1000.0,
                    "local_amount": 800.0,
                    "converted_at": "2026-01-01",
                },
            )
        mock_set_span_attrs.assert_any_call(budget_id=budget_id)
        mock_set_span_attrs.assert_any_call(conversion_id=conversion_id)
