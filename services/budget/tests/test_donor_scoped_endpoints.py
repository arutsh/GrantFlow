"""
Tests for the donor-scoped /budgets/funded/* endpoints (ticket #139).

Route-level tests mock the service layer (matching this service's existing
convention — see test_budget_routes.py) and cover the require_donor gate.
Crud-level tests hit a real sqlite session to verify the aggregation SQL
itself, including that a budget funded by a different donor is excluded.
"""

import uuid
from unittest.mock import AsyncMock, patch

CUSTOMER_ID = str(uuid.uuid4())


class TestFundedBudgetsSummaryEndpoint:
    def test_donor_with_data(self, make_client):
        client = make_client(customer_id=CUSTOMER_ID, is_donor=True)
        with patch(
            "app.api.budget_routes.get_funded_budgets_summary_service",
            return_value={
                "total_budgets": 3,
                "total_allocated_by_currency": [{"currency": "GBP", "total_allocated": 4500.0}],
            },
        ):
            response = client.get("/api/v1/budgets/funded/summary")

        assert response.status_code == 200
        assert response.json() == {
            "total_budgets": 3,
            "total_allocated_by_currency": [{"currency": "GBP", "total_allocated": 4500.0}],
        }

    def test_donor_with_zero_funded_budgets(self, make_client):
        client = make_client(customer_id=CUSTOMER_ID, is_donor=True)
        with patch(
            "app.api.budget_routes.get_funded_budgets_summary_service",
            return_value={"total_budgets": 0, "total_allocated_by_currency": []},
        ):
            response = client.get("/api/v1/budgets/funded/summary")

        assert response.status_code == 200
        assert response.json() == {
            "total_budgets": 0,
            "total_allocated_by_currency": [],
        }

    def test_non_donor_gets_403(self, make_client):
        client = make_client(customer_id=CUSTOMER_ID, is_donor=False)
        response = client.get("/api/v1/budgets/funded/summary")

        assert response.status_code == 403


class TestFundedGranteesEndpoint:
    def test_donor_with_data(self, make_client):
        client = make_client(customer_id=CUSTOMER_ID, is_donor=True)
        grantee_id = str(uuid.uuid4())
        with patch(
            "app.api.budget_routes.get_funded_grantees_service",
            AsyncMock(
                return_value=[
                    {
                        "id": grantee_id,
                        "name": "Test NGO",
                        "country": "KE",
                        "budgets_count": 2,
                        "total_allocated_by_currency": [
                            {"currency": "GBP", "total_allocated": 1500.0}
                        ],
                    }
                ]
            ),
        ):
            response = client.get("/api/v1/budgets/funded/grantees")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["name"] == "Test NGO"
        assert body[0]["budgets_count"] == 2

    def test_non_donor_gets_403(self, make_client):
        client = make_client(customer_id=CUSTOMER_ID, is_donor=False)
        response = client.get("/api/v1/budgets/funded/grantees")

        assert response.status_code == 403


class TestFundedBudgetsListEndpoint:
    def test_donor_with_data(self, make_client):
        client = make_client(customer_id=CUSTOMER_ID, is_donor=True)
        budget_id = str(uuid.uuid4())
        with patch(
            "app.api.budget_routes.get_funded_budgets_service",
            AsyncMock(
                return_value=[
                    {
                        "id": budget_id,
                        "name": "Clean Water Project",
                        "status": "confirmed",
                        "total_amount": 2000.0,
                        "owner": {"id": str(uuid.uuid4()), "name": "Test NGO"},
                    }
                ]
            ),
        ):
            response = client.get("/api/v1/budgets/funded/")

        assert response.status_code == 200
        body = response.json()
        assert body[0]["owner"]["name"] == "Test NGO"
        assert body[0]["total_amount"] == 2000.0

    def test_non_donor_gets_403(self, make_client):
        client = make_client(customer_id=CUSTOMER_ID, is_donor=False)
        response = client.get("/api/v1/budgets/funded/")

        assert response.status_code == 403


def _sqlite_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import Base
    from app.models.budget import BudgetModel, BudgetLineModel

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[BudgetModel.__table__, BudgetLineModel.__table__])
    return sessionmaker(bind=engine)()


