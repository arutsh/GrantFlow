"""Budget-category ownership scoping tests — uses the real-sqlite `db` fixture (conftest.py)."""

from uuid import uuid4

import pytest

from app.core.exceptions import DomainError
from app.models.budget import BudgetCategoryModel
from app.schemas.budget_schema import BudgetStatus
from app.services.budget_category_services import (
    get_or_create_category_service,
    get_or_create_categories_by_names_service,
    update_budget_category_service,
    delete_budget_category_service,
)
from tests.factories.budget import BudgetFactory
from tests.factories.user import ValidUserFactory

OWNER_ID = str(uuid4())
STRANGER_ID = str(uuid4())


def _make_budget(db, owner_id=OWNER_ID, status=BudgetStatus.draft, **overrides):
    budget = BudgetFactory.build(owner_id=owner_id, status=status, **overrides)
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def _valid_user(customer_id=OWNER_ID, user_id=None):
    return ValidUserFactory(customer_id=customer_id, user_id=user_id or str(uuid4()))


class TestGetOrCreateCategoryScoping:
    def test_same_name_in_two_budgets_creates_two_rows(self, db):
        budget_a = _make_budget(db)
        budget_b = _make_budget(db)
        user = _valid_user()

        category_a = get_or_create_category_service(
            db, user, budget_id=budget_a.id, category_name="Travel"
        )
        category_b = get_or_create_category_service(
            db, user, budget_id=budget_b.id, category_name="Travel"
        )

        assert category_a.id != category_b.id
        assert category_a.budget_id == budget_a.id
        assert category_b.budget_id == budget_b.id

    def test_same_name_in_one_budget_reuses_the_same_row(self, db):
        budget = _make_budget(db)
        user = _valid_user()

        first = get_or_create_category_service(
            db, user, budget_id=budget.id, category_name="Travel"
        )
        second = get_or_create_category_service(
            db, user, budget_id=budget.id, category_name="Travel"
        )

        assert first.id == second.id
        count = (
            db.query(BudgetCategoryModel).filter(BudgetCategoryModel.budget_id == budget.id).count()
        )
        assert count == 1

    def test_category_id_from_another_budget_is_rejected(self, db):
        budget_a = _make_budget(db)
        budget_b = _make_budget(db)
        user = _valid_user()
        other_budget_category = get_or_create_category_service(
            db, user, budget_id=budget_a.id, category_name="Travel"
        )

        with pytest.raises(DomainError):
            get_or_create_category_service(
                db, user, budget_id=budget_b.id, category_id=other_budget_category.id
            )


class TestGetOrCreateCategoriesByNamesScoping:
    def test_repeated_names_in_one_budget_dedupe_to_one_row_each(self, db):
        budget = _make_budget(db)
        user = _valid_user()

        result = get_or_create_categories_by_names_service(
            db, user, budget_id=budget.id, category_names=["Travel", "Travel", "Personnel"]
        )

        assert set(result.keys()) == {"Travel", "Personnel"}
        count = (
            db.query(BudgetCategoryModel).filter(BudgetCategoryModel.budget_id == budget.id).count()
        )
        assert count == 2

    def test_same_name_across_budgets_is_not_shared(self, db):
        budget_a = _make_budget(db)
        budget_b = _make_budget(db)
        user = _valid_user()

        result_a = get_or_create_categories_by_names_service(
            db, user, budget_id=budget_a.id, category_names=["Personnel"]
        )
        result_b = get_or_create_categories_by_names_service(
            db, user, budget_id=budget_b.id, category_names=["Personnel"]
        )

        assert result_a["Personnel"].id != result_b["Personnel"].id


class TestUpdateBudgetCategoryService:
    def test_owner_can_rename_and_updated_by_is_set(self, db):
        budget = _make_budget(db)
        owner = _valid_user()
        category = get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )

        editor = _valid_user(user_id=str(uuid4()))
        updated = update_budget_category_service(
            db, editor, budget.id, category.id, name="Transport", code="TRANSPORT"
        )

        assert updated.name == "Transport"
        assert updated.code == "TRANSPORT"
        assert str(updated.updated_by) == editor["user_id"]

    def test_rename_rejected_for_another_customers_budget(self, db):
        budget = _make_budget(db, owner_id=OWNER_ID)
        owner = _valid_user(customer_id=OWNER_ID)
        category = get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )

        stranger = _valid_user(customer_id=STRANGER_ID)
        with pytest.raises(DomainError):
            update_budget_category_service(db, stranger, budget.id, category.id, name="Hijacked")

    def test_rename_rejected_once_budget_is_confirmed(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed)
        owner = _valid_user()
        category = get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )

        with pytest.raises(DomainError):
            update_budget_category_service(db, owner, budget.id, category.id, name="Transport")

    def test_rename_rejected_when_budget_id_does_not_match_category(self, db):
        budget_a = _make_budget(db)
        budget_b = _make_budget(db)
        owner = _valid_user()
        category = get_or_create_category_service(
            db, owner, budget_id=budget_a.id, category_name="Travel"
        )

        with pytest.raises(DomainError):
            update_budget_category_service(db, owner, budget_b.id, category.id, name="Hijacked")


class TestDeleteBudgetCategoryService:
    def test_owner_can_delete(self, db):
        budget = _make_budget(db)
        owner = _valid_user()
        category = get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )

        result = delete_budget_category_service(db, owner, budget.id, category.id)

        assert result is True
        remaining = (
            db.query(BudgetCategoryModel).filter(BudgetCategoryModel.id == category.id).first()
        )
        assert remaining is None

    def test_delete_rejected_for_another_customers_budget(self, db):
        budget = _make_budget(db, owner_id=OWNER_ID)
        owner = _valid_user(customer_id=OWNER_ID)
        category = get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )

        stranger = _valid_user(customer_id=STRANGER_ID)
        with pytest.raises(DomainError):
            delete_budget_category_service(db, stranger, budget.id, category.id)

    def test_delete_rejected_once_budget_is_confirmed(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed)
        owner = _valid_user()
        category = get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )

        with pytest.raises(DomainError):
            delete_budget_category_service(db, owner, budget.id, category.id)

    def test_delete_rejected_when_budget_id_does_not_match_category(self, db):
        budget_a = _make_budget(db)
        budget_b = _make_budget(db)
        owner = _valid_user()
        category = get_or_create_category_service(
            db, owner, budget_id=budget_a.id, category_name="Travel"
        )

        with pytest.raises(DomainError):
            delete_budget_category_service(db, owner, budget_b.id, category.id)
