import pytest

from app.crud.budget_crud import create_budget
from tests.factories.user import ValidUserFactory


@pytest.mark.anyio
class TestCreateBudget:
    async def test_omitted_fields_use_model_defaults(self, db):
        user = ValidUserFactory()

        budget = create_budget(
            session=db, user_id=user["user_id"], name="No extras", owner_id=user["customer_id"]
        )

        assert budget.local_currency == "GBP"
        assert budget.duration_months == 0

    async def test_provided_fields_are_persisted(self, db):
        user = ValidUserFactory()

        budget = create_budget(
            session=db,
            user_id=user["user_id"],
            name="With extras",
            owner_id=user["customer_id"],
            local_currency="EUR",
            actual_currency="NOK",
            duration_months=12,
            donor_total_amount=5000.0,
            estimated_exchange_rate=1.1,
        )

        assert budget.local_currency == "EUR"
        assert budget.actual_currency == "NOK"
        assert budget.duration_months == 12
        assert budget.donor_total_amount == 5000.0
        assert budget.estimated_exchange_rate == 1.1
