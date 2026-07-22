"""
Tests for donor-view access to a funded budget's detail page.

get_viewable_budget_service / get_viewable_budget_lines_service let a donor who
funds a budget view it, without granting write access — update/delete still go
through the original, stricter owner-only get_budget_service /
get_budget_line_by_id_service, untouched by this change.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.services.budget_services import _can_view_budget
from tests.factories.budget import BudgetFactory
from tests.factories.user import make_valid_user

OWNER_ID = str(uuid4())
FUNDER_ID = str(uuid4())
STRANGER_ID = str(uuid4())


def _budget():
    return BudgetFactory.build(owner_id=OWNER_ID, funding_customer_id=FUNDER_ID)


class TestCanViewBudget:
    def test_owner_can_view(self):
        assert _can_view_budget(_budget(), make_valid_user(customer_id=OWNER_ID))

    def test_funder_can_view(self):
        assert _can_view_budget(_budget(), make_valid_user(customer_id=FUNDER_ID))

    def test_stranger_cannot_view(self):
        assert not _can_view_budget(_budget(), make_valid_user(customer_id=STRANGER_ID))

    def test_superuser_can_view_regardless_of_customer_id(self):
        user = make_valid_user(role="superuser", customer_id=STRANGER_ID)
        assert _can_view_budget(_budget(), user)

    def test_missing_customer_id_cannot_view(self):
        user = make_valid_user(customer_id=STRANGER_ID)
        user["customer_id"] = None
        assert not _can_view_budget(_budget(), user)


class TestFunderCanViewFundedBudgetEndpoint:
    def test_funder_can_view_budget_they_dont_own(self, make_client):
        budget = _budget()
        client = make_client(customer_id=FUNDER_ID)

        with (
            patch("app.services.budget_services.get_budget", return_value=budget),
            patch(
                "app.services.budget_services.get_users_by_ids_cached",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.budget_services.get_customers_by_ids",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch("app.services.budget_line_services.get_budget", return_value=budget),
            patch("app.services.budget_line_services.list_budget_lines", return_value=[]),
        ):
            response = client.get(f"/api/v1/budgets/{budget.id}")

        assert response.status_code == 200
        assert response.json()["id"] == str(budget.id)

    def test_owner_can_still_view_their_own_budget(self, make_client):
        budget = _budget()
        client = make_client(customer_id=OWNER_ID)

        with (
            patch("app.services.budget_services.get_budget", return_value=budget),
            patch(
                "app.services.budget_services.get_users_by_ids_cached",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.budget_services.get_customers_by_ids",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch("app.services.budget_line_services.get_budget", return_value=budget),
            patch("app.services.budget_line_services.list_budget_lines", return_value=[]),
        ):
            response = client.get(f"/api/v1/budgets/{budget.id}")

        assert response.status_code == 200

    def test_unrelated_customer_gets_not_found(self, make_client):
        budget = _budget()
        client = make_client(customer_id=STRANGER_ID)

        with patch("app.services.budget_services.get_budget", return_value=budget):
            response = client.get(f"/api/v1/budgets/{budget.id}")

        assert response.status_code == 400
