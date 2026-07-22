from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.budget import BudgetModel, BudgetLineModel, BudgetStatus
from uuid import UUID


def create_budget(
    session: Session,
    user_id: UUID,
    name: str,
    funding_customer_id: UUID | None = None,
    external_funder_name: str | None = None,
    owner_id: UUID | None = None,
    status: BudgetStatus | None = None,
) -> BudgetModel:
    budget = BudgetModel(
        name=name,
        owner_id=owner_id,
        funding_customer_id=funding_customer_id,
        external_funder_name=external_funder_name,
        created_by=user_id,
        updated_by=user_id,
        status=status or BudgetStatus.draft,
    )
    session.add(budget)
    session.commit()
    session.refresh(budget)
    return budget


def get_budget(
    session: Session, budget_id: UUID, customer_id: UUID | None = None
) -> BudgetModel | None:
    query = session.query(BudgetModel)
    if customer_id:
        return query.filter(
            BudgetModel.id == budget_id, BudgetModel.owner_id == customer_id
        ).first()
    return query.filter(BudgetModel.id == budget_id).first()


def list_budgets(
    session: Session,
    customer_id: UUID | None = None,
    funding_customer_id: UUID | None = None,
    limit: int = 100,
):
    query = session.query(BudgetModel)
    if customer_id:
        query = query.filter(BudgetModel.owner_id == customer_id)
    if funding_customer_id:
        query = query.filter(BudgetModel.funding_customer_id == funding_customer_id)
    return query.limit(limit).all()


def update_budget_name(session: Session, budget_id: UUID, new_name: str) -> BudgetModel | None:
    budget = get_budget(session, budget_id)
    if not budget:
        return None
    budget.name = new_name
    session.commit()
    session.refresh(budget)
    return budget


def update_budget(
    session: Session,
    budget_id: UUID,
    name: str | None = None,
    owner_id: UUID | None = None,
    funding_customer_id: UUID | None = None,
    external_funder_name: str | None = None,
    status: BudgetStatus | None = None,
    duration_months: int | None = None,
    local_currency: str | None = None,
) -> BudgetModel | None:
    budget = get_budget(session, budget_id)
    if not budget:
        return None

    budget.name = name or budget.name
    budget.status = status or budget.status
    budget.duration_months = duration_months or budget.duration_months
    budget.local_currency = local_currency or budget.local_currency
    budget.owner_id = owner_id or budget.owner_id
    budget.funding_customer_id = funding_customer_id or budget.funding_customer_id
    budget.external_funder_name = external_funder_name or budget.external_funder_name
    session.commit()
    session.refresh(budget)
    return budget


def delete_budget(session: Session, budget: BudgetModel) -> bool:
    session.delete(budget)
    session.commit()
    return True


def get_funded_budgets_summary(session: Session, funding_customer_id: UUID) -> dict:
    total_budgets = (
        session.query(func.count(BudgetModel.id))
        .filter(BudgetModel.funding_customer_id == funding_customer_id)
        .scalar()
    )
    currency_rows = (
        session.query(
            BudgetModel.local_currency,
            func.coalesce(func.sum(BudgetModel.total_amount), 0),
        )
        .filter(BudgetModel.funding_customer_id == funding_customer_id)
        .group_by(BudgetModel.local_currency)
        .all()
    )
    return {
        "total_budgets": total_budgets,
        "total_allocated_by_currency": [
            {"currency": currency, "total_allocated": total} for currency, total in currency_rows
        ],
    }


# TODO I guess return can be done with pydantic / revisit
def get_funded_grantees(session: Session, funding_customer_id: UUID) -> list[dict]:
    rows = (
        session.query(
            BudgetModel.owner_id,
            BudgetModel.local_currency,
            func.count(BudgetModel.id).label("budgets_count"),
            func.coalesce(func.sum(BudgetModel.total_amount), 0).label("total_allocated"),
        )
        .filter(BudgetModel.funding_customer_id == funding_customer_id)
        .group_by(BudgetModel.owner_id, BudgetModel.local_currency)
        .all()
    )
    grantees: dict = {}
    for row in rows:
        grantee = grantees.setdefault(
            row.owner_id,
            {"owner_id": row.owner_id, "budgets_count": 0, "total_allocated_by_currency": []},
        )
        grantee["budgets_count"] += row.budgets_count
        grantee["total_allocated_by_currency"].append(
            {"currency": row.local_currency, "total_allocated": row.total_allocated}
        )
    return list(grantees.values())


def recalculate_budget_total(session: Session, budget_id: UUID) -> BudgetModel | None:
    """Recompute total_amount from this budget's lines and persist it."""
    budget = get_budget(session, budget_id)
    if not budget:
        return None

    total = (
        session.query(func.coalesce(func.sum(BudgetLineModel.amount), 0))
        .filter(BudgetLineModel.budget_id == budget_id)
        .scalar()
    )
    budget.total_amount = total
    session.commit()
    session.refresh(budget)
    return budget
