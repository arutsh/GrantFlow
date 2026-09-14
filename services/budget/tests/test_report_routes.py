"""
Tests for ticket #146: report submission lifecycle.

The bulk of this suite calls the service layer directly against a real
sqlite session (matching the convention in
test_budget_line_services.py::TestRecalculateBudgetTotalCrud) — period
overlap detection and the confirmed-budget/permission gates are real SQL
and cross-record checks that are more reliably exercised this way than by
mocking every crud call individually. A small TestClient-based class at the
bottom covers route wiring (auth dependency, status codes) with the service
layer mocked, matching test_donor_scoped_endpoints.py's convention.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from dateutil.relativedelta import relativedelta

from app.core.exceptions import DomainError, PermissionDenied
from app.models.budget import BudgetModel
from app.models.report import ReportModel
from app.schemas.budget_schema import BudgetStatus
from app.schemas.report_schema import ReportStatus, ReportCreate, ReportUpdate
from app.services.report_services import (
    create_report_service,
    get_report_service,
    list_reports_service,
    list_all_reports_service,
    list_funded_reports_service,
    update_report_service,
    delete_report_service,
    submit_report_service,
    review_report_service,
    reopen_report_service,
)
from tests.factories.user import make_valid_user

OWNER_ID = str(uuid4())
FUNDER_ID = str(uuid4())
STRANGER_ID = str(uuid4())


def _valid_user(customer_id):
    return make_valid_user(customer_id=customer_id)


async def _make_budget(
    db,
    owner_id=OWNER_ID,
    funding_customer_id=None,
    status=BudgetStatus.confirmed,
    start_date=date(2026, 1, 1),
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
    await db.commit()
    await db.refresh(budget)
    return budget


async def _make_report(
    db, budget_id, status=ReportStatus.draft, period_start=None, period_end=None
):
    report = ReportModel(
        budget_id=budget_id,
        name="Interim report",
        status=status,
        period_start=period_start or date(2026, 1, 1),
        period_end=period_end or date(2026, 3, 31),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@pytest.mark.anyio
class TestCreateReportService:
    async def test_defaults_period_to_budget_full_span_when_omitted(self, db):
        budget = await _make_budget(db)
        payload = ReportCreate(budget_id=budget.id, name="Final report")

        result = await create_report_service(db, _valid_user(OWNER_ID), payload)

        assert result.period_start == budget.start_date
        assert result.period_end == budget.start_date + relativedelta(months=12)
        assert result.status == ReportStatus.draft

    async def test_creates_with_explicit_narrower_period(self, db):
        budget = await _make_budget(db)
        payload = ReportCreate(
            budget_id=budget.id,
            name="Q1 report",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        )

        result = await create_report_service(db, _valid_user(OWNER_ID), payload)

        assert result.period_start == date(2026, 1, 1)
        assert result.period_end == date(2026, 3, 31)

    async def test_rejected_when_only_period_start_supplied(self, db):
        # Regression: previously silently period-stomped instead of rejecting.
        budget = await _make_budget(db)
        payload = ReportCreate(budget_id=budget.id, name="Partial", period_start=date(2026, 2, 1))

        with pytest.raises(DomainError):
            await create_report_service(db, _valid_user(OWNER_ID), payload)

    async def test_rejected_when_only_period_end_supplied(self, db):
        budget = await _make_budget(db)
        payload = ReportCreate(budget_id=budget.id, name="Partial", period_end=date(2026, 2, 1))

        with pytest.raises(DomainError):
            await create_report_service(db, _valid_user(OWNER_ID), payload)

    async def test_rejected_when_period_is_inverted(self, db):
        budget = await _make_budget(db)
        payload = ReportCreate(
            budget_id=budget.id,
            name="Inverted",
            period_start=date(2026, 6, 1),
            period_end=date(2026, 1, 1),
        )

        with pytest.raises(DomainError):
            await create_report_service(db, _valid_user(OWNER_ID), payload)

    async def test_rejected_when_budget_not_confirmed(self, db):
        budget = await _make_budget(db, status=BudgetStatus.draft)
        payload = ReportCreate(budget_id=budget.id, name="Too early")

        with pytest.raises(DomainError):
            await create_report_service(db, _valid_user(OWNER_ID), payload)

    async def test_rejected_when_confirmed_budget_has_no_start_date(self, db):
        # Guards a hypothetical future path that sets confirmed directly.
        budget = await _make_budget(db, start_date=None)
        payload = ReportCreate(budget_id=budget.id, name="No start date")

        with pytest.raises(DomainError):
            await create_report_service(db, _valid_user(OWNER_ID), payload)

    async def test_rejected_for_user_without_budget_access(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        payload = ReportCreate(budget_id=budget.id, name="Not yours")

        with pytest.raises(DomainError):
            await create_report_service(db, _valid_user(STRANGER_ID), payload)

    async def test_funder_has_access_to_create(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        payload = ReportCreate(budget_id=budget.id, name="Funder-created")

        result = await create_report_service(db, _valid_user(FUNDER_ID), payload)

        assert result.budget_id == budget.id

    async def test_rejected_on_period_overlap_including_against_rejected_report(self, db):
        budget = await _make_budget(db)
        await _make_report(
            db,
            budget.id,
            status=ReportStatus.rejected,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 6, 30),
        )
        payload = ReportCreate(
            budget_id=budget.id,
            name="Overlapping",
            period_start=date(2026, 6, 1),
            period_end=date(2026, 9, 30),
        )

        with pytest.raises(DomainError):
            await create_report_service(db, _valid_user(OWNER_ID), payload)

    async def test_non_overlapping_period_allowed_regardless_of_existing_status(self, db):
        budget = await _make_budget(db)
        await _make_report(
            db,
            budget.id,
            status=ReportStatus.submitted,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 6, 30),
        )
        payload = ReportCreate(
            budget_id=budget.id,
            name="Next period",
            period_start=date(2026, 7, 1),
            period_end=date(2026, 12, 31),
        )

        result = await create_report_service(db, _valid_user(OWNER_ID), payload)

        assert result.period_start == date(2026, 7, 1)


@pytest.mark.anyio
class TestReportAccess:
    async def test_owner_can_get_and_list(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        report = await _make_report(db, budget.id)

        result = await get_report_service(db, _valid_user(OWNER_ID), report.id)
        assert result.id == report.id
        assert len(await list_reports_service(db, _valid_user(OWNER_ID), budget.id)) == 1

    async def test_funder_can_get_and_list(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        report = await _make_report(db, budget.id)

        result = await get_report_service(db, _valid_user(FUNDER_ID), report.id)
        assert result.id == report.id
        assert len(await list_reports_service(db, _valid_user(FUNDER_ID), budget.id)) == 1

    async def test_stranger_cannot_get_or_list(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        report = await _make_report(db, budget.id)

        with pytest.raises(DomainError):
            await get_report_service(db, _valid_user(STRANGER_ID), report.id)
        with pytest.raises(DomainError):
            await list_reports_service(db, _valid_user(STRANGER_ID), budget.id)


@pytest.mark.anyio
class TestListAllReportsService:
    """GET /reports/ — owner's cross-budget reports directory."""

    async def test_owner_sees_reports_across_all_their_budgets(self, db):
        budget_a = await _make_budget(db)
        budget_b = await _make_budget(db)
        other_owner_budget = await _make_budget(db, owner_id=STRANGER_ID)
        report_a = await _make_report(db, budget_a.id)
        report_b = await _make_report(
            db, budget_b.id, period_start=date(2026, 4, 1), period_end=date(2026, 6, 30)
        )
        await _make_report(db, other_owner_budget.id)

        results = await list_all_reports_service(db, _valid_user(OWNER_ID))

        assert {r.id for r in results} == {report_a.id, report_b.id}

    async def test_donor_does_not_see_reports_on_budgets_they_only_fund(self, db):
        # Owner-scoped directory must not leak funder-visible reports.
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        await _make_report(db, budget.id)

        assert await list_all_reports_service(db, _valid_user(FUNDER_ID)) == []

    async def test_stranger_sees_nothing(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        await _make_report(db, budget.id)

        assert await list_all_reports_service(db, _valid_user(STRANGER_ID)) == []

    async def test_status_filter(self, db):
        budget = await _make_budget(db)
        draft = await _make_report(db, budget.id, status=ReportStatus.draft)
        await _make_report(
            db,
            budget.id,
            status=ReportStatus.submitted,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 6, 30),
        )

        results = await list_all_reports_service(
            db, _valid_user(OWNER_ID), status=ReportStatus.draft
        )

        assert [r.id for r in results] == [draft.id]

    async def test_budget_id_filter(self, db):
        budget_a = await _make_budget(db)
        budget_b = await _make_budget(db)
        report_a = await _make_report(db, budget_a.id)
        await _make_report(
            db, budget_b.id, period_start=date(2026, 4, 1), period_end=date(2026, 6, 30)
        )

        results = await list_all_reports_service(db, _valid_user(OWNER_ID), budget_id=budget_a.id)

        assert [r.id for r in results] == [report_a.id]

    async def test_funding_customer_id_filter(self, db):
        funded_budget = await _make_budget(db, owner_id=OWNER_ID, funding_customer_id=FUNDER_ID)
        unfunded_budget = await _make_budget(db, owner_id=OWNER_ID)
        funded_report = await _make_report(db, funded_budget.id)
        await _make_report(
            db,
            unfunded_budget.id,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 6, 30),
        )

        results = await list_all_reports_service(
            db, _valid_user(OWNER_ID), funding_customer_id=FUNDER_ID
        )

        assert [r.id for r in results] == [funded_report.id]

    async def test_filters_combine(self, db):
        budget_a = await _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_b = await _make_budget(db, funding_customer_id=FUNDER_ID)
        matching = await _make_report(db, budget_a.id, status=ReportStatus.draft)
        await _make_report(
            db,
            budget_a.id,
            status=ReportStatus.submitted,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 6, 30),
        )
        await _make_report(db, budget_b.id, status=ReportStatus.draft)

        results = await list_all_reports_service(
            db,
            _valid_user(OWNER_ID),
            status=ReportStatus.draft,
            budget_id=budget_a.id,
        )

        assert [r.id for r in results] == [matching.id]

    async def test_budget_and_funder_fields_present_on_each_returned_report(self, db):
        budget = await _make_budget(
            db,
            funding_customer_id=FUNDER_ID,
        )
        budget.external_funder_name = "Acme Foundation"
        await db.commit()
        await _make_report(db, budget.id)

        [result] = await list_all_reports_service(db, _valid_user(OWNER_ID))

        assert result.budget_name == "Test Budget"
        assert result.budget_status == BudgetStatus.confirmed
        assert str(result.funding_customer_id) == FUNDER_ID
        assert result.external_funder_name == "Acme Foundation"


