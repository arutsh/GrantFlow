"""Route-level wiring checks for report_line_routes.py's business-context
span attributes, matching test_report_routes.py's TestReportRoutesWiring
convention. (Service-layer report-line tests live in
test_report_line_routes.py; this file is route-level only.)"""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4


class TestReportLineRoutesWiring:
    def test_create_route_sets_span_attributes(self, make_client):
        client = make_client()
        report_id = uuid4()
        report_line_id = uuid4()
        with (
            patch(
                "app.api.report_line_routes.create_report_line_service",
                return_value=SimpleNamespace(id=report_line_id),
            ),
            patch("app.api.report_line_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.post(
                "/api/v1/report-lines/",
                json={
                    "report_id": str(report_id),
                    "budget_line_id": str(uuid4()),
                    "description": "Bus tickets",
                    "amount": 50.0,
                    "expense_date": "2026-01-01",
                },
            )
        mock_set_span_attrs.assert_any_call(report_id=report_id)
        mock_set_span_attrs.assert_any_call(report_line_id=report_line_id)

    def test_update_route_sets_report_line_id_span_attribute(self, make_client):
        client = make_client()
        report_line_id = uuid4()
        with (
            patch(
                "app.api.report_line_routes.update_report_line_service",
                return_value=SimpleNamespace(id=report_line_id),
            ),
            patch("app.api.report_line_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.patch(
                f"/api/v1/report-lines/{report_line_id}",
                json={"report_id": str(uuid4()), "amount": 75.0},
            )
        mock_set_span_attrs.assert_any_call(report_line_id=report_line_id)

    def test_delete_route_sets_report_line_id_span_attribute(self, make_client):
        client = make_client()
        report_line_id = uuid4()
        with (
            patch(
                "app.api.report_line_routes.delete_report_line_service",
                return_value=True,
            ),
            patch("app.api.report_line_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.delete(f"/api/v1/report-lines/{report_line_id}")
        mock_set_span_attrs.assert_any_call(report_line_id=report_line_id)
