from datetime import date, datetime

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
    local_currency: str | None = None,
    actual_currency: str | None = None,
    start_date: date | None = None,
    duration_months: int | None = None,
    total_amount: float | None = None,
    donor_total_amount: float | None = None,
    estimated_exchange_rate: float | None = None,
) -> BudgetModel:
    kwargs = {
        "name": name,
        "owner_id": owner_id,
        "funding_customer_id": funding_customer_id,
        "external_funder_name": external_funder_name,
        "created_by": user_id,
        "updated_by": user_id,
        "status": status or BudgetStatus.draft,
        # Only set when provided — omitting a key lets the model's own
        # column default (e.g. local_currency="GBP") apply, same as before
        # this function accepted these fields at all.
        **{
            k: v
            for k, v in {
                "local_currency": local_currency,
                "actual_currency": actual_currency,
                "start_date": start_date,
                "duration_months": duration_months,
                "total_amount": total_amount,
                "donor_total_amount": donor_total_amount,
                "estimated_exchange_rate": estimated_exchange_rate,
            }.items()
            if v is not None
        },
    }
    budget = BudgetModel(**kwargs)
    session.add(budget)
    session.commit()
    session.refresh(budget)
    return budget


def get_budgets_by_creator(session: Session, user_id: UUID) -> list[BudgetModel]:
    """Data-subject-rights export (GET /users/me/export on the users
    service) — a listing of financial records the requesting user created,
    called cross-service via the no-auth internal
    GET /budgets/by-creator/{user_id} endpoint."""
    return session.query(BudgetModel).filter(BudgetModel.created_by == user_id).all()


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
    actual_currency: str | None = None,
    start_date: date | None = None,
    donor_total_amount: float | None = None,
    donor_total_amount_set: bool = False,
    estimated_exchange_rate: float | None = None,
    estimated_exchange_rate_set: bool = False,
    confirmed_at: datetime | None = None,
    clear_confirmed_at: bool = False,
) -> BudgetModel | None:
    budget = get_budget(session, budget_id)
    if not budget:
        return None

    if name is not None:
        budget.name = name
    if status is not None:
        budget.status = status
    if duration_months is not None:
        budget.duration_months = duration_months
    if local_currency is not None:
        budget.local_currency = local_currency
    if actual_currency is not None:
        budget.actual_currency = actual_currency
    if start_date is not None:
        budget.start_date = start_date
    if owner_id is not None:
        budget.owner_id = owner_id
    # The two funder fields are either/or, so external_funder_name being
    # explicitly sent (even "") is what signals a funder edit — and it
    # always carries the correct funding_customer_id alongside it (None to
    # clear, a UUID to link), letting a grantee switch between a donor-linked
    # and a free-text funder in one save. A funding_customer_id sent on its
    # own (no external_funder_name) is still applied directly, e.g. a future
    # donor-only linking flow that never touches the name field.
    if external_funder_name is not None:
        budget.external_funder_name = external_funder_name
        budget.funding_customer_id = funding_customer_id
    elif funding_customer_id is not None:
        budget.funding_customer_id = funding_customer_id
    # Unlike the "None means don't touch" fields above, these two need to be
    # explicitly clearable (an owner blanking the input to undo a mistaken
    # entry) — so the caller signals presence via the _set flags instead of
    # relying on None to mean "omitted". donor_total_amount_set/
    # estimated_exchange_rate_set=True always assigns, including None.
    if donor_total_amount_set:
        budget.donor_total_amount = donor_total_amount
    if estimated_exchange_rate_set:
        budget.estimated_exchange_rate = estimated_exchange_rate
    if clear_confirmed_at:
        budget.confirmed_at = None
    elif confirmed_at is not None:
        budget.confirmed_at = confirmed_at
    session.commit()
    session.refresh(budget)
    return budget


def delete_budget(session: Session, budget: BudgetModel) -> bool:
    session.delete(budget)
    session.commit()
    return True


