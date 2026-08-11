"""Tests for the by-creator crud lookups added for the data-subject-rights
data export (gdpr-iso27001-priority-1) — the users service calls the
corresponding self-service-only endpoints (GET /budgets/by-creator/{user_id}
and /reports/by-creator/{user_id}, forwarding the requesting user's own
token) to list a user's financial records.
"""

from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from app.crud.budget_crud import get_budgets_by_creator
from app.crud.report_crud import get_reports_by_creator
from shared.security.dependencies import get_validated_user
from tests.factories.budget import BudgetFactory
from tests.factories.report import ReportFactory

client = TestClient(app)


class TestGetBudgetsByCreator:
    def test_returns_only_that_users_budgets(self, db):
        creator_id = uuid4()
        other_id = uuid4()
        mine = BudgetFactory.build(created_by=creator_id)
        theirs = BudgetFactory.build(created_by=other_id)
        db.add_all([mine, theirs])
        db.commit()

        result = get_budgets_by_creator(db, creator_id)

        assert [b.id for b in result] == [mine.id]

    def test_no_budgets_returns_empty_list(self, db):
        assert get_budgets_by_creator(db, uuid4()) == []


class TestGetReportsByCreator:
    def test_returns_only_that_users_reports(self, db):
        creator_id = uuid4()
        other_id = uuid4()
        budget = BudgetFactory.build(created_by=creator_id)
        db.add(budget)
        db.commit()

        mine = ReportFactory.build(budget_id=budget.id, created_by=creator_id)
        theirs = ReportFactory.build(budget_id=budget.id, created_by=other_id)
        db.add_all([mine, theirs])
        db.commit()

        result = get_reports_by_creator(db, creator_id)

        assert [r.id for r in result] == [mine.id]


class TestByCreatorEndpointsAreSelfServiceOnly:
    """These endpoints sit on the same public router as every other
    /budgets and /reports route, with no gateway-level path exclusion —
    unlike /customers/by_ids/, they can't rely on a "trusted internal
    caller" convention, so they must reject anyone but the token's own
    subject themselves."""

    def test_budgets_by_creator_requires_auth(self):
        response = client.get(f"/api/v1/budgets/by-creator/{uuid4()}")
        assert response.status_code == 401

    def test_budgets_by_creator_allows_self(self):
        user_id = str(uuid4())
        app.dependency_overrides[get_validated_user] = lambda: {"user_id": user_id}
        try:
            with patch("app.api.budget_routes.get_budgets_by_creator", return_value=[]):
                response = client.get(f"/api/v1/budgets/by-creator/{user_id}")
        finally:
            app.dependency_overrides = {}
        assert response.status_code == 200

    def test_budgets_by_creator_rejects_other_user(self):
        app.dependency_overrides[get_validated_user] = lambda: {"user_id": str(uuid4())}
        try:
            response = client.get(f"/api/v1/budgets/by-creator/{uuid4()}")
        finally:
            app.dependency_overrides = {}
        assert response.status_code == 403

    def test_reports_by_creator_requires_auth(self):
        response = client.get(f"/api/v1/reports/by-creator/{uuid4()}")
        assert response.status_code == 401

    def test_reports_by_creator_allows_self(self):
        user_id = str(uuid4())
        app.dependency_overrides[get_validated_user] = lambda: {"user_id": user_id}
        try:
            with patch("app.api.report_routes.get_reports_by_creator", return_value=[]):
                response = client.get(f"/api/v1/reports/by-creator/{user_id}")
        finally:
            app.dependency_overrides = {}
        assert response.status_code == 200

    def test_reports_by_creator_rejects_other_user(self):
        app.dependency_overrides[get_validated_user] = lambda: {"user_id": str(uuid4())}
        try:
            response = client.get(f"/api/v1/reports/by-creator/{uuid4()}")
        finally:
            app.dependency_overrides = {}
        assert response.status_code == 403
