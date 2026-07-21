import pytest
from typing import Any
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from uuid import uuid4

from main import app
from app.api.budget_routes import get_validated_user
from tests.factories.user import make_valid_user
from tests.factories.budget import BudgetLineFactory, BudgetCategoryFactory

client = TestClient(app)

BUDGET_ID = str(uuid4())
USER_ID = str(uuid4())
CUSTOMER_ID = str(uuid4())
LINE_ID_1 = str(uuid4())
LINE_ID_2 = str(uuid4())
CATEGORY_ID = str(uuid4())

VALID_PAYLOAD: dict[str, Any] = {
    "budget_name": "Youth Program 2025",
    "external_funder_name": "Smith Foundation",
    "duration_months": 12,
    "lines": [
        {"category_name": "Personnel", "description": "2 FTE staff", "amount": 100000.0},
        {"category_name": "Supplies", "description": "Program supplies", "amount": 5000.0},
    ],
}

_CATEGORY_LOOKUP = (
    "app.services.budget_category_services" ".get_budget_category_by_name_and_template_id"
)


def _mock_valid_user():
    return make_valid_user(user_id=USER_ID, customer_id=CUSTOMER_ID)


def _mock_budget(budget_id=None):
    m = MagicMock()
    m.id = budget_id or BUDGET_ID
    m.name = "Youth Program 2025"
    m.owner_id = CUSTOMER_ID
    m.external_funder_name = "Smith Foundation"
    m.duration_months = 12
    m.funding_customer_id = None
    m.created_by = USER_ID
    m.updated_by = USER_ID
    m.created_at = None
    m.updated_at = None
    m.status = "draft"
    m.local_currency = "GBP"
    return m


def _mock_line(line_id, category_name="Personnel"):
    return BudgetLineFactory.build(
        id=line_id,
        budget_id=BUDGET_ID,
        category_id=CATEGORY_ID,
        description="test",
        amount=1000.0,
        category=BudgetCategoryFactory.build(
            id=CATEGORY_ID, name=category_name, code=category_name.upper()
        ),
    )


def _mock_category(name="Personnel"):
    return BudgetCategoryFactory.build(id=CATEGORY_ID, name=name, code=name.upper())


def _mock_enriched_budget(lines=None) -> dict:
    return {
        "id": BUDGET_ID,
        "name": "Youth Program 2025",
        "owner": {"id": CUSTOMER_ID, "name": "Test NGO", "type": "ngo"},
        "funder": {"name": "Smith Foundation"},
        "trace": {
            "created": {"user": {"id": USER_ID}, "event_date": None},
            "updated": {"user": {"id": USER_ID}, "event_date": None},
        },
        "lines": lines or [],
    }


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_validated_user] = _mock_valid_user
    yield
    app.dependency_overrides = {}


