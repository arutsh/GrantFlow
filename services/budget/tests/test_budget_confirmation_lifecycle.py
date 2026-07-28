"""
Tests for ticket #160's expanded scope (see openspec/changes/budget-report-frontend
design.md's "Confirm access extends to the matching funder" /
"Reverting a confirmed budget to draft" / "Editing budget metadata/lines is
blocked once the budget has any report" decisions).

Uses the shared `db` fixture (conftest.py) — a real sqlite session covering
Budget/BudgetLine/BudgetCategory/Report/ReportLine — since these behaviors
hinge on the real Budget<->Report relationship rather than a single mocked
crud call.
"""

from datetime import date
from uuid import uuid4

import pytest

from app.core.exceptions import DomainError
from app.models.budget import BudgetModel, BudgetLineModel, BudgetCategoryModel
from app.models.report import ReportModel, ReportLineModel
from app.schemas.budget_schema import BudgetStatus, BudgetUpdate
from app.schemas.report_schema import ReportStatus
from app.services.budget_services import update_budget_service
from app.services.budget_line_services import (
    create_budget_line_service,
    update_budget_line_service,
    delete_budget_line_service,
)
from app.schemas import BudgetLineCreate, BudgetLineUpdate
from tests.factories.user import make_valid_user

OWNER_ID = str(uuid4())
FUNDER_ID = str(uuid4())
STRANGER_ID = str(uuid4())


def _valid_user(customer_id):
    return make_valid_user(customer_id=customer_id)


