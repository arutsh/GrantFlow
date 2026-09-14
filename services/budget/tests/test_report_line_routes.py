"""
Tests for ticket #146: report line create/update/delete against the
draft-only lock and the same-budget cross-check on budget_line_id.

Same real-sqlite-session convention as test_report_routes.py.
"""

from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.exceptions import DomainError, PermissionDenied
from app.models.budget import BudgetModel, BudgetLineModel
from app.models.report import ReportModel, ReportLineModel, AttachmentModel
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
def storage():
    with patch("app.services.report_line_services.storage_client") as mock_storage:
        yield mock_storage


async def _make_budget(db, owner_id=OWNER_ID, funding_customer_id=None):
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
    await db.commit()
    await db.refresh(budget)
    return budget


async def _make_budget_line(db, budget_id, amount=1000.0):
    line = BudgetLineModel(budget_id=budget_id, description="Admin costs", amount=amount)
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return line


async def _make_report(db, budget_id, status=ReportStatus.draft):
    report = ReportModel(
        budget_id=budget_id,
        name="Report",
        status=status,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@pytest.mark.anyio
class TestCreateReportLine:
    async def test_create_against_matching_budget_line(self, db):
        budget = await _make_budget(db)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        payload = ReportLineCreate(
            report_id=report.id,
            budget_line_id=budget_line.id,
            description="Receipt #1",
            amount=250.0,
            expense_date=date(2026, 6, 15),
        )

        result = await create_report_line_service(db, _valid_user(OWNER_ID), payload)

        assert result.report_id == report.id
        assert result.budget_line_id == budget_line.id

    async def test_rejected_for_cross_budget_budget_line(self, db):
        budget = await _make_budget(db)
        other_budget = await _make_budget(db, owner_id=OWNER_ID)
        other_budget_line = await _make_budget_line(db, other_budget.id)
        report = await _make_report(db, budget.id)
        payload = ReportLineCreate(
            report_id=report.id,
            budget_line_id=other_budget_line.id,
            description="Wrong budget",
            amount=100.0,
            expense_date=date(2026, 6, 15),
        )

        with pytest.raises(DomainError):
            await create_report_line_service(db, _valid_user(OWNER_ID), payload)

    async def test_rejected_on_non_draft_report(self, db):
        budget = await _make_budget(db)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id, status=ReportStatus.submitted)
        payload = ReportLineCreate(
            report_id=report.id,
            budget_line_id=budget_line.id,
            description="Too late",
            amount=100.0,
            expense_date=date(2026, 6, 15),
        )

        with pytest.raises(DomainError):
            await create_report_line_service(db, _valid_user(OWNER_ID), payload)

    async def test_funder_cannot_create_report_line(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        payload = ReportLineCreate(
            report_id=report.id,
            budget_line_id=budget_line.id,
            description="Not funder's job",
            amount=100.0,
            expense_date=date(2026, 6, 15),
        )

        with pytest.raises(PermissionDenied):
            await create_report_line_service(db, _valid_user(FUNDER_ID), payload)

    async def test_multiple_lines_against_same_budget_line(self, db):
        budget = await _make_budget(db)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        for i in range(2):
            payload = ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description=f"Receipt #{i}",
                amount=100.0,
                expense_date=date(2026, 6, 15),
            )
            await create_report_line_service(db, _valid_user(OWNER_ID), payload)

        lines = await list_report_lines_service(db, _valid_user(OWNER_ID), report.id)
        assert len(lines) == 2


