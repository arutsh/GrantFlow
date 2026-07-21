"""
Tests for Budget.total_amount staying in sync with its budget lines.

Recalculation happens via app.crud.budget_crud.recalculate_budget_total,
called from create/update/delete_budget_line_service. These tests mock the
crud layer (matching this service's existing test convention — no real DB
session) and assert recalculation is triggered with the correct budget_id.
"""

from unittest.mock import patch
from uuid import uuid4

from tests.factories.user import make_valid_user
from tests.factories.budget import BudgetFactory, BudgetLineFactory
from app.schemas import BudgetLineCreate, BudgetLineUpdate
from app.services.budget_line_services import (
    create_budget_line_service,
    update_budget_line_service,
    delete_budget_line_service,
)

USER_ID = str(uuid4())
CUSTOMER_ID = str(uuid4())
DB = object()  # session is never actually used — every crud call is mocked


def _valid_user():
    return make_valid_user(user_id=USER_ID, customer_id=CUSTOMER_ID)


class TestTotalAmountRecalculation:
    def test_create_budget_line_recalculates_total(self):
        budget = BudgetFactory.build(id=uuid4(), owner_id=CUSTOMER_ID)
        line = BudgetLineFactory.build(budget_id=budget.id, created_by=USER_ID)
        payload = BudgetLineCreate(
            budget_id=budget.id,
            description="Coordinator salary",
            amount=500.0,
            category_name="Personnel",
        )

        with (
            patch("app.services.budget_line_services.get_budget", return_value=budget),
            patch(
                "app.services.budget_line_services.get_or_create_category_service",
                return_value=line.category,
            ),
            patch("app.services.budget_line_services.create_budget_line", return_value=line),
            patch("app.services.budget_line_services.recalculate_budget_total") as mock_recalc,
        ):
            result = create_budget_line_service(DB, _valid_user(), payload)

        assert result is line
        mock_recalc.assert_called_once_with(DB, budget.id)

    def test_update_budget_line_recalculates_total(self):
        budget = BudgetFactory.build(id=uuid4(), owner_id=CUSTOMER_ID)
        existing_line = BudgetLineFactory.build(budget_id=budget.id, amount=500.0)
        updated_line = BudgetLineFactory.build(budget_id=budget.id, amount=300.0)
        payload = BudgetLineUpdate(budget_id=budget.id, amount=300.0)

        with (
            patch(
                "app.services.budget_line_services.get_budget_line_by_id_service",
                return_value=existing_line,
            ),
            patch(
                "app.services.budget_line_services.update_budget_line",
                return_value=updated_line,
            ),
            patch("app.services.budget_line_services.recalculate_budget_total") as mock_recalc,
        ):
            result = update_budget_line_service(DB, _valid_user(), existing_line.id, payload)

        assert result is updated_line
        mock_recalc.assert_called_once_with(DB, budget.id)

    def test_delete_budget_line_recalculates_total(self):
        budget_id = uuid4()
        existing_line = BudgetLineFactory.build(budget_id=budget_id)

        with (
            patch(
                "app.services.budget_line_services.get_budget_line_by_id_service",
                return_value=existing_line,
            ),
            patch("app.services.budget_line_services.delete_budget_line", return_value=True),
            patch("app.services.budget_line_services.recalculate_budget_total") as mock_recalc,
        ):
            result = delete_budget_line_service(existing_line.id, _valid_user(), DB)

        assert result is True
        mock_recalc.assert_called_once_with(DB, budget_id)

    def test_delete_budget_line_not_found_skips_recalculation(self):
        with (
            patch(
                "app.services.budget_line_services.get_budget_line_by_id_service",
                return_value=None,
            ),
            patch("app.services.budget_line_services.recalculate_budget_total") as mock_recalc,
        ):
            result = delete_budget_line_service(uuid4(), _valid_user(), DB)

        assert result is False
        mock_recalc.assert_not_called()


class TestRecalculateBudgetTotalCrud:
    """Direct coverage of the SQL aggregation itself, against a real sqlite session."""

    def test_sums_line_amounts_and_ignores_null_amounts(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models.base import Base
        from app.models.budget import BudgetModel, BudgetLineModel
        from app.crud.budget_crud import recalculate_budget_total

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[BudgetModel.__table__, BudgetLineModel.__table__])
        session = sessionmaker(bind=engine)()

        budget = BudgetModel(name="Test Budget", owner_id=uuid4())
        session.add(budget)
        session.commit()

        session.add_all(
            [
                BudgetLineModel(budget_id=budget.id, amount=500.0),
                BudgetLineModel(budget_id=budget.id, amount=300.0),
                BudgetLineModel(budget_id=budget.id, amount=None),
            ]
        )
        session.commit()

        updated = recalculate_budget_total(session, budget.id)

        assert updated.total_amount == 800.0

    def test_returns_zero_when_budget_has_no_lines(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models.base import Base
        from app.models.budget import BudgetModel, BudgetLineModel
        from app.crud.budget_crud import recalculate_budget_total

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[BudgetModel.__table__, BudgetLineModel.__table__])
        session = sessionmaker(bind=engine)()

        budget = BudgetModel(name="Empty Budget", owner_id=uuid4())
        session.add(budget)
        session.commit()

        updated = recalculate_budget_total(session, budget.id)

        assert updated.total_amount == 0

    def test_returns_none_for_unknown_budget(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models.base import Base
        from app.models.budget import BudgetModel, BudgetLineModel
        from app.crud.budget_crud import recalculate_budget_total

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[BudgetModel.__table__, BudgetLineModel.__table__])
        session = sessionmaker(bind=engine)()

        assert recalculate_budget_total(session, uuid4()) is None
