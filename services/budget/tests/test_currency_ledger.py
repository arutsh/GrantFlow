"""
Tests for ticket #148: currency ledger FIFO allocation, and retroactive
backfill on a later conversion (design.md's 2026-07-26 amended note).

Same real-sqlite-session convention as test_report_line_routes.py.
"""

from datetime import date, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.budget import BudgetModel, BudgetLineModel, BudgetCategoryModel
from app.models.report import ReportModel, ReportLineModel, AttachmentModel
from app.models.currency_ledger import (
    FundingReceiptModel,
    CurrencyConversionModel,
    ReportLineConversionAllocationModel,
)
from app.crud.report_line_crud import list_report_lines
from app.schemas.budget_schema import BudgetStatus
from app.schemas.report_schema import ReportStatus
from app.schemas.report_line_schema import ReportLineCreate, ReportLineUpdate
from app.schemas.currency_ledger_schema import FundingReceiptCreate, CurrencyConversionCreate
from app.services.report_line_services import (
    create_report_line_service,
    update_report_line_service,
)
from app.services.currency_ledger_services import (
    record_receipt_service,
    record_conversion_service,
    get_ledger_balance_service,
)
from tests.factories.user import make_valid_user

OWNER_ID = str(uuid4())


def _valid_user(customer_id=OWNER_ID):
    return make_valid_user(customer_id=customer_id)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            BudgetModel.__table__,
            BudgetLineModel.__table__,
            BudgetCategoryModel.__table__,
            ReportModel.__table__,
            ReportLineModel.__table__,
            AttachmentModel.__table__,
            FundingReceiptModel.__table__,
            CurrencyConversionModel.__table__,
            ReportLineConversionAllocationModel.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def _make_budget(db, owner_id=OWNER_ID, local_currency="USD", actual_currency="EUR"):
    budget = BudgetModel(
        name="Test Budget",
        owner_id=owner_id,
        status=BudgetStatus.confirmed,
        start_date=date(2026, 1, 1),
        duration_months=12,
        local_currency=local_currency,
        actual_currency=actual_currency,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def _make_budget_line(db, budget_id, amount=1000.0):
    line = BudgetLineModel(budget_id=budget_id, description="Admin costs", amount=amount)
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def _make_report(db, budget_id, status=ReportStatus.draft):
    report = ReportModel(
        budget_id=budget_id,
        name="Report",
        status=status,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _make_expense(db, report, budget_line, amount):
    return create_report_line_service(
        db,
        _valid_user(),
        ReportLineCreate(
            report_id=report.id,
            budget_line_id=budget_line.id,
            description="Expense",
            amount=amount,
            expense_date=date(2026, 6, 15),
        ),
    )


def _record_receipt(db, budget, amount, received_at):
    return record_receipt_service(
        db,
        _valid_user(),
        FundingReceiptCreate(budget_id=budget.id, amount=amount, received_at=received_at),
    )


def _record_conversion(db, budget, donor_amount, local_amount, converted_at):
    return record_conversion_service(
        db,
        _valid_user(),
        CurrencyConversionCreate(
            budget_id=budget.id,
            donor_amount=donor_amount,
            local_amount=local_amount,
            converted_at=converted_at,
        ),
    )


def _allocations_for(db, report_line_id):
    return (
        db.query(ReportLineConversionAllocationModel).filter_by(report_line_id=report_line_id).all()
    )


class TestFifoAllocation:
    def test_single_lot_fully_covers_expense(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        _record_conversion(
            db, budget, donor_amount=500.0, local_amount=550.0, converted_at=date(2026, 1, 2)
        )

        expense = _make_expense(db, report, budget_line, amount=300.0)

        allocations = _allocations_for(db, expense.id)
        assert len(allocations) == 1
        assert allocations[0].amount_allocated == 300.0

    def test_expense_splits_across_two_lots(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        _record_conversion(
            db, budget, donor_amount=200.0, local_amount=220.0, converted_at=date(2026, 1, 2)
        )
        _record_conversion(
            db, budget, donor_amount=300.0, local_amount=330.0, converted_at=date(2026, 1, 5)
        )

        expense = _make_expense(db, report, budget_line, amount=400.0)

        allocations = sorted(_allocations_for(db, expense.id), key=lambda a: a.amount_allocated)
        assert [a.amount_allocated for a in allocations] == [180.0, 220.0]


class TestOverspendAndBackfill:
    def test_overspend_leaves_remainder_unsatisfied(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        _record_conversion(
            db, budget, donor_amount=500.0, local_amount=550.0, converted_at=date(2026, 1, 2)
        )

        expense = _make_expense(db, report, budget_line, amount=800.0)

        allocations = _allocations_for(db, expense.id)
        assert len(allocations) == 1
        assert allocations[0].amount_allocated == 550.0

        balance = get_ledger_balance_service(db, _valid_user(), budget.id)
        assert balance.local_balance == pytest.approx(550.0 - 800.0)

    def test_next_conversion_backfills_the_overspent_expense(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        _record_conversion(
            db, budget, donor_amount=500.0, local_amount=550.0, converted_at=date(2026, 1, 2)
        )
        expense = _make_expense(db, report, budget_line, amount=800.0)

        second_conversion = _record_conversion(
            db, budget, donor_amount=500.0, local_amount=560.0, converted_at=date(2026, 1, 6)
        )

        allocations = _allocations_for(db, expense.id)
        assert len(allocations) == 2
        assert sum(a.amount_allocated for a in allocations) == pytest.approx(800.0)

        backfilled = [a for a in allocations if a.conversion_id == second_conversion.id]
        assert len(backfilled) == 1
        assert backfilled[0].amount_allocated == pytest.approx(250.0)

        balance = get_ledger_balance_service(db, _valid_user(), budget.id)
        assert balance.local_balance == pytest.approx(310.0)

    def test_oldest_unsatisfied_expense_backfilled_first(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        _record_conversion(
            db, budget, donor_amount=100.0, local_amount=100.0, converted_at=date(2026, 1, 1)
        )
        # 100 covered by the existing lot, 200 left unsatisfied.
        first_expense = _make_expense(db, report, budget_line, amount=300.0)
        # No lots left at all — fully unsatisfied.
        second_expense = _make_expense(db, report, budget_line, amount=150.0)
        # SQLite's func.now() default only has second resolution, so two
        # inserts in the same test tick can otherwise collide on created_at
        # (Postgres's microsecond resolution makes this a non-issue in
        # practice) — stagger them explicitly so "oldest first" is
        # unambiguous for this assertion.
        first_expense.created_at = datetime(2026, 1, 3, 0, 0, 0)
        second_expense.created_at = datetime(2026, 1, 3, 0, 0, 1)
        db.commit()

        new_conversion = _record_conversion(
            db, budget, donor_amount=180.0, local_amount=200.0, converted_at=date(2026, 1, 10)
        )

        first_allocations = _allocations_for(db, first_expense.id)
        second_allocations = _allocations_for(db, second_expense.id)
        assert sum(a.amount_allocated for a in first_allocations) == pytest.approx(300.0)
        assert sum(a.amount_allocated for a in second_allocations) == pytest.approx(0.0)
        assert any(a.conversion_id == new_conversion.id for a in first_allocations)


class TestPerCurrencyBalance:
    def test_balance_reported_separately_per_currency(self, db):
        budget = _make_budget(db, local_currency="USD", actual_currency="EUR")
        _record_receipt(db, budget, amount=1000.0, received_at=date(2026, 1, 1))
        _record_conversion(
            db, budget, donor_amount=500.0, local_amount=550.0, converted_at=date(2026, 1, 2)
        )

        balance = get_ledger_balance_service(db, _valid_user(), budget.id)

        assert balance.actual_currency == "EUR"
        assert balance.donor_balance == pytest.approx(1000.0 - 500.0)
        assert balance.local_currency == "USD"
        assert balance.local_balance == pytest.approx(550.0)


class TestReallocationOnEdit:
    def test_amount_increase_allocates_the_additional_amount(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        _record_conversion(
            db, budget, donor_amount=500.0, local_amount=550.0, converted_at=date(2026, 1, 2)
        )
        expense = _make_expense(db, report, budget_line, amount=300.0)

        update_report_line_service(
            db, _valid_user(), expense.id, ReportLineUpdate(report_id=report.id, amount=500.0)
        )

        allocations = _allocations_for(db, expense.id)
        assert sum(a.amount_allocated for a in allocations) == pytest.approx(500.0)

    def test_amount_decrease_frees_capacity_for_the_next_expense(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        _record_conversion(
            db, budget, donor_amount=500.0, local_amount=550.0, converted_at=date(2026, 1, 2)
        )
        # Fully consumes the only lot.
        expense = _make_expense(db, report, budget_line, amount=550.0)

        update_report_line_service(
            db, _valid_user(), expense.id, ReportLineUpdate(report_id=report.id, amount=200.0)
        )
        assert sum(a.amount_allocated for a in _allocations_for(db, expense.id)) == pytest.approx(
            200.0
        )

        # The 350 the edit freed up is now available to a new expense.
        second_expense = _make_expense(db, report, budget_line, amount=350.0)
        assert sum(
            a.amount_allocated for a in _allocations_for(db, second_expense.id)
        ) == pytest.approx(350.0)


class TestCompensatingRollback:
    def test_create_report_line_rolled_back_when_allocation_fails(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)

        with patch(
            "app.services.report_line_services.allocate_fifo_service",
            side_effect=RuntimeError("simulated allocation failure"),
        ):
            with pytest.raises(RuntimeError):
                create_report_line_service(
                    db,
                    _valid_user(),
                    ReportLineCreate(
                        report_id=report.id,
                        budget_line_id=budget_line.id,
                        description="Expense",
                        amount=300.0,
                        expense_date=date(2026, 6, 15),
                    ),
                )

        assert list_report_lines(db, report_id=report.id) == []

    def test_update_report_line_amount_reverted_when_reallocation_fails(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        _record_conversion(
            db, budget, donor_amount=500.0, local_amount=550.0, converted_at=date(2026, 1, 2)
        )
        expense = _make_expense(db, report, budget_line, amount=300.0)

        with patch(
            "app.services.report_line_services.allocate_fifo_service",
            side_effect=[RuntimeError("simulated allocation failure"), None],
        ):
            with pytest.raises(RuntimeError):
                update_report_line_service(
                    db,
                    _valid_user(),
                    expense.id,
                    ReportLineUpdate(report_id=report.id, amount=999.0),
                )

        db.refresh(expense)
        assert expense.amount == 300.0