def get_funded_budgets_summary(session: Session, funding_customer_id: UUID) -> dict:
    """Grouped by `actual_currency` and summed from `total_amount ÷
    estimated_exchange_rate` — the real, line-derived total converted into
    the donor's own currency — not the flat `donor_total_amount` promise
    (which can overstate what's actually been built) and not `local_currency`
    (the grantee's operating currency, meaningless to a donor who may fund
    several grantees in different currencies). Same computation as the
    grantee dashboard's own committed-by-currency aggregation
    (`dashboard_crud.sum_committed_by_currency`, design.md Decision 8), just
    scoped to `funding_customer_id` instead of `owner_id`. Budgets missing
    `actual_currency` or a usable (non-null, non-zero) `estimated_exchange_rate`
    are excluded from this figure entirely, not folded into another
    currency's total — they still count toward `total_budgets`.
    `total_budgets` counts every funded budget regardless of status; the
    currency-grouped figure is scoped to `confirmed` only — draft totals can
    still change."""
    total_budgets = (
        session.query(func.count(BudgetModel.id))
        .filter(BudgetModel.funding_customer_id == funding_customer_id)
        .scalar()
    )
    currency_rows = (
        session.query(
            BudgetModel.actual_currency,
            func.sum(
                func.coalesce(BudgetModel.total_amount, 0.0) / BudgetModel.estimated_exchange_rate
            ),
        )
        .filter(
            BudgetModel.funding_customer_id == funding_customer_id,
            BudgetModel.status == BudgetStatus.confirmed,
            BudgetModel.actual_currency.isnot(None),
            BudgetModel.estimated_exchange_rate.isnot(None),
            BudgetModel.estimated_exchange_rate != 0,
        )
        .group_by(BudgetModel.actual_currency)
        .all()
    )
    return {
        "total_budgets": total_budgets,
        "total_allocated_by_currency": [
            {"currency": currency, "total_allocated": total or 0.0}
            for currency, total in currency_rows
        ],
    }


# TODO I guess return can be done with pydantic / revisit
def get_funded_grantees(session: Session, funding_customer_id: UUID) -> list[dict]:
    """`budgets_count` counts every budget funded for that grantee, regardless
    of status. `total_allocated_by_currency` is grouped by `actual_currency`
    and summed from `total_amount ÷ estimated_exchange_rate` (see
    `get_funded_budgets_summary` for why not `donor_total_amount`/
    `local_currency`), scoped to `confirmed` budgets only, so it's computed
    separately and only covers the subset with a usable rate on file."""
    count_rows = (
        session.query(
            BudgetModel.owner_id,
            func.count(BudgetModel.id).label("budgets_count"),
        )
        .filter(BudgetModel.funding_customer_id == funding_customer_id)
        .group_by(BudgetModel.owner_id)
        .all()
    )
    currency_rows = (
        session.query(
            BudgetModel.owner_id,
            BudgetModel.actual_currency,
            func.sum(
                func.coalesce(BudgetModel.total_amount, 0.0) / BudgetModel.estimated_exchange_rate
            ).label("total_allocated"),
        )
        .filter(
            BudgetModel.funding_customer_id == funding_customer_id,
            BudgetModel.status == BudgetStatus.confirmed,
            BudgetModel.actual_currency.isnot(None),
            BudgetModel.estimated_exchange_rate.isnot(None),
            BudgetModel.estimated_exchange_rate != 0,
        )
        .group_by(BudgetModel.owner_id, BudgetModel.actual_currency)
        .all()
    )
    grantees: dict = {
        row.owner_id: {
            "owner_id": row.owner_id,
            "budgets_count": row.budgets_count,
            "total_allocated_by_currency": [],
        }
        for row in count_rows
    }
    for row in currency_rows:
        grantee = grantees.setdefault(
            row.owner_id,
            {"owner_id": row.owner_id, "budgets_count": 0, "total_allocated_by_currency": []},
        )
        grantee["total_allocated_by_currency"].append(
            {"currency": row.actual_currency, "total_allocated": row.total_allocated or 0.0}
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