@pytest.mark.anyio
class TestListFundedReportsService:
    """GET /reports/funded/ — donor's cross-budget reports directory."""

    def _patched_customers(self, customers_map=None):
        return patch(
            "app.services.report_services.get_customers_by_ids",
            new_callable=AsyncMock,
            return_value=customers_map or {},
        )

    async def test_donor_sees_reports_across_all_budgets_they_fund(self, db):
        budget_a = await _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_b = await _make_budget(db, funding_customer_id=FUNDER_ID)
        unrelated_budget = await _make_budget(db)
        report_a = await _make_report(db, budget_a.id)
        report_b = await _make_report(
            db, budget_b.id, period_start=date(2026, 4, 1), period_end=date(2026, 6, 30)
        )
        await _make_report(db, unrelated_budget.id)

        with self._patched_customers():
            results = await list_funded_reports_service(db, _valid_user(FUNDER_ID))

        assert {r.id for r in results} == {report_a.id, report_b.id}

    async def test_grantee_does_not_see_reports_on_budgets_they_only_own(self, db):
        # Donor-scoped directory must not leak owner-visible reports.
        budget = await _make_budget(db, owner_id=OWNER_ID)
        await _make_report(db, budget.id)

        with self._patched_customers():
            results = await list_funded_reports_service(db, _valid_user(OWNER_ID))

        assert results == []

    async def test_stranger_sees_nothing(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        await _make_report(db, budget.id)

        with self._patched_customers():
            results = await list_funded_reports_service(db, _valid_user(STRANGER_ID))

        assert results == []

    async def test_status_filter(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        draft = await _make_report(db, budget.id, status=ReportStatus.draft)
        await _make_report(
            db,
            budget.id,
            status=ReportStatus.submitted,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 6, 30),
        )

        with self._patched_customers():
            results = await list_funded_reports_service(
                db, _valid_user(FUNDER_ID), status=ReportStatus.draft
            )

        assert [r.id for r in results] == [draft.id]

    async def test_budget_id_filter(self, db):
        budget_a = await _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_b = await _make_budget(db, funding_customer_id=FUNDER_ID)
        report_a = await _make_report(db, budget_a.id)
        await _make_report(
            db, budget_b.id, period_start=date(2026, 4, 1), period_end=date(2026, 6, 30)
        )

        with self._patched_customers():
            results = await list_funded_reports_service(
                db, _valid_user(FUNDER_ID), budget_id=budget_a.id
            )

        assert [r.id for r in results] == [report_a.id]

    async def test_owner_id_filter_narrows_to_one_grantee(self, db):
        grantee_a = str(uuid4())
        grantee_b = str(uuid4())
        budget_a = await _make_budget(db, owner_id=grantee_a, funding_customer_id=FUNDER_ID)
        budget_b = await _make_budget(db, owner_id=grantee_b, funding_customer_id=FUNDER_ID)
        report_a = await _make_report(db, budget_a.id)
        await _make_report(
            db, budget_b.id, period_start=date(2026, 4, 1), period_end=date(2026, 6, 30)
        )

        with self._patched_customers():
            results = await list_funded_reports_service(
                db, _valid_user(FUNDER_ID), owner_id=grantee_a
            )

        assert [r.id for r in results] == [report_a.id]

    async def test_budget_owner_and_funder_fields_present_with_resolved_owner_name(self, db):
        budget = await _make_budget(db, owner_id=OWNER_ID, funding_customer_id=FUNDER_ID)
        budget.external_funder_name = "Acme Foundation"
        await db.commit()
        await _make_report(db, budget.id)

        with self._patched_customers({OWNER_ID: {"name": "Hope Relief NGO"}}):
            [result] = await list_funded_reports_service(db, _valid_user(FUNDER_ID))

        assert result.budget_name == "Test Budget"
        assert result.budget_status == BudgetStatus.confirmed
        assert str(result.owner_id) == OWNER_ID
        assert result.owner_name == "Hope Relief NGO"
        assert result.external_funder_name == "Acme Foundation"

    async def test_owner_name_is_none_when_customers_service_fails(self, db):
        budget = await _make_budget(db, owner_id=OWNER_ID, funding_customer_id=FUNDER_ID)
        await _make_report(db, budget.id)

        with patch(
            "app.services.report_services.get_customers_by_ids",
            new_callable=AsyncMock,
            side_effect=Exception("customers service unavailable"),
        ):
            [result] = await list_funded_reports_service(db, _valid_user(FUNDER_ID))

        assert result.owner_name is None


@pytest.mark.anyio
class TestUpdateDeleteOwnership:
    async def test_funder_cannot_update_or_delete(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        report = await _make_report(db, budget.id)
        update = ReportUpdate(name="Renamed")

        with pytest.raises(PermissionDenied):
            await update_report_service(db, _valid_user(FUNDER_ID), report.id, update)
        with pytest.raises(PermissionDenied):
            await delete_report_service(db, _valid_user(FUNDER_ID), report.id)

    async def test_owner_can_update_and_delete_draft_report(self, db):
        budget = await _make_budget(db)
        report = await _make_report(db, budget.id)
        update = ReportUpdate(name="Renamed")

        updated = await update_report_service(db, _valid_user(OWNER_ID), report.id, update)
        assert updated.name == "Renamed"

        assert await delete_report_service(db, _valid_user(OWNER_ID), report.id) is True

    async def test_update_rejected_when_partial_period_would_invert(self, db):
        # Moving only period_start past the untouched period_end must be rejected.
        budget = await _make_budget(db)
        report = await _make_report(db, budget.id)
        update = ReportUpdate(period_start=date(2026, 4, 1))

        with pytest.raises(DomainError):
            await update_report_service(db, _valid_user(OWNER_ID), report.id, update)

    async def test_cannot_update_non_draft_report(self, db):
        budget = await _make_budget(db)
        report = await _make_report(db, budget.id, status=ReportStatus.submitted)
        update = ReportUpdate(name="Too late")

        with pytest.raises(DomainError):
            await update_report_service(db, _valid_user(OWNER_ID), report.id, update)

    async def test_cannot_delete_non_draft_report(self, db):
        budget = await _make_budget(db)
        report = await _make_report(db, budget.id, status=ReportStatus.submitted)

        with pytest.raises(DomainError):
            await delete_report_service(db, _valid_user(OWNER_ID), report.id)


@pytest.mark.anyio
class TestSubmitTransition:
    async def test_submit_draft_report(self, db):
        budget = await _make_budget(db)
        report = await _make_report(db, budget.id, status=ReportStatus.draft)

        result = await submit_report_service(db, _valid_user(OWNER_ID), report.id)

        assert result.status == ReportStatus.submitted
        assert result.submitted_at is not None

    async def test_cannot_resubmit_non_draft_report(self, db):
        budget = await _make_budget(db)
        report = await _make_report(db, budget.id, status=ReportStatus.submitted)

        with pytest.raises(DomainError):
            await submit_report_service(db, _valid_user(OWNER_ID), report.id)

    async def test_funder_cannot_submit(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        report = await _make_report(db, budget.id, status=ReportStatus.draft)

        with pytest.raises(PermissionDenied):
            await submit_report_service(db, _valid_user(FUNDER_ID), report.id)


@pytest.mark.anyio
class TestReviewTransition:
    async def test_funder_approves_submitted_report(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        report = await _make_report(db, budget.id, status=ReportStatus.submitted)
        funder_user = _valid_user(FUNDER_ID)

        result = await review_report_service(db, funder_user, report.id, ReportStatus.approved)

        assert result.status == ReportStatus.approved
        assert result.reviewed_at is not None
        assert str(result.reviewed_by) == funder_user["user_id"]

    async def test_funder_rejects_with_notes(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        report = await _make_report(db, budget.id, status=ReportStatus.submitted)

        result = await review_report_service(
            db, _valid_user(FUNDER_ID), report.id, ReportStatus.rejected, "please fix the totals"
        )

        assert result.status == ReportStatus.rejected
        assert result.review_notes == "please fix the totals"

    async def test_owner_self_reviews_when_no_funder(self, db):
        budget = await _make_budget(db, funding_customer_id=None)
        report = await _make_report(db, budget.id, status=ReportStatus.submitted)

        result = await review_report_service(
            db, _valid_user(OWNER_ID), report.id, ReportStatus.approved
        )

        assert result.status == ReportStatus.approved

    async def test_owner_cannot_review_when_a_real_funder_exists(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        report = await _make_report(db, budget.id, status=ReportStatus.submitted)

        with pytest.raises(PermissionDenied):
            await review_report_service(db, _valid_user(OWNER_ID), report.id, ReportStatus.approved)

    async def test_stranger_cannot_review(self, db):
        # No view access to the budget hits the info-hiding not-found path.
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        report = await _make_report(db, budget.id, status=ReportStatus.submitted)

        with pytest.raises(DomainError):
            await review_report_service(
                db, _valid_user(STRANGER_ID), report.id, ReportStatus.approved
            )

    async def test_cannot_review_non_submitted_report(self, db):
        budget = await _make_budget(db, funding_customer_id=FUNDER_ID)
        report = await _make_report(db, budget.id, status=ReportStatus.draft)

        with pytest.raises(DomainError):
            await review_report_service(
                db, _valid_user(FUNDER_ID), report.id, ReportStatus.approved
            )


@pytest.mark.anyio
class TestReopenTransition:
    async def test_reopen_rejected_report_to_draft(self, db):
        budget = await _make_budget(db)
        report = await _make_report(db, budget.id, status=ReportStatus.rejected)

        result = await reopen_report_service(db, _valid_user(OWNER_ID), report.id)

        assert result.status == ReportStatus.draft

    async def test_cannot_reopen_non_rejected_report(self, db):
        budget = await _make_budget(db)
        report = await _make_report(db, budget.id, status=ReportStatus.draft)

        with pytest.raises(DomainError):
            await reopen_report_service(db, _valid_user(OWNER_ID), report.id)


class TestReportRoutesWiring:
    """Thin route-level checks with the service layer mocked, matching
    test_donor_scoped_endpoints.py's convention."""

    def test_create_report_route_delegates_to_service(self, make_client):
        client = make_client()
        with patch(
            "app.api.report_routes.create_report_service",
            return_value=SimpleNamespace(id=uuid4()),
        ) as mock_service:
            response = client.post(
                "/api/v1/reports/",
                json={"budget_id": str(uuid4()), "name": "Report"},
            )
        assert response.status_code == 200
        mock_service.assert_called_once()

    def test_create_report_route_sets_span_attributes(self, make_client):
        client = make_client()
        budget_id = uuid4()
        report_id = uuid4()
        with (
            patch(
                "app.api.report_routes.create_report_service",
                return_value=SimpleNamespace(id=report_id),
            ),
            patch("app.api.report_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.post(
                "/api/v1/reports/",
                json={"budget_id": str(budget_id), "name": "Report"},
            )
        mock_set_span_attrs.assert_any_call(budget_id=budget_id)
        mock_set_span_attrs.assert_any_call(report_id=report_id)

    def test_update_report_route_sets_report_id_span_attribute(self, make_client):
        client = make_client()
        report_id = uuid4()
        with (
            patch(
                "app.api.report_routes.update_report_service",
                return_value={"id": str(report_id)},
            ),
            patch("app.api.report_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.patch(f"/api/v1/reports/{report_id}", json={"name": "Renamed"})
        mock_set_span_attrs.assert_any_call(report_id=report_id)

    def test_get_report_route_sets_report_id_span_attribute(self, make_client):
        client = make_client()
        report_id = uuid4()
        with (
            patch(
                "app.api.report_routes.get_report_service",
                return_value={"id": str(report_id)},
            ),
            patch("app.api.report_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.get(f"/api/v1/reports/{report_id}")
        mock_set_span_attrs.assert_any_call(report_id=report_id)

    def test_list_reports_by_budget_route_sets_budget_id_span_attribute(self, make_client):
        client = make_client()
        budget_id = uuid4()
        with (
            patch("app.api.report_routes.list_reports_service", return_value=[]),
            patch("app.api.report_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.get(f"/api/v1/reports/by-budget/{budget_id}")
        mock_set_span_attrs.assert_any_call(budget_id=budget_id)

    def test_submit_report_route_delegates_to_service(self, make_client):
        client = make_client()
        report_id = uuid4()
        with patch(
            "app.api.report_routes.submit_report_service", return_value={"id": str(report_id)}
        ) as mock_service:
            response = client.post(f"/api/v1/reports/{report_id}/submit")
        assert response.status_code == 200
        mock_service.assert_called_once()

    def test_list_all_reports_route_delegates_to_service(self, make_client):
        client = make_client()
        with patch(
            "app.api.report_routes.list_all_reports_service", return_value=[]
        ) as mock_service:
            response = client.get(
                "/api/v1/reports/",
                params={"status": "draft", "budget_id": str(uuid4())},
            )
        assert response.status_code == 200
        assert response.json() == []
        mock_service.assert_called_once()

    def test_list_funded_reports_route_delegates_to_service(self, make_client):
        client = make_client(is_donor=True)
        with patch(
            "app.api.report_routes.list_funded_reports_service",
            AsyncMock(return_value=[]),
        ) as mock_service:
            response = client.get(
                "/api/v1/reports/funded/",
                params={"status": "draft", "budget_id": str(uuid4())},
            )
        assert response.status_code == 200
        assert response.json() == []
        mock_service.assert_called_once()

    def test_list_funded_reports_route_rejects_non_donor(self, make_client):
        client = make_client(is_donor=False)
        response = client.get("/api/v1/reports/funded/")
        assert response.status_code == 403

    def test_review_report_route_delegates_to_service(self, make_client):
        client = make_client()
        report_id = uuid4()
        with patch(
            "app.api.report_routes.review_report_service", return_value={"id": str(report_id)}
        ) as mock_service:
            response = client.post(
                f"/api/v1/reports/{report_id}/review",
                json={"decision": "approved"},
            )
        assert response.status_code == 200
        mock_service.assert_called_once()
