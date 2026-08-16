"""
Tests for openspec/changes/superuser-cross-tenant-access, Group 1: closing
the unconditional `if valid_user["role"] == "superuser": <unscoped>` bypass
in budget/report services.

A superuser is scoped purely by `valid_user.get("customer_id")`, exactly
like a regular customer user (design.md Decision 7). With no active
impersonation session (no customer_id resolved on their token), every list
endpoint touched by that fix must return an empty result and every
single-resource endpoint must behave as not-found — never fall back to
"every customer's data". A regular customer's own access must stay
unaffected.
"""

import asyncio
from datetime import date
from uuid import uuid4

import pytest

from app.core.exceptions import DomainError, PermissionDenied
from app.models.budget import BudgetModel
from app.models.report import ReportModel
from app.schemas.budget_schema import BudgetStatus
from app.schemas import BudgetLineCreate
from app.services.budget_services import (
    get_budget_service,
    get_viewable_budget_service,
    list_budget_service,
)
from app.services.budget_line_services import (
    create_budget_line_service,
    get_budget_line_by_id_service,
    get_budget_lines_service,
)
from app.services.report_services import (
    get_report_service,
    list_all_reports_service,
    list_reports_service,
)
from tests.factories.user import make_valid_user

OWNER_ID = str(uuid4())


def _superuser_no_session():
    user = make_valid_user(role="superuser")
    user["customer_id"] = None
    return user


def _owner_user():
    return make_valid_user(customer_id=OWNER_ID)


def _make_budget(db, status=BudgetStatus.confirmed):
    budget = BudgetModel(
        name="Test Budget",
        owner_id=OWNER_ID,
        status=status,
        start_date=None,
        duration_months=12,
        local_currency="GBP",
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def _make_budget_line(db, budget_id):
    from app.models.budget import BudgetLineModel

    line = BudgetLineModel(budget_id=budget_id, description="Coordinator salary", amount=500.0)
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def _make_report(db, budget_id):
    report = ReportModel(
        budget_id=budget_id,
        name="Interim report",
        status="draft",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


class TestListEndpointsReturnEmptyWithNoSession:
    def test_list_budget_service(self, db):
        _make_budget(db)
        result = asyncio.run(list_budget_service(_superuser_no_session(), db))
        assert result == []

    def test_list_budget_service_still_works_for_owner(self, db):
        _make_budget(db)
        result = asyncio.run(list_budget_service(_owner_user(), db))
        assert len(result) == 1

    def test_get_budget_lines_service_list_branch(self, db):
        budget = _make_budget(db)
        _make_budget_line(db, budget.id)
        result = get_budget_lines_service(db, _superuser_no_session())
        assert result == []

    def test_get_budget_lines_service_list_branch_still_works_for_owner(self, db):
        budget = _make_budget(db)
        _make_budget_line(db, budget.id)
        result = get_budget_lines_service(db, _owner_user())
        assert len(result) == 1

    def test_list_all_reports_service(self, db):
        budget = _make_budget(db)
        _make_report(db, budget.id)
        result = list_all_reports_service(db, _superuser_no_session())
        assert result == []

    def test_list_all_reports_service_still_works_for_owner(self, db):
        budget = _make_budget(db)
        _make_report(db, budget.id)
        result = list_all_reports_service(db, _owner_user())
        assert len(result) == 1


class TestSingleResourceEndpointsNotFoundWithNoSession:
    def test_get_budget_service(self, db):
        budget = _make_budget(db)
        with pytest.raises(DomainError):
            asyncio.run(get_budget_service(budget.id, _superuser_no_session(), db))

    def test_get_budget_service_still_works_for_owner(self, db):
        budget = _make_budget(db)
        result = asyncio.run(get_budget_service(budget.id, _owner_user(), db))
        assert result.id == budget.id

    def test_get_viewable_budget_service(self, db):
        budget = _make_budget(db)
        with pytest.raises(DomainError):
            asyncio.run(get_viewable_budget_service(budget.id, _superuser_no_session(), db))

    def test_get_viewable_budget_service_still_works_for_owner(self, db):
        budget = _make_budget(db)
        result = asyncio.run(get_viewable_budget_service(budget.id, _owner_user(), db))
        assert result.id == budget.id

    def test_get_budget_lines_service_single_budget_branch(self, db):
        budget = _make_budget(db)
        with pytest.raises(DomainError):
            get_budget_lines_service(db, _superuser_no_session(), budget_id=budget.id)

    def test_get_budget_lines_service_single_budget_branch_still_works_for_owner(self, db):
        budget = _make_budget(db)
        _make_budget_line(db, budget.id)
        result = get_budget_lines_service(db, _owner_user(), budget_id=budget.id)
        assert len(result) == 1

    def test_get_budget_line_by_id_service(self, db):
        budget = _make_budget(db)
        line = _make_budget_line(db, budget.id)
        with pytest.raises(PermissionDenied):
            get_budget_line_by_id_service(db, _superuser_no_session(), line.id)

    def test_get_budget_line_by_id_service_still_works_for_owner(self, db):
        budget = _make_budget(db)
        line = _make_budget_line(db, budget.id)
        result = get_budget_line_by_id_service(db, _owner_user(), line.id)
        assert result.id == line.id

    def test_create_budget_line_service(self, db):
        budget = _make_budget(db)
        payload = BudgetLineCreate(
            budget_id=budget.id, description="Bogus line", amount=100.0, category_name="Personnel"
        )
        with pytest.raises(DomainError):
            create_budget_line_service(db, _superuser_no_session(), payload)

    def test_get_report_service(self, db):
        budget = _make_budget(db)
        report = _make_report(db, budget.id)
        with pytest.raises(DomainError):
            get_report_service(db, _superuser_no_session(), report.id)

    def test_get_report_service_still_works_for_owner(self, db):
        budget = _make_budget(db)
        report = _make_report(db, budget.id)
        result = get_report_service(db, _owner_user(), report.id)
        assert result.id == report.id

    def test_list_reports_service(self, db):
        budget = _make_budget(db)
        _make_report(db, budget.id)
        with pytest.raises(DomainError):
            list_reports_service(db, _superuser_no_session(), budget.id)

    def test_list_reports_service_still_works_for_owner(self, db):
        budget = _make_budget(db)
        _make_report(db, budget.id)
        result = list_reports_service(db, _owner_user(), budget.id)
        assert len(result) == 1
