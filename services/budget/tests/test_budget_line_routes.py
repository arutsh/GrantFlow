"""Route-level wiring checks for budget_line_routes.py's business-context
span attributes, matching test_report_routes.py's TestReportRoutesWiring
convention."""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4


class TestBudgetLineRoutesWiring:
    def test_create_route_sets_span_attributes(self, make_client):
        client = make_client()
        budget_id = uuid4()
        budget_line_id = uuid4()
        with (
            patch(
                "app.api.budget_line_routes.create_budget_line_service",
                return_value=SimpleNamespace(
                    id=budget_line_id, budget_id=budget_id, description="Travel", amount=100.0
                ),
            ),
            patch("app.api.budget_line_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.post(
                "/api/v1/budget-lines/",
                json={
                    "budget_id": str(budget_id),
                    "description": "Travel",
                    "amount": 100.0,
                    "category_name": "Travel",
                },
            )
        mock_set_span_attrs.assert_any_call(budget_id=budget_id)
        mock_set_span_attrs.assert_any_call(budget_line_id=budget_line_id)

    def test_update_route_sets_budget_line_id_span_attribute(self, make_client):
        client = make_client()
        budget_line_id = uuid4()
        with (
            patch(
                "app.api.budget_line_routes.update_budget_line_service",
                return_value=SimpleNamespace(
                    id=budget_line_id, budget_id=uuid4(), description="Travel", amount=200.0
                ),
            ),
            patch("app.api.budget_line_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.patch(
                f"/api/v1/budget-lines/{budget_line_id}/",
                json={"budget_id": str(uuid4()), "amount": 200.0},
            )
        mock_set_span_attrs.assert_any_call(budget_line_id=budget_line_id)

    def test_delete_route_sets_budget_line_id_span_attribute(self, make_client):
        client = make_client()
        budget_line_id = uuid4()
        with (
            patch(
                "app.api.budget_line_routes.delete_budget_line_service",
                return_value=True,
            ),
            patch("app.api.budget_line_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.delete(f"/api/v1/budget-lines/{budget_line_id}/")
        mock_set_span_attrs.assert_any_call(budget_line_id=budget_line_id)
