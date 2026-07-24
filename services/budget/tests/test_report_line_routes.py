"""
Tests for ticket #146: report line create/update/delete against the
draft-only lock and the same-budget cross-check on budget_line_id.

Same real-sqlite-session convention as test_report_routes.py.
"""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import DomainError, PermissionDenied
from app.models.base import Base
from app.models.budget import BudgetModel, BudgetLineModel, BudgetCategoryModel
from app.models.report import ReportModel, ReportLineModel
from app.schemas.budget_schema import BudgetStatus
from app.schemas.report_schema import ReportStatus
from app.schemas.report_line_schema import ReportLineCreate, ReportLineUpdate
from app.services.report_line_services import (
    create_report_line_service,
    get_report_line_by_id_service,
    list_report_lines_service,
    update_report_line_service,
    delete_report_line_service,
)
from tests.factories.user import make_valid_user

OWNER_ID = str(uuid4())
FUNDER_ID = str(uuid4())
STRANGER_ID = str(uuid4())


def _valid_user(customer_id):
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
        ],
    )
    return sessionmaker(bind=engine)()


def _make_budget(db, owner_id=OWNER_ID, funding_customer_id=None):
    budget = BudgetModel(
        name="Test Budget",
        owner_id=owner_id,
        funding_customer_id=funding_customer_id,
        status=BudgetStatus.confirmed,
        start_date=date(2026, 1, 1),
        duration_months=12,
        local_currency="GBP",
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


class TestCreateReportLine:
    def test_create_against_matching_budget_line(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        payload = ReportLineCreate(
            report_id=report.id,
            budget_line_id=budget_line.id,
            description="Receipt #1",
            amount=250.0,
        )

        result = create_report_line_service(db, _valid_user(OWNER_ID), payload)

        assert result.report_id == report.id
        assert result.budget_line_id == budget_line.id

    def test_rejected_for_cross_budget_budget_line(self, db):
        budget = _make_budget(db)
        other_budget = _make_budget(db, owner_id=OWNER_ID)
        other_budget_line = _make_budget_line(db, other_budget.id)
        report = _make_report(db, budget.id)
        payload = ReportLineCreate(
            report_id=report.id,
            budget_line_id=other_budget_line.id,
            description="Wrong budget",
            amount=100.0,
        )

        with pytest.raises(DomainError):
            create_report_line_service(db, _valid_user(OWNER_ID), payload)

    def test_rejected_on_non_draft_report(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id, status=ReportStatus.submitted)
        payload = ReportLineCreate(
            report_id=report.id,
            budget_line_id=budget_line.id,
            description="Too late",
            amount=100.0,
        )

        with pytest.raises(DomainError):
            create_report_line_service(db, _valid_user(OWNER_ID), payload)

    def test_funder_cannot_create_report_line(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        payload = ReportLineCreate(
            report_id=report.id,
            budget_line_id=budget_line.id,
            description="Not funder's job",
            amount=100.0,
        )

        with pytest.raises(PermissionDenied):
            create_report_line_service(db, _valid_user(FUNDER_ID), payload)

    def test_multiple_lines_against_same_budget_line(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        for i in range(2):
            payload = ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description=f"Receipt #{i}",
                amount=100.0,
            )
            create_report_line_service(db, _valid_user(OWNER_ID), payload)

        lines = list_report_lines_service(db, _valid_user(OWNER_ID), report.id)
        assert len(lines) == 2


class TestReportLineAccess:
    def test_owner_and_funder_can_view(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        line = create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
            ),
        )

        assert get_report_line_by_id_service(db, _valid_user(OWNER_ID), line.id).id == line.id
        assert get_report_line_by_id_service(db, _valid_user(FUNDER_ID), line.id).id == line.id

    def test_stranger_cannot_view(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        line = create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
            ),
        )

        with pytest.raises(DomainError):
            get_report_line_by_id_service(db, _valid_user(STRANGER_ID), line.id)


class TestUpdateDeleteLock:
    def test_update_rejected_on_non_draft_report(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        line = create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
            ),
        )
        report.status = ReportStatus.submitted
        db.commit()

        with pytest.raises(DomainError):
            update_report_line_service(
                db,
                _valid_user(OWNER_ID),
                line.id,
                ReportLineUpdate(report_id=report.id, amount=99.0),
            )

    def test_delete_rejected_on_non_draft_report(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        line = create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
            ),
        )
        report.status = ReportStatus.approved
        db.commit()

        with pytest.raises(DomainError):
            delete_report_line_service(db, _valid_user(OWNER_ID), line.id)

    def test_update_allowed_on_draft_report(self, db):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        line = create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
            ),
        )

        updated = update_report_line_service(
            db, _valid_user(OWNER_ID), line.id, ReportLineUpdate(report_id=report.id, amount=99.0)
        )

        assert updated.amount == 99.0
