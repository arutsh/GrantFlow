"""
Tests for openspec/changes/recovering-archived-budgets — restore_budget_service.

Uses the shared `db` fixture (conftest.py) — a real sqlite session — since
these behaviors hinge on real BudgetModel column state (status, confirmed_at,
start_date) rather than a single mocked crud call.
"""

from datetime import date
from uuid import uuid4

import pytest

from app.core.exceptions import DomainError
from app.models.budget import BudgetModel
from app.schemas.budget_schema import BudgetStatus
from app.services.budget_services import restore_budget_service
from tests.factories.user import make_valid_user

pytestmark = pytest.mark.anyio

OWNER_ID = str(uuid4())
STRANGER_ID = str(uuid4())


async def _make_budget(
    db,
    owner_id=OWNER_ID,
    status=BudgetStatus.archived,
    confirmed_at=None,
    start_date=None,
):
    budget = BudgetModel(
        name="Test Budget",
        owner_id=owner_id,
        status=status,
        confirmed_at=confirmed_at,
        start_date=start_date,
        duration_months=12,
        local_currency="GBP",
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


class TestRestoreArchivedBudget:
    async def test_restore_from_archived_was_confirmed(self, db):
        import datetime as dt

        budget = await _make_budget(
            db,
            confirmed_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
            start_date=date(2026, 1, 1),
        )

        result = await restore_budget_service(budget.id, make_valid_user(customer_id=OWNER_ID), db)

        assert result.status == BudgetStatus.confirmed
        assert result.start_date == date(2026, 1, 1)

    async def test_restore_from_archived_was_draft(self, db):
        budget = await _make_budget(db)

        result = await restore_budget_service(budget.id, make_valid_user(customer_id=OWNER_ID), db)

        assert result.status == BudgetStatus.draft

    async def test_restore_falls_back_to_draft_when_start_date_missing(self, db):
        import datetime as dt

        budget = await _make_budget(
            db,
            confirmed_at=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
            start_date=None,
        )

        result = await restore_budget_service(budget.id, make_valid_user(customer_id=OWNER_ID), db)

        assert result.status == BudgetStatus.draft
        assert result.confirmed_at is None

    async def test_restore_rejected_on_a_non_archived_budget(self, db):
        budget = await _make_budget(db, status=BudgetStatus.draft)

        with pytest.raises(DomainError):
            await restore_budget_service(budget.id, make_valid_user(customer_id=OWNER_ID), db)

    async def test_restore_rejected_for_a_non_owner_non_superuser_caller(self, db):
        budget = await _make_budget(db)

        with pytest.raises(DomainError):
            await restore_budget_service(budget.id, make_valid_user(customer_id=STRANGER_ID), db)

    async def test_superuser_without_matching_session_cannot_restore(self, db):
        """No active impersonation session for this owner means not-found."""
        budget = await _make_budget(db)

        with pytest.raises(DomainError):
            await restore_budget_service(
                budget.id, make_valid_user(customer_id=STRANGER_ID, role="superuser"), db
            )

    async def test_superuser_impersonating_the_owner_can_restore(self, db):
        budget = await _make_budget(db)

        result = await restore_budget_service(
            budget.id, make_valid_user(customer_id=OWNER_ID, role="superuser"), db
        )

        assert result.status == BudgetStatus.draft
