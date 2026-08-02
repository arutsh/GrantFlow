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
from unittest.mock import patch
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


def _make_budget(
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
    db.commit()
    db.refresh(budget)
    return budget


def _make_report(db, budget_id, status=ReportStatus.draft, period_start=None, period_end=None):
    report = ReportModel(
        budget_id=budget_id,
        name="Interim report",
        status=status,
        period_start=period_start or date(2026, 1, 1),
        period_end=period_end or date(2026, 3, 31),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


class TestCreateReportService:
    def test_defaults_period_to_budget_full_span_when_omitted(self, db):
        budget = _make_budget(db)
        payload = ReportCreate(budget_id=budget.id, name="Final report")

        result = create_report_service(db, _valid_user(OWNER_ID), payload)

        assert result.period_start == budget.start_date
        assert result.period_end == budget.start_date + relativedelta(months=12)
        assert result.status == ReportStatus.draft

    def test_creates_with_explicit_narrower_period(self, db):
        budget = _make_budget(db)
        payload = ReportCreate(
            budget_id=budget.id,
            name="Q1 report",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        )

        result = create_report_service(db, _valid_user(OWNER_ID), payload)

        assert result.period_start == date(2026, 1, 1)
        assert result.period_end == date(2026, 3, 31)

    def test_rejected_when_only_period_start_supplied(self, db):
        # Regression: previously silently discarded the supplied period_start
        # and defaulted both fields to the budget's full span instead of
        # rejecting the ambiguous partial input ("period-stomping").
        budget = _make_budget(db)
        payload = ReportCreate(budget_id=budget.id, name="Partial", period_start=date(2026, 2, 1))

        with pytest.raises(DomainError):
            create_report_service(db, _valid_user(OWNER_ID), payload)

    def test_rejected_when_only_period_end_supplied(self, db):
        budget = _make_budget(db)
        payload = ReportCreate(budget_id=budget.id, name="Partial", period_end=date(2026, 2, 1))

        with pytest.raises(DomainError):
            create_report_service(db, _valid_user(OWNER_ID), payload)

    def test_rejected_when_period_is_inverted(self, db):
        budget = _make_budget(db)
        payload = ReportCreate(
            budget_id=budget.id,
            name="Inverted",
            period_start=date(2026, 6, 1),
            period_end=date(2026, 1, 1),
        )

        with pytest.raises(DomainError):
            create_report_service(db, _valid_user(OWNER_ID), payload)

    def test_rejected_when_budget_not_confirmed(self, db):
        budget = _make_budget(db, status=BudgetStatus.draft)
        payload = ReportCreate(budget_id=budget.id, name="Too early")

        with pytest.raises(DomainError):
            create_report_service(db, _valid_user(OWNER_ID), payload)

    def test_rejected_when_confirmed_budget_has_no_start_date(self, db):
        # update_budget_service enforces start_date before confirming a budget,
        # but this guards a hypothetical future path that sets confirmed directly.
        budget = _make_budget(db, start_date=None)
        payload = ReportCreate(budget_id=budget.id, name="No start date")

        with pytest.raises(DomainError):
            create_report_service(db, _valid_user(OWNER_ID), payload)

    def test_rejected_for_user_without_budget_access(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        payload = ReportCreate(budget_id=budget.id, name="Not yours")

        with pytest.raises(DomainError):
            create_report_service(db, _valid_user(STRANGER_ID), payload)

    def test_funder_has_access_to_create(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        payload = ReportCreate(budget_id=budget.id, name="Funder-created")

        result = create_report_service(db, _valid_user(FUNDER_ID), payload)

        assert result.budget_id == budget.id

    def test_rejected_on_period_overlap_including_against_rejected_report(self, db):
        budget = _make_budget(db)
        _make_report(
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
            create_report_service(db, _valid_user(OWNER_ID), payload)

    def test_non_overlapping_period_allowed_regardless_of_existing_status(self, db):
        budget = _make_budget(db)
        _make_report(
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

        result = create_report_service(db, _valid_user(OWNER_ID), payload)

        assert result.period_start == date(2026, 7, 1)


class TestReportAccess:
    def test_owner_can_get_and_list(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        report = _make_report(db, budget.id)

        assert get_report_service(db, _valid_user(OWNER_ID), report.id).id == report.id
        assert len(list_reports_service(db, _valid_user(OWNER_ID), budget.id)) == 1

    def test_funder_can_get_and_list(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        report = _make_report(db, budget.id)

        assert get_report_service(db, _valid_user(FUNDER_ID), report.id).id == report.id
        assert len(list_reports_service(db, _valid_user(FUNDER_ID), budget.id)) == 1

    def test_stranger_cannot_get_or_list(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        report = _make_report(db, budget.id)

        with pytest.raises(DomainError):
            get_report_service(db, _valid_user(STRANGER_ID), report.id)
        with pytest.raises(DomainError):
            list_reports_service(db, _valid_user(STRANGER_ID), budget.id)


class TestListAllReportsService:
    """GET /reports/ — cross-budget reports directory (ticket #182)."""

    def test_owner_sees_reports_across_all_their_budgets(self, db):
        budget_a = _make_budget(db)
        budget_b = _make_budget(db)
        other_owner_budget = _make_budget(db, owner_id=STRANGER_ID)
        report_a = _make_report(db, budget_a.id)
        report_b = _make_report(
            db, budget_b.id, period_start=date(2026, 4, 1), period_end=date(2026, 6, 30)
        )
        _make_report(db, other_owner_budget.id)

        results = list_all_reports_service(db, _valid_user(OWNER_ID))

        assert {r.id for r in results} == {report_a.id, report_b.id}

    def test_donor_sees_reports_across_all_budgets_they_fund(self, db):
        budget_a = _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_b = _make_budget(db, funding_customer_id=FUNDER_ID)
        unrelated_budget = _make_budget(db)
        report_a = _make_report(db, budget_a.id)
        report_b = _make_report(
            db, budget_b.id, period_start=date(2026, 4, 1), period_end=date(2026, 6, 30)
        )
        _make_report(db, unrelated_budget.id)

        results = list_all_reports_service(db, _valid_user(FUNDER_ID))

        assert {r.id for r in results} == {report_a.id, report_b.id}

    def test_stranger_sees_nothing(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        _make_report(db, budget.id)

        assert list_all_reports_service(db, _valid_user(STRANGER_ID)) == []

    def test_status_filter(self, db):
        budget = _make_budget(db)
        draft = _make_report(db, budget.id, status=ReportStatus.draft)
        _make_report(
            db,
            budget.id,
            status=ReportStatus.submitted,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 6, 30),
        )

        results = list_all_reports_service(db, _valid_user(OWNER_ID), status=ReportStatus.draft)

        assert [r.id for r in results] == [draft.id]

    def test_budget_id_filter(self, db):
        budget_a = _make_budget(db)
        budget_b = _make_budget(db)
        report_a = _make_report(db, budget_a.id)
        _make_report(db, budget_b.id, period_start=date(2026, 4, 1), period_end=date(2026, 6, 30))

        results = list_all_reports_service(db, _valid_user(OWNER_ID), budget_id=budget_a.id)

        assert [r.id for r in results] == [report_a.id]

    def test_funding_customer_id_filter(self, db):
        funded_budget = _make_budget(db, owner_id=OWNER_ID, funding_customer_id=FUNDER_ID)
        unfunded_budget = _make_budget(db, owner_id=OWNER_ID)
        funded_report = _make_report(db, funded_budget.id)
        _make_report(
            db,
            unfunded_budget.id,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 6, 30),
        )

        results = list_all_reports_service(db, _valid_user(OWNER_ID), funding_customer_id=FUNDER_ID)

        assert [r.id for r in results] == [funded_report.id]

    def test_filters_combine(self, db):
        budget_a = _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_b = _make_budget(db, funding_customer_id=FUNDER_ID)
        matching = _make_report(db, budget_a.id, status=ReportStatus.draft)
        _make_report(
            db,
            budget_a.id,
            status=ReportStatus.submitted,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 6, 30),
        )
        _make_report(db, budget_b.id, status=ReportStatus.draft)

        results = list_all_reports_service(
            db,
            _valid_user(FUNDER_ID),
            status=ReportStatus.draft,
            budget_id=budget_a.id,
        )

        assert [r.id for r in results] == [matching.id]

    def test_budget_and_funder_fields_present_on_each_returned_report(self, db):
        budget = _make_budget(
            db,
            funding_customer_id=FUNDER_ID,
        )
        budget.external_funder_name = "Acme Foundation"
        db.commit()
        _make_report(db, budget.id)

        [result] = list_all_reports_service(db, _valid_user(OWNER_ID))

        assert result.budget_name == "Test Budget"
        assert result.budget_status == BudgetStatus.confirmed
        assert str(result.funding_customer_id) == FUNDER_ID
        assert result.external_funder_name == "Acme Foundation"


class TestUpdateDeleteOwnership:
    def test_funder_cannot_update_or_delete(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        report = _make_report(db, budget.id)
        update = ReportUpdate(name="Renamed")

        with pytest.raises(PermissionDenied):
            update_report_service(db, _valid_user(FUNDER_ID), report.id, update)
        with pytest.raises(PermissionDenied):
            delete_report_service(db, _valid_user(FUNDER_ID), report.id)

    def test_owner_can_update_and_delete_draft_report(self, db):
        budget = _make_budget(db)
        report = _make_report(db, budget.id)
        update = ReportUpdate(name="Renamed")

        updated = update_report_service(db, _valid_user(OWNER_ID), report.id, update)
        assert updated.name == "Renamed"

        assert delete_report_service(db, _valid_user(OWNER_ID), report.id) is True

    def test_update_rejected_when_partial_period_would_invert(self, db):
        # Regression: report starts at period_start=Jan1/period_end=Mar31
        # (see _make_report). Moving only period_start past the existing,
        # untouched period_end used to save silently with no ordering check.
        budget = _make_budget(db)
        report = _make_report(db, budget.id)
        update = ReportUpdate(period_start=date(2026, 4, 1))

        with pytest.raises(DomainError):
            update_report_service(db, _valid_user(OWNER_ID), report.id, update)

    def test_cannot_update_non_draft_report(self, db):
        budget = _make_budget(db)
        report = _make_report(db, budget.id, status=ReportStatus.submitted)
        update = ReportUpdate(name="Too late")

        with pytest.raises(DomainError):
            update_report_service(db, _valid_user(OWNER_ID), report.id, update)

    def test_cannot_delete_non_draft_report(self, db):
        budget = _make_budget(db)
        report = _make_report(db, budget.id, status=ReportStatus.submitted)

        with pytest.raises(DomainError):
            delete_report_service(db, _valid_user(OWNER_ID), report.id)


class TestSubmitTransition:
    def test_submit_draft_report(self, db):
        budget = _make_budget(db)
        report = _make_report(db, budget.id, status=ReportStatus.draft)

        result = submit_report_service(db, _valid_user(OWNER_ID), report.id)

        assert result.status == ReportStatus.submitted
        assert result.submitted_at is not None

    def test_cannot_resubmit_non_draft_report(self, db):
        budget = _make_budget(db)
        report = _make_report(db, budget.id, status=ReportStatus.submitted)

        with pytest.raises(DomainError):
            submit_report_service(db, _valid_user(OWNER_ID), report.id)

    def test_funder_cannot_submit(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        report = _make_report(db, budget.id, status=ReportStatus.draft)

        with pytest.raises(PermissionDenied):
            submit_report_service(db, _valid_user(FUNDER_ID), report.id)


class TestReviewTransition:
    def test_funder_approves_submitted_report(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        report = _make_report(db, budget.id, status=ReportStatus.submitted)
        funder_user = _valid_user(FUNDER_ID)

        result = review_report_service(db, funder_user, report.id, ReportStatus.approved)

        assert result.status == ReportStatus.approved
        assert result.reviewed_at is not None
        assert str(result.reviewed_by) == funder_user["user_id"]

    def test_funder_rejects_with_notes(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        report = _make_report(db, budget.id, status=ReportStatus.submitted)

        result = review_report_service(
            db, _valid_user(FUNDER_ID), report.id, ReportStatus.rejected, "please fix the totals"
        )

        assert result.status == ReportStatus.rejected
        assert result.review_notes == "please fix the totals"

    def test_owner_self_reviews_when_no_funder(self, db):
        budget = _make_budget(db, funding_customer_id=None)
        report = _make_report(db, budget.id, status=ReportStatus.submitted)

        result = review_report_service(db, _valid_user(OWNER_ID), report.id, ReportStatus.approved)

        assert result.status == ReportStatus.approved

    def test_owner_cannot_review_when_a_real_funder_exists(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        report = _make_report(db, budget.id, status=ReportStatus.submitted)

        with pytest.raises(PermissionDenied):
            review_report_service(db, _valid_user(OWNER_ID), report.id, ReportStatus.approved)

    def test_stranger_cannot_review(self, db):
        # A stranger has no view access to the budget at all, so this hits the
        # same info-hiding "not found" path as every other report endpoint —
        # not PermissionDenied, which would confirm the report exists.
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        report = _make_report(db, budget.id, status=ReportStatus.submitted)

        with pytest.raises(DomainError):
            review_report_service(db, _valid_user(STRANGER_ID), report.id, ReportStatus.approved)

    def test_cannot_review_non_submitted_report(self, db):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        report = _make_report(db, budget.id, status=ReportStatus.draft)

        with pytest.raises(DomainError):
            review_report_service(db, _valid_user(FUNDER_ID), report.id, ReportStatus.approved)


class TestReopenTransition:
    def test_reopen_rejected_report_to_draft(self, db):
        budget = _make_budget(db)
        report = _make_report(db, budget.id, status=ReportStatus.rejected)

        result = reopen_report_service(db, _valid_user(OWNER_ID), report.id)

        assert result.status == ReportStatus.draft

    def test_cannot_reopen_non_rejected_report(self, db):
        budget = _make_budget(db)
        report = _make_report(db, budget.id, status=ReportStatus.draft)

        with pytest.raises(DomainError):
            reopen_report_service(db, _valid_user(OWNER_ID), report.id)


class TestReportRoutesWiring:
    """Thin route-level checks with the service layer mocked, matching
    test_donor_scoped_endpoints.py's convention."""

    def test_create_report_route_delegates_to_service(self, make_client):
        client = make_client()
        with patch(
            "app.api.report_routes.create_report_service", return_value={"id": str(uuid4())}
        ) as mock_service:
            response = client.post(
                "/api/v1/reports/",
                json={"budget_id": str(uuid4()), "name": "Report"},
            )
        assert response.status_code == 200
        mock_service.assert_called_once()

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