@pytest.mark.anyio
class TestExpenseDateValidation:
    """expense_date must fall within the report's own period — the real-world
    date an expense happened, not when the row was written (created_at)."""

    async def test_rejected_before_report_period_start(self, db):
        budget = await _make_budget(db)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        payload = ReportLineCreate(
            report_id=report.id,
            budget_line_id=budget_line.id,
            description="Too early",
            amount=100.0,
            expense_date=date(2025, 12, 31),
        )

        with pytest.raises(DomainError):
            await create_report_line_service(db, _valid_user(OWNER_ID), payload)

    async def test_rejected_after_report_period_end(self, db):
        budget = await _make_budget(db)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        payload = ReportLineCreate(
            report_id=report.id,
            budget_line_id=budget_line.id,
            description="Too late",
            amount=100.0,
            expense_date=date(2027, 1, 1),
        )

        with pytest.raises(DomainError):
            await create_report_line_service(db, _valid_user(OWNER_ID), payload)

    async def test_accepted_on_period_boundaries(self, db):
        budget = await _make_budget(db)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)

        start_line = await create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="On period start",
                amount=10.0,
                expense_date=report.period_start,
            ),
        )
        end_line = await create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="On period end",
                amount=10.0,
                expense_date=report.period_end,
            ),
        )

        assert start_line.expense_date == report.period_start
        assert end_line.expense_date == report.period_end

    async def test_update_rejected_when_expense_date_moved_outside_period(self, db):
        budget = await _make_budget(db)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        line = await create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
                expense_date=date(2026, 6, 15),
            ),
        )

        with pytest.raises(DomainError):
            await update_report_line_service(
                db,
                _valid_user(OWNER_ID),
                line.id,
                ReportLineUpdate(report_id=report.id, expense_date=date(2027, 1, 1)),
            )

    async def test_update_allowed_within_period(self, db):
        budget = await _make_budget(db)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        line = await create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
                expense_date=date(2026, 6, 15),
            ),
        )

        updated = await update_report_line_service(
            db,
            _valid_user(OWNER_ID),
            line.id,
            ReportLineUpdate(report_id=report.id, expense_date=date(2026, 7, 1)),
        )

        assert updated.expense_date == date(2026, 7, 1)


@pytest.mark.anyio
class TestReportLineAccess:
    async def test_owner_and_funder_can_view(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        line = await create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
                expense_date=date(2026, 6, 15),
            ),
        )

        owner_result = await get_report_line_by_id_service(db, _valid_user(OWNER_ID), line.id)
        funder_result = await get_report_line_by_id_service(db, _valid_user(FUNDER_ID), line.id)
        assert owner_result.id == line.id
        assert funder_result.id == line.id

    async def test_stranger_cannot_view(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        line = await create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
                expense_date=date(2026, 6, 15),
            ),
        )

        with pytest.raises(DomainError):
            await get_report_line_by_id_service(db, _valid_user(STRANGER_ID), line.id)


@pytest.mark.anyio
class TestUpdateDeleteLock:
    async def test_update_rejected_on_non_draft_report(self, db):
        budget = await _make_budget(db)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        line = await create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
                expense_date=date(2026, 6, 15),
            ),
        )
        report.status = ReportStatus.submitted
        await db.commit()

        with pytest.raises(DomainError):
            await update_report_line_service(
                db,
                _valid_user(OWNER_ID),
                line.id,
                ReportLineUpdate(report_id=report.id, amount=99.0),
            )

    async def test_delete_rejected_on_non_draft_report(self, db):
        budget = await _make_budget(db)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        line = await create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
                expense_date=date(2026, 6, 15),
            ),
        )
        report.status = ReportStatus.approved
        await db.commit()

        with pytest.raises(DomainError):
            await delete_report_line_service(db, _valid_user(OWNER_ID), line.id)

    async def test_update_allowed_on_draft_report(self, db):
        budget = await _make_budget(db)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        line = await create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
                expense_date=date(2026, 6, 15),
            ),
        )

        updated = await update_report_line_service(
            db, _valid_user(OWNER_ID), line.id, ReportLineUpdate(report_id=report.id, amount=99.0)
        )

        assert updated.amount == 99.0


@pytest.mark.anyio
class TestDeleteCascadesAttachments:
    """Deleting a report line with attachments must not raise (the ORM
    relationship cascades the rows) and must clean up their storage blobs
    rather than orphaning them."""

    async def test_delete_removes_attachments_and_blobs(self, db, storage):
        budget = await _make_budget(db)
        budget_line = await _make_budget_line(db, budget.id)
        report = await _make_report(db, budget.id)
        line = await create_report_line_service(
            db,
            _valid_user(OWNER_ID),
            ReportLineCreate(
                report_id=report.id,
                budget_line_id=budget_line.id,
                description="Receipt",
                amount=50.0,
                expense_date=date(2026, 6, 15),
            ),
        )
        attachment = AttachmentModel(
            report_line_id=line.id,
            filename="receipt.pdf",
            content_type="application/pdf",
            size=10,
            storage_key="attachments/some/key.pdf",
        )
        db.add(attachment)
        await db.commit()

        await delete_report_line_service(db, _valid_user(OWNER_ID), line.id)

        storage.delete.assert_called_once_with("attachments/some/key.pdf")
        remaining_attachment = (
            await db.execute(select(AttachmentModel).filter_by(report_line_id=line.id))
        ).scalar_one_or_none()
        remaining_line = (
            await db.execute(select(ReportLineModel).filter_by(id=line.id))
        ).scalar_one_or_none()
        assert remaining_attachment is None
        assert remaining_line is None
