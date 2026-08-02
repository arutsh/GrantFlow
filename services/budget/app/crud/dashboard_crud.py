from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models.budget import BudgetModel, BudgetStatus
from app.models.currency_ledger import CurrencyConversionModel, FundingReceiptModel
from app.models.report import ReportLineModel, ReportModel


def _owned_confirmed_clause(customer_id: UUID) -> tuple[ColumnElement[bool], ColumnElement[bool]]:
    """The owner+confirmed filter pair every dashboard aggregate below scopes
    to (count_budgets_by_status is the one exception — it counts every
    status, not just confirmed) — single source of truth so the two
    conditions can't drift apart across functions."""
    return (BudgetModel.owner_id == customer_id, BudgetModel.status == BudgetStatus.confirmed)


def count_budgets_by_status(session: Session, customer_id: UUID) -> list[tuple[BudgetStatus, int]]:
    return (
        session.query(BudgetModel.status, func.count(BudgetModel.id))
        .filter(BudgetModel.owner_id == customer_id)
        .group_by(BudgetModel.status)
        .all()
    )


def sum_committed_by_currency(session: Session, customer_id: UUID) -> list[tuple[str, float]]:
    """Per design.md Decision 8: committed is built lines (total_amount)
    converted back to the donor's currency via the grantee's own estimated
    rate — never the flat donor_total_amount promise, which can overstate
    what's actually allocated. Budgets missing actual_currency or a usable
    (non-null, non-zero) estimated_exchange_rate are excluded entirely
    rather than folded into another currency's total."""
    rows = (
        session.query(
            BudgetModel.actual_currency,
            func.sum(
                func.coalesce(BudgetModel.total_amount, 0.0) / BudgetModel.estimated_exchange_rate
            ),
        )
        .filter(
            *_owned_confirmed_clause(customer_id),
            BudgetModel.actual_currency.isnot(None),
            BudgetModel.estimated_exchange_rate.isnot(None),
            BudgetModel.estimated_exchange_rate != 0,
        )
        .group_by(BudgetModel.actual_currency)
        .all()
    )
    return [(currency, amount or 0.0) for currency, amount in rows]


def sum_received_by_currency(session: Session, customer_id: UUID) -> list[tuple[str, float]]:
    rows = (
        session.query(
            BudgetModel.actual_currency,
            func.coalesce(func.sum(FundingReceiptModel.amount), 0.0),
        )
        .join(FundingReceiptModel, FundingReceiptModel.budget_id == BudgetModel.id)
        .filter(*_owned_confirmed_clause(customer_id), BudgetModel.actual_currency.isnot(None))
        .group_by(BudgetModel.actual_currency)
        .all()
    )
    return [(currency, amount) for currency, amount in rows if currency is not None]


def sum_converted_by_currency(session: Session, customer_id: UUID) -> list[tuple[str, float]]:
    """Donor-currency side of each conversion (CurrencyConversion.donor_amount),
    grouped the same way as received-by-currency, so the two are directly
    comparable as a conversion-progress percentage."""
    rows = (
        session.query(
            BudgetModel.actual_currency,
            func.coalesce(func.sum(CurrencyConversionModel.donor_amount), 0.0),
        )
        .join(CurrencyConversionModel, CurrencyConversionModel.budget_id == BudgetModel.id)
        .filter(*_owned_confirmed_clause(customer_id), BudgetModel.actual_currency.isnot(None))
        .group_by(BudgetModel.actual_currency)
        .all()
    )
    return [(currency, amount) for currency, amount in rows if currency is not None]


def budget_breakdown(session: Session, customer_id: UUID) -> list[tuple[BudgetModel, float, float]]:
    """One row per confirmed budget this customer owns: (budget, converted,
    spent), both in local_currency. Reuses the same building blocks
    get_ledger_balance_service composes (CurrencyConversion.local_amount and
    ReportLine.amount sums) — no new FIFO/allocation logic — but as two
    grouped subqueries joined once across every confirmed budget, instead of
    N per-budget calls. Each subquery is pre-scoped to this customer's own
    confirmed budget ids rather than aggregating every budget in the system
    and filtering afterward."""
    budget_ids = (
        session.query(BudgetModel.id).filter(*_owned_confirmed_clause(customer_id)).subquery()
    )
    converted_sq = (
        session.query(
            CurrencyConversionModel.budget_id.label("budget_id"),
            func.sum(CurrencyConversionModel.local_amount).label("converted"),
        )
        .filter(CurrencyConversionModel.budget_id.in_(session.query(budget_ids.c.id)))
        .group_by(CurrencyConversionModel.budget_id)
        .subquery()
    )
    spent_sq = (
        session.query(
            ReportModel.budget_id.label("budget_id"),
            func.sum(ReportLineModel.amount).label("spent"),
        )
        .join(ReportLineModel, ReportLineModel.report_id == ReportModel.id)
        .filter(ReportModel.budget_id.in_(session.query(budget_ids.c.id)))
        .group_by(ReportModel.budget_id)
        .subquery()
    )
    rows = (
        session.query(
            BudgetModel,
            func.coalesce(converted_sq.c.converted, 0.0),
            func.coalesce(spent_sq.c.spent, 0.0),
        )
        .outerjoin(converted_sq, converted_sq.c.budget_id == BudgetModel.id)
        .outerjoin(spent_sq, spent_sq.c.budget_id == BudgetModel.id)
        .filter(*_owned_confirmed_clause(customer_id))
        .all()
    )
    return [(budget, converted or 0.0, spent or 0.0) for budget, converted, spent in rows]
