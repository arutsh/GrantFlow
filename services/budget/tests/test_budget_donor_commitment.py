"""
Tests for ticket #179 (budget-report-iteration-2, group 1): donor_total_amount,
estimated_exchange_rate, confirmed_at, and the derived estimated_local_cap.

Covers: column round-trip (real sqlite session, matching the convention in
test_budget_currency_fields.py), the metadata-lock on a confirmed budget
(mocked crud layer, matching update_budget_service's existing test
convention), confirmed_at set/reset on the confirm transition, and
estimated_local_cap computed at read time via the full GET /budgets/{id}
route (matching test_budget_services.py's end_date tests).
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app
from app.api.budget_routes import get_validated_user
from tests.factories.user import make_valid_user
from tests.factories.budget import BudgetFactory
from app.core.exceptions import DomainError
from app.schemas.budget_schema import BudgetCreate, BudgetStatus, BudgetUpdate
from app.services.budget_services import update_budget_service

USER_ID = str(uuid4())
CUSTOMER_ID = str(uuid4())
DB = object()  # session is never actually used — every crud call is mocked

client = TestClient(app)


def _valid_user():
    return make_valid_user(user_id=USER_ID, customer_id=CUSTOMER_ID)


def _payload(**kwargs):
    kwargs.setdefault("name", "Grant")
    kwargs.setdefault("funding_customer_id", uuid4())
    return BudgetCreate(**kwargs)


class TestColumnRoundTrip:
    def test_new_columns_persist_and_reload(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models.base import Base
        from app.models.budget import BudgetModel

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[BudgetModel.__table__])
        session = sessionmaker(bind=engine)()

        confirmed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        budget = BudgetModel(
            name="Downstream",
            owner_id=uuid4(),
            local_currency="EUR",
            actual_currency="USD",
            donor_total_amount=10000,
            estimated_exchange_rate=0.8,
            confirmed_at=confirmed_at,
        )
        session.add(budget)
        session.commit()
        session.refresh(budget)

        reloaded = session.query(BudgetModel).filter(BudgetModel.id == budget.id).one()
        assert reloaded.donor_total_amount == 10000
        assert reloaded.estimated_exchange_rate == 0.8
        # sqlite drops tzinfo on round-trip (unlike Postgres); compare naive.
        assert reloaded.confirmed_at.replace(tzinfo=timezone.utc) == confirmed_at

    def test_new_columns_default_to_null(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models.base import Base
        from app.models.budget import BudgetModel

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[BudgetModel.__table__])
        session = sessionmaker(bind=engine)()

        budget = BudgetModel(name="Plain", owner_id=uuid4())
        session.add(budget)
        session.commit()
        session.refresh(budget)

        assert budget.donor_total_amount is None
        assert budget.estimated_exchange_rate is None
        assert budget.confirmed_at is None


class TestMetadataLockOnConfirmed:
    def test_set_donor_commitment_on_unconfirmed_budget_is_accepted(self):
        existing = BudgetFactory.build(id=uuid4(), owner_id=CUSTOMER_ID, status=BudgetStatus.draft)
        payload = _payload(donor_total_amount=10000, estimated_exchange_rate=0.8)

        with (
            patch(
                "app.services.budget_services.validate_customer_can_fund",
                return_value=None,
            ),
            patch(
                "app.services.budget_services.validate_donor_grantee_relationship",
                return_value=None,
            ),
            patch("app.services.budget_services.get_budget", return_value=existing),
            patch(
                "app.services.budget_services.update_budget", return_value=existing
            ) as mock_update,
        ):
            import asyncio

            result = asyncio.run(update_budget_service(existing.id, payload, _valid_user(), DB))

        assert result.id == existing.id
        mock_update.assert_called_once()
        assert mock_update.call_args.kwargs["donor_total_amount"] == 10000
        assert mock_update.call_args.kwargs["donor_total_amount_set"] is True
        assert mock_update.call_args.kwargs["estimated_exchange_rate"] == 0.8
        assert mock_update.call_args.kwargs["estimated_exchange_rate_set"] is True

    def test_donor_commitment_edit_rejected_on_confirmed_budget(self):
        existing = BudgetFactory.build(
            id=uuid4(),
            owner_id=CUSTOMER_ID,
            status=BudgetStatus.confirmed,
            start_date=date(2026, 1, 1),
        )
        payload = _payload(donor_total_amount=10000)

        with (
            patch(
                "app.services.budget_services.validate_customer_can_fund",
                return_value=None,
            ),
            patch(
                "app.services.budget_services.validate_donor_grantee_relationship",
                return_value=None,
            ),
            patch("app.services.budget_services.get_budget", return_value=existing),
        ):
            with pytest.raises((DomainError, HTTPException)):
                import asyncio

                asyncio.run(update_budget_service(existing.id, payload, _valid_user(), DB))

    def test_estimated_exchange_rate_edit_rejected_on_confirmed_budget(self):
        existing = BudgetFactory.build(
            id=uuid4(),
            owner_id=CUSTOMER_ID,
            status=BudgetStatus.confirmed,
            start_date=date(2026, 1, 1),
        )
        payload = _payload(estimated_exchange_rate=0.9)

        with (
            patch(
                "app.services.budget_services.validate_customer_can_fund",
                return_value=None,
            ),
            patch(
                "app.services.budget_services.validate_donor_grantee_relationship",
                return_value=None,
            ),
            patch("app.services.budget_services.get_budget", return_value=existing),
        ):
            with pytest.raises((DomainError, HTTPException)):
                import asyncio

                asyncio.run(update_budget_service(existing.id, payload, _valid_user(), DB))


class TestClearingDonorFields:
    """Regression test: update_budget's CRUD used to treat an incoming None
    the same as "field omitted", so blanking the donor commitment/rate in
    the edit form could never actually clear them — the old value silently
    survived every save (see update_budget_service's donor_total_amount_set/
    estimated_exchange_rate_set kwargs)."""

    def test_donor_total_amount_and_rate_can_be_cleared(self, db):
        from app.models.budget import BudgetModel

        budget = BudgetModel(
            name="Grant",
            owner_id=CUSTOMER_ID,
            status=BudgetStatus.draft,
            donor_total_amount=10000,
            estimated_exchange_rate=0.8,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

        payload = BudgetUpdate(donor_total_amount=None, estimated_exchange_rate=None)

        with patch("app.services.budget_services.validate_customer_can_fund", return_value=None):
            import asyncio

            result = asyncio.run(update_budget_service(budget.id, payload, _valid_user(), db))

        assert result.donor_total_amount is None
        assert result.estimated_exchange_rate is None
        db.refresh(budget)
        assert budget.donor_total_amount is None
        assert budget.estimated_exchange_rate is None

    def test_omitting_the_fields_leaves_them_unchanged(self, db):
        from app.models.budget import BudgetModel

        budget = BudgetModel(
            name="Grant",
            owner_id=CUSTOMER_ID,
            status=BudgetStatus.draft,
            donor_total_amount=10000,
            estimated_exchange_rate=0.8,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

        payload = BudgetUpdate(name="Renamed")

        with patch("app.services.budget_services.validate_customer_can_fund", return_value=None):
            import asyncio

            result = asyncio.run(update_budget_service(budget.id, payload, _valid_user(), db))

        assert result.name == "Renamed"
        assert result.donor_total_amount == 10000
        assert result.estimated_exchange_rate == 0.8


class TestConfirmedAtTransition:
    def test_confirmed_at_set_on_first_confirm(self):
        existing = BudgetFactory.build(
            id=uuid4(),
            owner_id=CUSTOMER_ID,
            status=BudgetStatus.draft,
            start_date=date(2026, 1, 1),
            confirmed_at=None,
        )
        payload = _payload(status=BudgetStatus.confirmed)

        with (
            patch(
                "app.services.budget_services.validate_customer_can_fund",
                return_value=None,
            ),
            patch(
                "app.services.budget_services.validate_donor_grantee_relationship",
                return_value=None,
            ),
            patch("app.services.budget_services.get_budget", return_value=existing),
            patch(
                "app.services.budget_services.update_budget", return_value=existing
            ) as mock_update,
        ):
            import asyncio

            asyncio.run(update_budget_service(existing.id, payload, _valid_user(), DB))

        confirmed_at = mock_update.call_args.kwargs["confirmed_at"]
        assert confirmed_at is not None
        assert (datetime.now(timezone.utc) - confirmed_at) < timedelta(seconds=5)

    def test_confirmed_at_updated_on_reconfirm_after_revert(self):
        stale_confirmed_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        existing = BudgetFactory.build(
            id=uuid4(),
            owner_id=CUSTOMER_ID,
            status=BudgetStatus.draft,  # reverted back to draft after a prior confirm
            start_date=date(2026, 1, 1),
            confirmed_at=stale_confirmed_at,
        )
        payload = _payload(status=BudgetStatus.confirmed)

        with (
            patch(
                "app.services.budget_services.validate_customer_can_fund",
                return_value=None,
            ),
            patch(
                "app.services.budget_services.validate_donor_grantee_relationship",
                return_value=None,
            ),
            patch("app.services.budget_services.get_budget", return_value=existing),
            patch(
                "app.services.budget_services.update_budget", return_value=existing
            ) as mock_update,
        ):
            import asyncio

            asyncio.run(update_budget_service(existing.id, payload, _valid_user(), DB))

        confirmed_at = mock_update.call_args.kwargs["confirmed_at"]
        assert confirmed_at is not None
        assert confirmed_at > stale_confirmed_at

    def test_confirmed_at_not_touched_on_non_confirm_update(self):
        existing = BudgetFactory.build(id=uuid4(), owner_id=CUSTOMER_ID, status=BudgetStatus.draft)
        payload = _payload(name="Renamed")

        with (
            patch(
                "app.services.budget_services.validate_customer_can_fund",
                return_value=None,
            ),
            patch(
                "app.services.budget_services.validate_donor_grantee_relationship",
                return_value=None,
            ),
            patch("app.services.budget_services.get_budget", return_value=existing),
            patch(
                "app.services.budget_services.update_budget", return_value=existing
            ) as mock_update,
        ):
            import asyncio

            asyncio.run(update_budget_service(existing.id, payload, _valid_user(), DB))

        assert mock_update.call_args.kwargs["confirmed_at"] is None


class TestEstimatedLocalCap:
    """GET /api/v1/budgets/{id} — estimated_local_cap derived at read time."""

    @pytest.fixture(autouse=True)
    def override_auth(self):
        app.dependency_overrides[get_validated_user] = lambda: make_valid_user(
            user_id=USER_ID, customer_id=CUSTOMER_ID
        )
        yield
        app.dependency_overrides = {}

    def _get(self, budget):
        with (
            patch("app.services.budget_services.get_budget", return_value=budget),
            patch(
                "app.services.budget_services.get_users_by_ids_cached",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.budget_services.get_customers_by_ids",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch("app.api.budget_routes.get_viewable_budget_lines_service", return_value=[]),
        ):
            return client.get(f"/api/v1/budgets/{budget.id}")

    def test_present_when_both_inputs_set(self):
        budget = BudgetFactory.build(
            owner_id=CUSTOMER_ID,
            created_by=USER_ID,
            updated_by=USER_ID,
            donor_total_amount=10000,
            estimated_exchange_rate=0.8,
        )
        response = self._get(budget)
        assert response.status_code == 200
        assert response.json()["estimated_local_cap"] == 8000

    def test_null_when_estimated_exchange_rate_missing(self):
        budget = BudgetFactory.build(
            owner_id=CUSTOMER_ID,
            created_by=USER_ID,
            updated_by=USER_ID,
            donor_total_amount=10000,
            estimated_exchange_rate=None,
        )
        response = self._get(budget)
        assert response.status_code == 200
        assert response.json()["estimated_local_cap"] is None

    def test_null_when_donor_total_amount_missing(self):
        budget = BudgetFactory.build(
            owner_id=CUSTOMER_ID,
            created_by=USER_ID,
            updated_by=USER_ID,
            donor_total_amount=None,
            estimated_exchange_rate=0.8,
        )
        response = self._get(budget)
        assert response.status_code == 200
        assert response.json()["estimated_local_cap"] is None

    def test_null_when_either_input_is_zero(self):
        budget = BudgetFactory.build(
            owner_id=CUSTOMER_ID,
            created_by=USER_ID,
            updated_by=USER_ID,
            donor_total_amount=0,
            estimated_exchange_rate=0.8,
        )
        response = self._get(budget)
        assert response.status_code == 200
        assert response.json()["estimated_local_cap"] is None