class TestCreateBudgetWithLinesEndpoint:
    def test_creates_budget_and_all_lines(self):
        mock_budget = _mock_budget()
        mock_lines = [_mock_line(LINE_ID_1, "Personnel"), _mock_line(LINE_ID_2, "Supplies")]

        with (
            patch("app.services.budget_services.create_budget", return_value=mock_budget),
            patch("app.services.budget_line_services.get_budget", return_value=mock_budget),
            patch(_CATEGORY_LOOKUP, return_value=_mock_category()),
            patch("app.services.budget_line_services.create_budget_line", side_effect=mock_lines),
            patch("app.services.budget_line_services.recalculate_budget_total"),
            patch(
                "app.services.budget_services.get_budget_service",
                new_callable=AsyncMock,
                return_value=_mock_enriched_budget(mock_lines),
            ),
        ):
            response = client.post("/api/v1/budgets/with-lines", json=VALID_PAYLOAD)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Youth Program 2025"
        assert len(data["lines"]) == 2

    def test_returns_full_budget_with_enriched_details(self):
        mock_budget = _mock_budget()
        mock_line = _mock_line(LINE_ID_1)
        payload = {**VALID_PAYLOAD, "lines": [VALID_PAYLOAD["lines"][0]]}
        with (
            patch("app.services.budget_services.create_budget", return_value=mock_budget),
            patch("app.services.budget_line_services.get_budget", return_value=mock_budget),
            patch(_CATEGORY_LOOKUP, return_value=_mock_category()),
            patch("app.services.budget_line_services.create_budget_line", return_value=mock_line),
            patch("app.services.budget_line_services.recalculate_budget_total"),
            patch(
                "app.services.budget_services.get_budget_service",
                new_callable=AsyncMock,
                return_value=_mock_enriched_budget([mock_line]),
            ),
        ):
            response = client.post("/api/v1/budgets/with-lines", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "owner" in data
        assert "funder" in data
        assert data["funder"]["name"] == "Smith Foundation"

    def test_requires_authentication(self):
        app.dependency_overrides = {}
        response = client.post("/api/v1/budgets/with-lines", json=VALID_PAYLOAD)
        assert response.status_code == 401
        app.dependency_overrides[get_validated_user] = _mock_valid_user

    def test_rolls_back_on_second_line_failure(self):
        """If the second line fails, the first line and budget are cleaned up."""
        mock_budget = _mock_budget()
        first_line = _mock_line(LINE_ID_1)
        call_count = {"n": 0}

        def line_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return first_line
            raise Exception("DB error on second line")

        with (
            patch("app.services.budget_services.create_budget", return_value=mock_budget),
            patch("app.services.budget_line_services.get_budget", return_value=mock_budget),
            patch(_CATEGORY_LOOKUP, return_value=_mock_category()),
            patch(
                "app.services.budget_line_services.create_budget_line", side_effect=line_side_effect
            ),
            patch("app.services.budget_line_services.recalculate_budget_total"),
            patch("app.services.budget_services.delete_budget_line") as mock_delete_line,
            patch("app.services.budget_services.delete_budget") as mock_delete_budget,
        ):
            response = client.post("/api/v1/budgets/with-lines", json=VALID_PAYLOAD)

        assert response.status_code == 500
        mock_delete_line.assert_called_once()
        mock_delete_budget.assert_called_once()

    def test_rolls_back_budget_if_first_line_fails(self):
        """If the very first line fails, no lines to clean up — only budget is deleted."""
        mock_budget = _mock_budget()

        with (
            patch("app.services.budget_services.create_budget", return_value=mock_budget),
            patch("app.services.budget_line_services.get_budget", return_value=mock_budget),
            patch(_CATEGORY_LOOKUP, return_value=_mock_category()),
            patch(
                "app.services.budget_line_services.create_budget_line",
                side_effect=Exception("DB error"),
            ),
            patch("app.services.budget_services.delete_budget_line") as mock_delete_line,
            patch("app.services.budget_services.delete_budget") as mock_delete_budget,
        ):
            response = client.post("/api/v1/budgets/with-lines", json=VALID_PAYLOAD)

        assert response.status_code == 500
        mock_delete_line.assert_not_called()
        mock_delete_budget.assert_called_once()

    def test_duration_months_is_optional(self):
        payload = {
            "budget_name": "Simple Budget",
            "external_funder_name": "Donor Corp",
            "lines": [{"category_name": "Travel", "description": "Transport", "amount": 2000.0}],
        }
        mock_budget = _mock_budget()
        mock_line = _mock_line(LINE_ID_1, "Travel")

        with (
            patch("app.services.budget_services.create_budget", return_value=mock_budget),
            patch("app.services.budget_line_services.get_budget", return_value=mock_budget),
            patch(_CATEGORY_LOOKUP, return_value=_mock_category("Travel")),
            patch("app.services.budget_line_services.create_budget_line", return_value=mock_line),
            patch("app.services.budget_line_services.recalculate_budget_total"),
            patch(
                "app.services.budget_services.get_budget_service",
                new_callable=AsyncMock,
                return_value=_mock_enriched_budget([mock_line]),
            ),
        ):
            response = client.post("/api/v1/budgets/with-lines", json=payload)

        assert response.status_code == 200

    def test_rejects_payload_missing_budget_name(self):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "budget_name"}
        response = client.post("/api/v1/budgets/with-lines", json=payload)
        assert response.status_code == 422

    def test_rejects_payload_missing_funder_name(self):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "external_funder_name"}
        response = client.post("/api/v1/budgets/with-lines", json=payload)
        assert response.status_code == 422
