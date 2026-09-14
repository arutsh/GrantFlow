"""A superuser with no customer_id (no active impersonation session) gets an
empty list / not-found, never every customer's data (design.md Decision 7)."""

from datetime import date
from uuid import uuid4

import pytest

from app.core.exceptions import DomainError, PermissionDenied
from app.models.budget import BudgetModel, BudgetLineModel
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
from tests.factories.user import ValidUserFactory

OWNER_ID = str(uuid4())


def _superuser_no_session():
    return ValidUserFactory(role="superuser", customer_id=None)


def _owner_user():
    return ValidUserFactory(customer_id=OWNER_ID)


async def _make_budget(db, status=BudgetStatus.confirmed):
    budget = BudgetModel(
        name="Test Budget",
        owner_id=OWNER_ID,
        status=status,
        start_date=None,
        duration_months=12,
        local_currency="GBP",
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


async def _make_budget_line(db, budget_id):
    line = BudgetLineModel(budget_id=budget_id, description="Coordinator salary", amount=500.0)
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return line


async def _make_report(db, budget_id):
    report = ReportModel(
        budget_id=budget_id,
        name="Interim report",
        status="draft",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@pytest.mark.anyio
class TestListEndpointsReturnEmptyWithNoSession:
    async def test_list_budget_service(self, db):
        await _make_budget(db)
        result = await list_budget_service(_superuser_no_session(), db)
        assert result == []

    async def test_list_budget_service_still_works_for_owner(self, db):
        await _make_budget(db)
        result = await list_budget_service(_owner_user(), db)
        assert len(result) == 1

    async def test_get_budget_lines_service_list_branch(self, db):
        budget = await _make_budget(db)
        await _make_budget_line(db, budget.id)
        result = await get_budget_lines_service(db, _superuser_no_session())
        assert result == []

    async def test_get_budget_lines_service_list_branch_still_works_for_owner(self, db):
        budget = await _make_budget(db)
        await _make_budget_line(db, budget.id)
        result = await get_budget_lines_service(db, _owner_user())
        assert len(result) == 1

    async def test_list_all_reports_service(self, db):
        budget = await _make_budget(db)
        await _make_report(db, budget.id)
        result = await list_all_reports_service(db, _superuser_no_session())
        assert result == []

    async def test_list_all_reports_service_still_works_for_owner(self, db):
        budget = await _make_budget(db)
        await _make_report(db, budget.id)
        result = await list_all_reports_service(db, _owner_user())
        assert len(result) == 1


@pytest.mark.anyio
class TestSingleResourceEndpointsNotFoundWithNoSession:
    async def test_get_budget_service(self, db):
        budget = await _make_budget(db)
        with pytest.raises(DomainError):
            await get_budget_service(budget.id, _superuser_no_session(), db)

    async def test_get_budget_service_still_works_for_owner(self, db):
        budget = await _make_budget(db)
        result = await get_budget_service(budget.id, _owner_user(), db)
        assert result.id == budget.id

    async def test_get_viewable_budget_service(self, db):
        budget = await _make_budget(db)
        with pytest.raises(DomainError):
            await get_viewable_budget_service(budget.id, _superuser_no_session(), db)

    async def test_get_viewable_budget_service_still_works_for_owner(self, db):
        budget = await _make_budget(db)
        result = await get_viewable_budget_service(budget.id, _owner_user(), db)
        assert result.id == budget.id

    async def test_get_budget_lines_service_single_budget_branch(self, db):
        budget = await _make_budget(db)
        with pytest.raises(DomainError):
            await get_budget_lines_service(db, _superuser_no_session(), budget_id=budget.id)

    async def test_get_budget_lines_service_single_budget_branch_still_works_for_owner(self, db):
        budget = await _make_budget(db)
        await _make_budget_line(db, budget.id)
        result = await get_budget_lines_service(db, _owner_user(), budget_id=budget.id)
        assert len(result) == 1

    async def test_get_budget_line_by_id_service(self, db):
        budget = await _make_budget(db)
        line = await _make_budget_line(db, budget.id)
        with pytest.raises(PermissionDenied):
            await get_budget_line_by_id_service(db, _superuser_no_session(), line.id)

    async def test_get_budget_line_by_id_service_still_works_for_owner(self, db):
        budget = await _make_budget(db)
        line = await _make_budget_line(db, budget.id)
        result = await get_budget_line_by_id_service(db, _owner_user(), line.id)
        assert result.id == line.id

    async def test_create_budget_line_service(self, db):
        budget = await _make_budget(db)
        payload = BudgetLineCreate(
            budget_id=budget.id, description="Bogus line", amount=100.0, category_name="Personnel"
        )
        with pytest.raises(DomainError):
            await create_budget_line_service(db, _superuser_no_session(), payload)

    async def test_get_report_service(self, db):
        budget = await _make_budget(db)
        report = await _make_report(db, budget.id)
        with pytest.raises(DomainError):
            await get_report_service(db, _superuser_no_session(), report.id)

    async def test_get_report_service_still_works_for_owner(self, db):
        budget = await _make_budget(db)
        report = await _make_report(db, budget.id)
        result = await get_report_service(db, _owner_user(), report.id)
        assert result.id == report.id

    async def test_list_reports_service(self, db):
        budget = await _make_budget(db)
        await _make_report(db, budget.id)
        with pytest.raises(DomainError):
            await list_reports_service(db, _superuser_no_session(), budget.id)

    async def test_list_reports_service_still_works_for_owner(self, db):
        budget = await _make_budget(db)
        await _make_report(db, budget.id)
        result = await list_reports_service(db, _owner_user(), budget.id)
        assert len(result) == 1
