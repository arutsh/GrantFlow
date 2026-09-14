"""Budget-category ownership scoping tests — uses the real-sqlite `db` fixture (conftest.py)."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.exceptions import DomainError
from app.models.budget import BudgetCategoryModel
from app.schemas.budget_schema import BudgetStatus
from app.services.budget_category_services import (
    get_or_create_category_service,
    get_or_create_categories_by_names_service,
    update_budget_category_service,
    delete_budget_category_service,
)
from tests.factories.budget import BudgetFactory, BudgetLineFactory
from tests.factories.user import ValidUserFactory

pytestmark = pytest.mark.anyio

OWNER_ID = str(uuid4())
STRANGER_ID = str(uuid4())


async def _make_budget(db, owner_id=OWNER_ID, status=BudgetStatus.draft, **overrides):
    budget = BudgetFactory.build(owner_id=owner_id, status=status, **overrides)
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


def _valid_user(customer_id=OWNER_ID, user_id=None):
    return ValidUserFactory(customer_id=customer_id, user_id=user_id or str(uuid4()))


async def _make_budget_line(db, budget, category, **overrides):
    # Pass real objects, not ids — see budget_category_factory_subfactory_conflict memory.
    line = BudgetLineFactory.build(budget=budget, category=category, **overrides)
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return line


class TestGetOrCreateCategoryScoping:
    async def test_same_name_in_two_budgets_creates_two_rows(self, db):
        budget_a = await _make_budget(db)
        budget_b = await _make_budget(db)
        user = _valid_user()

        category_a = await get_or_create_category_service(
            db, user, budget_id=budget_a.id, category_name="Travel"
        )
        category_b = await get_or_create_category_service(
            db, user, budget_id=budget_b.id, category_name="Travel"
        )

        assert category_a.id != category_b.id
        assert category_a.budget_id == budget_a.id
        assert category_b.budget_id == budget_b.id

    async def test_same_name_in_one_budget_reuses_the_same_row(self, db):
        budget = await _make_budget(db)
        user = _valid_user()

        first = await get_or_create_category_service(
            db, user, budget_id=budget.id, category_name="Travel"
        )
        second = await get_or_create_category_service(
            db, user, budget_id=budget.id, category_name="Travel"
        )

        assert first.id == second.id
        count = (
            await db.execute(
                select(func.count()).select_from(
                    select(BudgetCategoryModel)
                    .where(BudgetCategoryModel.budget_id == budget.id)
                    .subquery()
                )
            )
        ).scalar()
        assert count == 1

    async def test_category_id_from_another_budget_is_rejected(self, db):
        budget_a = await _make_budget(db)
        budget_b = await _make_budget(db)
        user = _valid_user()
        other_budget_category = await get_or_create_category_service(
            db, user, budget_id=budget_a.id, category_name="Travel"
        )

        with pytest.raises(DomainError):
            await get_or_create_category_service(
                db, user, budget_id=budget_b.id, category_id=other_budget_category.id
            )


class TestGetOrCreateCategoriesByNamesScoping:
    async def test_repeated_names_in_one_budget_dedupe_to_one_row_each(self, db):
        budget = await _make_budget(db)
        user = _valid_user()

        result = await get_or_create_categories_by_names_service(
            db, user, budget_id=budget.id, category_names=["Travel", "Travel", "Personnel"]
        )

        assert set(result.keys()) == {"Travel", "Personnel"}
        count = (
            await db.execute(
                select(func.count()).select_from(
                    select(BudgetCategoryModel)
                    .where(BudgetCategoryModel.budget_id == budget.id)
                    .subquery()
                )
            )
        ).scalar()
        assert count == 2

    async def test_same_name_across_budgets_is_not_shared(self, db):
        budget_a = await _make_budget(db)
        budget_b = await _make_budget(db)
        user = _valid_user()

        result_a = await get_or_create_categories_by_names_service(
            db, user, budget_id=budget_a.id, category_names=["Personnel"]
        )
        result_b = await get_or_create_categories_by_names_service(
            db, user, budget_id=budget_b.id, category_names=["Personnel"]
        )

        assert result_a["Personnel"].id != result_b["Personnel"].id


class TestUpdateBudgetCategoryService:
    async def test_owner_can_rename_and_updated_by_is_set(self, db):
        budget = await _make_budget(db)
        owner = _valid_user()
        category = await get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )

        editor = _valid_user(user_id=str(uuid4()))
        updated = await update_budget_category_service(
            db, editor, category.id, {"name": "Transport", "code": "TRANSPORT"}
        )

        assert updated.name == "Transport"
        assert updated.code == "TRANSPORT"
        assert str(updated.updated_by) == editor["user_id"]

    async def test_rename_rejected_for_another_customers_budget(self, db):
        budget = await _make_budget(db, owner_id=OWNER_ID)
        owner = _valid_user(customer_id=OWNER_ID)
        category = await get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )

        stranger = _valid_user(customer_id=STRANGER_ID)
        with pytest.raises(DomainError):
            await update_budget_category_service(db, stranger, category.id, {"name": "Hijacked"})

    async def test_rename_rejected_once_budget_is_confirmed(self, db):
        budget = await _make_budget(db, status=BudgetStatus.confirmed)
        owner = _valid_user()
        category = await get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )

        with pytest.raises(DomainError):
            await update_budget_category_service(db, owner, category.id, {"name": "Transport"})

    async def test_rename_rejected_for_unknown_category_id(self, db):
        owner = _valid_user()
        with pytest.raises(DomainError):
            await update_budget_category_service(db, owner, uuid4(), {"name": "Hijacked"})


class TestDeleteBudgetCategoryService:
    async def test_owner_can_delete(self, db):
        budget = await _make_budget(db)
        owner = _valid_user()
        category = await get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )

        result = await delete_budget_category_service(db, owner, category.id)

        assert result is True
        remaining = (
            await db.execute(
                select(BudgetCategoryModel).where(BudgetCategoryModel.id == category.id)
            )
        ).scalar_one_or_none()
        assert remaining is None

    async def test_delete_nulls_out_category_id_on_referencing_lines(self, db):
        budget = await _make_budget(db)
        owner = _valid_user()
        category = await get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )
        line = await _make_budget_line(db, budget, category)
        assert line.category_id == category.id

        await delete_budget_category_service(db, owner, category.id)

        await db.refresh(line)
        assert line.category_id is None

    async def test_delete_rejected_for_another_customers_budget(self, db):
        budget = await _make_budget(db, owner_id=OWNER_ID)
        owner = _valid_user(customer_id=OWNER_ID)
        category = await get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )

        stranger = _valid_user(customer_id=STRANGER_ID)
        with pytest.raises(DomainError):
            await delete_budget_category_service(db, stranger, category.id)

    async def test_delete_rejected_once_budget_is_confirmed(self, db):
        budget = await _make_budget(db, status=BudgetStatus.confirmed)
        owner = _valid_user()
        category = await get_or_create_category_service(
            db, owner, budget_id=budget.id, category_name="Travel"
        )

        with pytest.raises(DomainError):
            await delete_budget_category_service(db, owner, category.id)

    async def test_delete_rejected_for_unknown_category_id(self, db):
        owner = _valid_user()
        with pytest.raises(DomainError):
            await delete_budget_category_service(db, owner, uuid4())