class TestFundedBudgetsCrud:
    """Direct coverage of the new aggregation queries, against a real sqlite session."""

    def test_summary_totals_only_this_donors_budgets(self):
        from app.models.budget import BudgetModel
        from app.crud.budget_crud import get_funded_budgets_summary

        session = _sqlite_session()
        donor_id = uuid.uuid4()
        other_donor_id = uuid.uuid4()

        for budget in (
            BudgetModel(
                name="A", owner_id=uuid.uuid4(), funding_customer_id=donor_id, total_amount=1000.0
            ),
            BudgetModel(
                name="B", owner_id=uuid.uuid4(), funding_customer_id=donor_id, total_amount=500.0
            ),
            BudgetModel(
                name="C",
                owner_id=uuid.uuid4(),
                funding_customer_id=other_donor_id,
                total_amount=9999.0,
            ),
        ):
            # Committed one at a time: BudgetModel.id's default returns a str,
            # not a uuid.UUID (unlike sibling models), which trips SQLAlchemy's
            # batched-insert sentinel matching when >1 row flushes at once.
            session.add(budget)
            session.commit()

        summary = get_funded_budgets_summary(session, donor_id)

        assert summary == {
            "total_budgets": 2,
            "total_allocated_by_currency": [{"currency": "GBP", "total_allocated": 1500.0}],
        }

    def test_summary_zero_for_donor_with_no_funded_budgets(self):
        from app.crud.budget_crud import get_funded_budgets_summary

        session = _sqlite_session()
        summary = get_funded_budgets_summary(session, uuid.uuid4())

        assert summary == {
            "total_budgets": 0,
            "total_allocated_by_currency": [],
        }

    def test_summary_keeps_currencies_separate_not_blended(self):
        """A donor funding budgets in different currencies must not get one
        blended sum mislabeled with an arbitrary currency (see #139 review)."""
        from app.models.budget import BudgetModel
        from app.crud.budget_crud import get_funded_budgets_summary

        session = _sqlite_session()
        donor_id = uuid.uuid4()

        for budget in (
            BudgetModel(
                name="A",
                owner_id=uuid.uuid4(),
                funding_customer_id=donor_id,
                total_amount=3000.0,
                local_currency="GBP",
            ),
            BudgetModel(
                name="B",
                owner_id=uuid.uuid4(),
                funding_customer_id=donor_id,
                total_amount=5000.0,
                local_currency="USD",
            ),
        ):
            session.add(budget)
            session.commit()

        summary = get_funded_budgets_summary(session, donor_id)

        assert summary["total_budgets"] == 2
        by_currency = {
            c["currency"]: c["total_allocated"] for c in summary["total_allocated_by_currency"]
        }
        assert by_currency == {"GBP": 3000.0, "USD": 5000.0}

    def test_grantees_groups_by_owner_across_multiple_budgets(self):
        from app.models.budget import BudgetModel
        from app.crud.budget_crud import get_funded_grantees

        session = _sqlite_session()
        donor_id = uuid.uuid4()
        grantee_id = uuid.uuid4()
        other_grantee_id = uuid.uuid4()

        for budget in (
            BudgetModel(
                name="A", owner_id=grantee_id, funding_customer_id=donor_id, total_amount=100.0
            ),
            BudgetModel(
                name="B", owner_id=grantee_id, funding_customer_id=donor_id, total_amount=200.0
            ),
            BudgetModel(
                name="C", owner_id=grantee_id, funding_customer_id=donor_id, total_amount=300.0
            ),
            BudgetModel(
                name="D", owner_id=other_grantee_id, funding_customer_id=donor_id, total_amount=50.0
            ),
        ):
            session.add(budget)
            session.commit()

        grantees = get_funded_grantees(session, donor_id)
        by_owner = {g["owner_id"]: g for g in grantees}

        assert by_owner[grantee_id]["budgets_count"] == 3
        assert by_owner[grantee_id]["total_allocated_by_currency"] == [
            {"currency": "GBP", "total_allocated": 600.0}
        ]
        assert by_owner[other_grantee_id]["budgets_count"] == 1
        assert by_owner[other_grantee_id]["total_allocated_by_currency"] == [
            {"currency": "GBP", "total_allocated": 50.0}
        ]

    def test_grantees_keeps_currencies_separate_not_blended(self):
        """Same grantee funded via budgets in two different currencies must not
        be blended into one mislabeled sum (see #139 review)."""
        from app.models.budget import BudgetModel
        from app.crud.budget_crud import get_funded_grantees

        session = _sqlite_session()
        donor_id = uuid.uuid4()
        grantee_id = uuid.uuid4()

        for budget in (
            BudgetModel(
                name="A",
                owner_id=grantee_id,
                funding_customer_id=donor_id,
                total_amount=3000.0,
                local_currency="GBP",
            ),
            BudgetModel(
                name="B",
                owner_id=grantee_id,
                funding_customer_id=donor_id,
                total_amount=5000.0,
                local_currency="USD",
            ),
        ):
            session.add(budget)
            session.commit()

        grantees = get_funded_grantees(session, donor_id)
        assert len(grantees) == 1
        grantee = grantees[0]
        assert grantee["budgets_count"] == 2
        by_currency = {
            c["currency"]: c["total_allocated"] for c in grantee["total_allocated_by_currency"]
        }
        assert by_currency == {"GBP": 3000.0, "USD": 5000.0}

    def test_list_budgets_funding_filter_excludes_other_donors(self):
        from app.models.budget import BudgetModel
        from app.crud.budget_crud import list_budgets

        session = _sqlite_session()
        donor_id = uuid.uuid4()
        other_donor_id = uuid.uuid4()

        mine = BudgetModel(name="Mine", owner_id=uuid.uuid4(), funding_customer_id=donor_id)
        theirs = BudgetModel(
            name="Theirs", owner_id=uuid.uuid4(), funding_customer_id=other_donor_id
        )
        session.add(mine)
        session.commit()
        session.add(theirs)
        session.commit()

        results = list_budgets(session, funding_customer_id=donor_id)

        assert [b.name for b in results] == ["Mine"]