def _make_budget(
    db,
    owner_id=OWNER_ID,
    funding_customer_id=None,
    status=BudgetStatus.draft,
    start_date=None,
    duration_months=12,
):
    budget = BudgetModel(
        name="Test Budget",
        owner_id=owner_id,
        funding_customer_id=funding_customer_id,
        status=status,
        start_date=start_date,
        duration_months=duration_months,
        local_currency="GBP",
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def _make_report(db, budget_id, status=ReportStatus.draft):
    report = ReportModel(
        budget_id=budget_id,
        name="Interim report",
        status=status,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


class TestFunderCanConfirm:
    def test_matching_funder_can_confirm_a_draft_budget(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID, status=BudgetStatus.draft)
        payload = BudgetUpdate(status=BudgetStatus.confirmed, start_date=date(2026, 2, 1))

        import asyncio

        result = asyncio.run(
            update_budget_service(budget.id, payload, _valid_user(FUNDER_ID), db)
        )

        assert result.status == BudgetStatus.confirmed
        assert result.start_date == date(2026, 2, 1)

    def test_matching_funder_can_confirm_an_ai_draft_budget(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID, status=BudgetStatus.ai_draft)
        payload = BudgetUpdate(status=BudgetStatus.confirmed, start_date=date(2026, 2, 1))

        import asyncio

        result = asyncio.run(
            update_budget_service(budget.id, payload, _valid_user(FUNDER_ID), db)
        )

        assert result.status == BudgetStatus.confirmed

    def test_stranger_cannot_confirm(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID, status=BudgetStatus.draft)
        payload = BudgetUpdate(status=BudgetStatus.confirmed, start_date=date(2026, 2, 1))

        import asyncio

        with pytest.raises(DomainError):
            asyncio.run(
                update_budget_service(budget.id, payload, _valid_user(STRANGER_ID), db)
            )

    def test_funder_cannot_edit_metadata(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID, status=BudgetStatus.draft)
        payload = BudgetUpdate(name="Renamed by funder")

        import asyncio

        with pytest.raises(DomainError):
            asyncio.run(
                update_budget_service(budget.id, payload, _valid_user(FUNDER_ID), db)
            )

    def test_funder_cannot_bundle_a_confirm_with_a_metadata_edit(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID, status=BudgetStatus.draft)
        payload = BudgetUpdate(
            status=BudgetStatus.confirmed,
            start_date=date(2026, 2, 1),
            name="Renamed while confirming",
        )

        import asyncio

        with pytest.raises(DomainError, match="metadata"):
            asyncio.run(
                update_budget_service(budget.id, payload, _valid_user(FUNDER_ID), db)
            )

        db.refresh(budget)
        assert budget.status == BudgetStatus.draft

    def test_funder_cannot_revert_a_confirmed_budget(self, db):
        budget = _make_budget(
            db,
            funding_customer_id=FUNDER_ID,
            status=BudgetStatus.confirmed,
            start_date=date(2026, 1, 1),
        )
        payload = BudgetUpdate(status=BudgetStatus.draft)

        import asyncio

        with pytest.raises(DomainError):
            asyncio.run(
                update_budget_service(budget.id, payload, _valid_user(FUNDER_ID), db)
            )


class TestRevertToDraft:
    def test_owner_can_revert_a_confirmed_budget_with_no_reports(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        payload = BudgetUpdate(status=BudgetStatus.draft)

        import asyncio

        result = asyncio.run(
            update_budget_service(budget.id, payload, _valid_user(OWNER_ID), db)
        )

        assert result.status == BudgetStatus.draft

    def test_revert_blocked_by_a_submitted_report(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        _make_report(db, budget.id, status=ReportStatus.submitted)
        payload = BudgetUpdate(status=BudgetStatus.draft)

        import asyncio

        with pytest.raises(DomainError):
            asyncio.run(
                update_budget_service(budget.id, payload, _valid_user(OWNER_ID), db)
            )

        db.refresh(budget)
        assert budget.status == BudgetStatus.confirmed

    def test_revert_blocked_by_an_approved_report(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        _make_report(db, budget.id, status=ReportStatus.approved)
        payload = BudgetUpdate(status=BudgetStatus.draft)

        import asyncio

        with pytest.raises(DomainError):
            asyncio.run(
                update_budget_service(budget.id, payload, _valid_user(OWNER_ID), db)
            )

    def test_revert_succeeds_and_deletes_draft_reports(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        report = _make_report(db, budget.id, status=ReportStatus.draft)
        report_id = report.id
        payload = BudgetUpdate(status=BudgetStatus.draft)

        import asyncio

        result = asyncio.run(
            update_budget_service(budget.id, payload, _valid_user(OWNER_ID), db)
        )

        assert result.status == BudgetStatus.draft
        remaining = db.query(ReportModel).filter(ReportModel.budget_id == budget.id).all()
        assert remaining == []
        assert db.query(ReportModel).filter(ReportModel.id == report_id).first() is None

    def test_revert_succeeds_and_deletes_draft_report_with_lines(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        budget_line = BudgetLineModel(budget_id=budget.id, description="Line", amount=100)
        db.add(budget_line)
        db.commit()
        db.refresh(budget_line)

        report = _make_report(db, budget.id, status=ReportStatus.draft)
        report_line = ReportLineModel(
            report_id=report.id, budget_line_id=budget_line.id, description="Spent", amount=50
        )
        db.add(report_line)
        db.commit()
        report_id = report.id
        report_line_id = report_line.id

        payload = BudgetUpdate(status=BudgetStatus.draft)

        import asyncio

        result = asyncio.run(
            update_budget_service(budget.id, payload, _valid_user(OWNER_ID), db)
        )

        assert result.status == BudgetStatus.draft
        assert db.query(ReportModel).filter(ReportModel.id == report_id).first() is None
        assert (
            db.query(ReportLineModel).filter(ReportLineModel.id == report_line_id).first()
            is None
        )


class TestConfirmStatusGuard:
    def test_owner_cannot_reconfirm_an_already_confirmed_budget(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        payload = BudgetUpdate(status=BudgetStatus.confirmed, start_date=date(2026, 2, 1))

        import asyncio

        with pytest.raises(DomainError):
            asyncio.run(
                update_budget_service(budget.id, payload, _valid_user(OWNER_ID), db)
            )

        db.refresh(budget)
        assert budget.start_date == date(2026, 1, 1)

    def test_owner_cannot_confirm_an_archived_budget(self, db):
        budget = _make_budget(db, status=BudgetStatus.archived)
        payload = BudgetUpdate(status=BudgetStatus.confirmed, start_date=date(2026, 2, 1))

        import asyncio

        with pytest.raises(DomainError):
            asyncio.run(
                update_budget_service(budget.id, payload, _valid_user(OWNER_ID), db)
            )


class TestStartDateLockedOnceConfirmed:
    def test_bare_start_date_edit_is_rejected_on_a_confirmed_budget(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        payload = BudgetUpdate(start_date=date(2027, 1, 1))

        import asyncio

        with pytest.raises(DomainError):
            asyncio.run(
                update_budget_service(budget.id, payload, _valid_user(OWNER_ID), db)
            )

        db.refresh(budget)
        assert budget.start_date == date(2026, 1, 1)


class TestEditLockedOnceConfirmed:
    """Budget metadata/lines lock as soon as the budget is `confirmed` — not
    only once a report exists. A report can only ever be created against an
    already-confirmed budget (create_report_service), so "confirmed" is a
    strictly broader (and correct) condition than "has a report": there's a
    real window — confirmed, before any report is created — where the old
    report-based guard would have wrongly allowed edits."""

    def test_metadata_edit_blocked_when_confirmed_even_without_a_report(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        payload = BudgetUpdate(name="Renamed")

        import asyncio

        with pytest.raises(DomainError):
            asyncio.run(
                update_budget_service(budget.id, payload, _valid_user(OWNER_ID), db)
            )

    def test_metadata_edit_blocked_when_confirmed_with_a_report(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        _make_report(db, budget.id, status=ReportStatus.draft)
        payload = BudgetUpdate(name="Renamed")

        import asyncio

        with pytest.raises(DomainError):
            asyncio.run(
                update_budget_service(budget.id, payload, _valid_user(OWNER_ID), db)
            )

    def test_metadata_edit_allowed_on_a_draft_budget(self, db):
        budget = _make_budget(db, status=BudgetStatus.draft)
        payload = BudgetUpdate(name="Renamed")

        import asyncio

        result = asyncio.run(
            update_budget_service(budget.id, payload, _valid_user(OWNER_ID), db)
        )

        assert result.name == "Renamed"
        # A bare metadata edit that omits `status` must not silently reset it.
        assert result.status == BudgetStatus.draft

    def test_create_budget_line_blocked_when_confirmed_even_without_a_report(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        payload = BudgetLineCreate(
            budget_id=budget.id,
            description="New line",
            amount=100.0,
            category_name="Personnel",
        )

        with pytest.raises(DomainError):
            create_budget_line_service(db, _valid_user(OWNER_ID), payload)

    def test_create_budget_line_blocked_when_confirmed_with_a_report(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        _make_report(db, budget.id, status=ReportStatus.draft)
        payload = BudgetLineCreate(
            budget_id=budget.id,
            description="New line",
            amount=100.0,
            category_name="Personnel",
        )

        with pytest.raises(DomainError):
            create_budget_line_service(db, _valid_user(OWNER_ID), payload)

    def _make_line(self, db, budget_id):
        category = BudgetCategoryModel(name="Personnel", code="PERSONNEL")
        db.add(category)
        db.commit()
        db.refresh(category)
        line = BudgetLineModel(
            budget_id=budget_id, category_id=category.id, description="Line", amount=100.0
        )
        db.add(line)
        db.commit()
        db.refresh(line)
        return line

    def test_update_budget_line_blocked_when_confirmed_even_without_a_report(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        line = self._make_line(db, budget.id)

        with pytest.raises(DomainError):
            update_budget_line_service(
                db,
                _valid_user(OWNER_ID),
                line.id,
                BudgetLineUpdate(budget_id=budget.id, amount=200.0),
            )

    def test_update_budget_line_blocked_when_confirmed_with_a_report(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        line = self._make_line(db, budget.id)
        _make_report(db, budget.id, status=ReportStatus.draft)

        with pytest.raises(DomainError):
            update_budget_line_service(
                db,
                _valid_user(OWNER_ID),
                line.id,
                BudgetLineUpdate(budget_id=budget.id, amount=200.0),
            )

    def test_delete_budget_line_blocked_when_confirmed_even_without_a_report(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        line = self._make_line(db, budget.id)

        with pytest.raises(DomainError):
            delete_budget_line_service(line.id, _valid_user(OWNER_ID), db)

    def test_delete_budget_line_blocked_when_confirmed_with_a_report(self, db):
        budget = _make_budget(db, status=BudgetStatus.confirmed, start_date=date(2026, 1, 1))
        line = self._make_line(db, budget.id)
        _make_report(db, budget.id, status=ReportStatus.draft)

        with pytest.raises(DomainError):
            delete_budget_line_service(line.id, _valid_user(OWNER_ID), db)
