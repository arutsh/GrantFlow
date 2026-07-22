"""
Tests for budget service layer logic.

P2: populate_budget_with_user_details graceful degradation — when inter-service
    calls (users cache or customers HTTP) raise, the endpoint still returns 200
    with partial nulls instead of propagating a 500.
P3: create_budget_with_lines_service — asserts created budget gets status=ai_draft.
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from uuid import uuid4

from main import app
from app.api.budget_routes import get_validated_user
from tests.factories.user import make_valid_user
from tests.factories.budget import BudgetFactory, BudgetLineFactory

client = TestClient(app)

USER_ID = str(uuid4())
CUSTOMER_ID = str(uuid4())
_CATEGORY_LOOKUP = (
    "app.services.budget_category_services.get_budget_category_by_name_and_template_id"
)


def _mock_valid_user():
    return make_valid_user(user_id=USER_ID, customer_id=CUSTOMER_ID)


def _enriched(budget, lines=None):
    """Minimal enriched dict matching what populate_budget_with_user_details returns."""
    return {
        "id": budget.id,
        "name": budget.name,
        "owner": {"id": str(CUSTOMER_ID), "name": "Test NGO", "type": "ngo"},
        "funder": {"name": budget.external_funder_name},
        "trace": {
            "created": {"user": None, "event_date": None},
            "updated": {"user": None, "event_date": None},
        },
        "lines": lines or [],
    }


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_validated_user] = _mock_valid_user
    yield
    app.dependency_overrides = {}


# ---------------------------------------------------------------------------
# P2 — Graceful degradation
# ---------------------------------------------------------------------------


class TestPopulateBudgetGracefulDegradation:
    """
    GET /api/v1/budgets/{id} must return 200 even when the users service or
    customers service raises an exception during the enrichment step.
    """

    def test_returns_200_when_both_services_raise(self):
        budget = BudgetFactory.build(
            owner_id=CUSTOMER_ID,
            funding_customer_id=None,
            external_funder_name="Smith Foundation",
            created_by=USER_ID,
            updated_by=USER_ID,
        )

        with (
            patch("app.services.budget_services.get_budget", return_value=budget),
            patch(
                "app.services.budget_services.get_users_by_ids_cached",
                new_callable=AsyncMock,
                side_effect=Exception("users service unavailable"),
            ),
            patch(
                "app.services.budget_services.get_customers_by_ids",
                new_callable=AsyncMock,
                side_effect=Exception("customers service unavailable"),
            ),
            patch("app.api.budget_routes.get_viewable_budget_lines_service", return_value=[]),
        ):
            response = client.get(f"/api/v1/budgets/{budget.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(budget.id)
        assert data["owner"] is None

    def test_owner_is_null_when_customers_service_raises(self):
        budget = BudgetFactory.build(
            owner_id=CUSTOMER_ID,
            funding_customer_id=None,
            external_funder_name="Smith Foundation",
            created_by=USER_ID,
            updated_by=USER_ID,
        )

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
                side_effect=ConnectionError("timeout"),
            ),
            patch("app.api.budget_routes.get_viewable_budget_lines_service", return_value=[]),
        ):
            response = client.get(f"/api/v1/budgets/{budget.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["owner"] is None
        assert data["funder"]["name"] == "Smith Foundation"

    def test_trace_users_are_null_when_users_service_raises(self):
        budget = BudgetFactory.build(
            owner_id=CUSTOMER_ID,
            created_by=USER_ID,
            updated_by=USER_ID,
        )

        with (
            patch("app.services.budget_services.get_budget", return_value=budget),
            patch(
                "app.services.budget_services.get_users_by_ids_cached",
                new_callable=AsyncMock,
                side_effect=RuntimeError("users service down"),
            ),
            patch(
                "app.services.budget_services.get_customers_by_ids",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch("app.api.budget_routes.get_viewable_budget_lines_service", return_value=[]),
        ):
            response = client.get(f"/api/v1/budgets/{budget.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["trace"]["created"]["user"] is None
        assert data["trace"]["updated"]["user"] is None

    def test_returns_enriched_data_when_services_succeed(self):
        budget = BudgetFactory.build(
            owner_id=CUSTOMER_ID,
            created_by=USER_ID,
            updated_by=USER_ID,
        )
        users_map = {
            str(USER_ID): {
                "id": str(USER_ID),
                "first_name": "Alice",
                "last_name": "Smith",
                "email": "alice@example.com",
            }
        }
        customers_map = {
            str(CUSTOMER_ID): {"id": str(CUSTOMER_ID), "name": "Test NGO", "type": "ngo"}
        }

        with (
            patch("app.services.budget_services.get_budget", return_value=budget),
            patch(
                "app.services.budget_services.get_users_by_ids_cached",
                new_callable=AsyncMock,
                return_value=users_map,
            ),
            patch(
                "app.services.budget_services.get_customers_by_ids",
                new_callable=AsyncMock,
                return_value=customers_map,
            ),
            patch("app.api.budget_routes.get_viewable_budget_lines_service", return_value=[]),
        ):
            response = client.get(f"/api/v1/budgets/{budget.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["owner"]["name"] == "Test NGO"
        assert data["trace"]["created"]["user"]["first_name"] == "Alice"


# ---------------------------------------------------------------------------
# P3 — ai_draft status
# ---------------------------------------------------------------------------

VALID_PAYLOAD = {
    "budget_name": "AI-Generated Budget",
    "external_funder_name": "Smith Foundation",
    "duration_months": 12,
    "lines": [
        {"category_name": "Personnel", "description": "2 FTE staff", "amount": 100000.0},
    ],
}


class TestAiDraftBudgetStatus:
    """
    POST /api/v1/budgets/with-lines must create the budget with status=ai_draft.
    Manually created budgets via POST /api/v1/budgets/ default to status=draft.
    """

    def test_with_lines_creates_budget_with_ai_draft_status(self):
        from app.schemas.budget_schema import BudgetStatus

        budget = BudgetFactory.build(
            owner_id=CUSTOMER_ID,
            external_funder_name="Smith Foundation",
            created_by=USER_ID,
            updated_by=USER_ID,
        )
        line = BudgetLineFactory.build(budget_id=budget.id, created_by=USER_ID)

        with (
            patch("app.services.budget_services.create_budget", return_value=budget) as mock_create,
            patch("app.services.budget_line_services.get_budget", return_value=budget),
            patch(
                _CATEGORY_LOOKUP,
                return_value=line.category,
            ),
            patch(
                "app.services.budget_line_services.create_budget_line",
                return_value=line,
            ),
            patch("app.services.budget_line_services.recalculate_budget_total"),
            patch(
                "app.services.budget_services.get_budget_service",
                new_callable=AsyncMock,
                return_value=_enriched(budget),
            ),
        ):
            response = client.post("/api/v1/budgets/with-lines", json=VALID_PAYLOAD)

        assert response.status_code == 200
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("status") == BudgetStatus.ai_draft

    def test_manual_budget_create_defaults_to_draft(self):
        from app.schemas.budget_schema import BudgetStatus

        budget = BudgetFactory.build(
            owner_id=CUSTOMER_ID,
            external_funder_name="Donor Corp",
            created_by=USER_ID,
            updated_by=USER_ID,
        )

        with (
            patch("app.services.budget_services.create_budget", return_value=budget) as mock_create,
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
        ):
            response = client.post(
                "/api/v1/budgets/",
                json={"name": "Manual Budget", "external_funder_name": "Donor Corp"},
            )

        assert response.status_code == 200
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("status") != BudgetStatus.ai_draft
