"""Route-level wiring for budget_category_routes.py; ownership/lock is
real-DB tested in test_budget_category_services.py."""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import status

from app.core.exceptions import DomainError


class TestListBudgetCategoriesRoute:
    def test_delegates_to_service_and_sets_span_attribute(self, make_client):
        client = make_client()
        budget_id = uuid4()
        with (
            patch(
                "app.api.budget_category_routes.list_budget_categories_service",
                return_value=[],
            ) as mock_service,
            patch("app.api.budget_category_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            response = client.get(f"/api/v1/budget-categories/by-budget/{budget_id}")

        assert response.status_code == 200
        assert response.json() == []
        mock_service.assert_called_once()
        mock_set_span_attrs.assert_any_call(budget_id=budget_id)

    def test_ownership_rejection_propagates_status_code(self, make_client):
        client = make_client()
        with patch(
            "app.api.budget_category_routes.list_budget_categories_service",
            side_effect=DomainError("Budget Not found", status.HTTP_400_BAD_REQUEST),
        ):
            response = client.get(f"/api/v1/budget-categories/by-budget/{uuid4()}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUpdateBudgetCategoryRoute:
    def test_category_not_found_returns_404(self, make_client):
        client = make_client()
        with patch(
            "app.api.budget_category_routes.get_budget_category_by_id_service",
            side_effect=DomainError("Budget Category not found", status.HTTP_404_NOT_FOUND),
        ):
            response = client.patch(
                f"/api/v1/budget-categories/{uuid4()}", json={"name": "Transport"}
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_ownership_rejection_propagates_status_code(self, make_client):
        client = make_client()
        budget_id = uuid4()
        category_id = uuid4()
        with (
            patch(
                "app.api.budget_category_routes.get_budget_category_by_id_service",
                return_value=SimpleNamespace(
                    id=category_id, budget_id=budget_id, name="Travel", code="TRAVEL"
                ),
            ),
            patch(
                "app.api.budget_category_routes.update_budget_category_service",
                side_effect=DomainError("Budget Category not found", status.HTTP_404_NOT_FOUND),
            ),
        ):
            response = client.patch(
                f"/api/v1/budget-categories/{category_id}", json={"name": "Hijacked"}
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_lock_rejection_propagates_status_code(self, make_client):
        client = make_client()
        budget_id = uuid4()
        category_id = uuid4()
        with (
            patch(
                "app.api.budget_category_routes.get_budget_category_by_id_service",
                return_value=SimpleNamespace(
                    id=category_id, budget_id=budget_id, name="Travel", code="TRAVEL"
                ),
            ),
            patch(
                "app.api.budget_category_routes.update_budget_category_service",
                side_effect=DomainError(
                    "Budget categories cannot be changed once the budget is confirmed",
                    status.HTTP_400_BAD_REQUEST,
                ),
            ),
        ):
            response = client.patch(
                f"/api/v1/budget-categories/{category_id}", json={"name": "Transport"}
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_happy_path_falls_back_to_existing_name_and_code(self, make_client):
        client = make_client()
        budget_id = uuid4()
        category_id = uuid4()
        existing = SimpleNamespace(
            id=category_id, budget_id=budget_id, name="Travel", code="TRAVEL"
        )
        with (
            patch(
                "app.api.budget_category_routes.get_budget_category_by_id_service",
                return_value=existing,
            ),
            patch(
                "app.api.budget_category_routes.update_budget_category_service",
                return_value=SimpleNamespace(
                    id=category_id,
                    budget_id=budget_id,
                    name="Travel",
                    code="NEWCODE",
                    created_by=uuid4(),
                    updated_by=uuid4(),
                ),
            ) as mock_service,
            patch("app.api.budget_category_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            response = client.patch(
                f"/api/v1/budget-categories/{category_id}", json={"code": "NEWCODE"}
            )

        assert response.status_code == 200
        _, call_args, call_kwargs = mock_service.mock_calls[0]
        assert call_args[1] == client.user
        assert call_kwargs == {
            "budget_id": budget_id,
            "category_id": category_id,
            "name": "Travel",
            "code": "NEWCODE",
        }
        mock_set_span_attrs.assert_any_call(budget_category_id=category_id)


class TestDeleteBudgetCategoryRoute:
    def test_category_not_found_returns_404(self, make_client):
        client = make_client()
        with patch(
            "app.api.budget_category_routes.get_budget_category_by_id_service",
            side_effect=DomainError("Budget Category not found", status.HTTP_404_NOT_FOUND),
        ):
            response = client.delete(f"/api/v1/budget-categories/{uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_lock_rejection_propagates_status_code(self, make_client):
        client = make_client()
        budget_id = uuid4()
        category_id = uuid4()
        with (
            patch(
                "app.api.budget_category_routes.get_budget_category_by_id_service",
                return_value=SimpleNamespace(id=category_id, budget_id=budget_id),
            ),
            patch(
                "app.api.budget_category_routes.delete_budget_category_service",
                side_effect=DomainError(
                    "Budget categories cannot be changed once the budget is confirmed",
                    status.HTTP_400_BAD_REQUEST,
                ),
            ),
        ):
            response = client.delete(f"/api/v1/budget-categories/{category_id}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_happy_path_deletes_and_sets_span_attribute(self, make_client):
        client = make_client()
        budget_id = uuid4()
        category_id = uuid4()
        with (
            patch(
                "app.api.budget_category_routes.get_budget_category_by_id_service",
                return_value=SimpleNamespace(id=category_id, budget_id=budget_id),
            ),
            patch(
                "app.api.budget_category_routes.delete_budget_category_service",
                return_value=True,
            ) as mock_service,
            patch("app.api.budget_category_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            response = client.delete(f"/api/v1/budget-categories/{category_id}")

        assert response.status_code == 200
        assert response.json() is True
        mock_service.assert_called_once()
        mock_set_span_attrs.assert_any_call(budget_category_id=category_id)
