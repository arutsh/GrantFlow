from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.currency_ledger import CurrencyConversionModel, ReportLineConversionAllocationModel
from app.models.report import ReportLineModel, ReportModel

# Guards against float rounding noise being treated as a real remaining
# balance (e.g. -1e-14 after several float subtractions).
FLOAT_EPSILON = 1e-9


def create_currency_conversion(
    session: Session,
    user_id: UUID,
    budget_id: UUID,
    donor_amount: float,
    local_amount: float,
    converted_at: date,
) -> CurrencyConversionModel:
    conversion = CurrencyConversionModel(
        budget_id=budget_id,
        donor_amount=donor_amount,
        local_amount=local_amount,
        converted_at=converted_at,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(conversion)
    session.commit()
    session.refresh(conversion)
    return conversion


def get_currency_conversion(
    session: Session, conversion_id: UUID
) -> CurrencyConversionModel | None:
    return (
        session.query(CurrencyConversionModel)
        .filter(CurrencyConversionModel.id == conversion_id)
        .first()
    )


def list_currency_conversions(
    session: Session, budget_id: UUID | None = None
) -> list[CurrencyConversionModel]:
    query = session.query(CurrencyConversionModel)
    if budget_id:
        query = query.filter(CurrencyConversionModel.budget_id == budget_id)
    return query.order_by(CurrencyConversionModel.converted_at).all()


def create_allocation(
    session: Session,
    report_line_id: UUID,
    conversion_id: UUID,
    amount_allocated: float,
) -> ReportLineConversionAllocationModel:
    allocation = ReportLineConversionAllocationModel(
        report_line_id=report_line_id,
        conversion_id=conversion_id,
        amount_allocated=amount_allocated,
    )
    session.add(allocation)
    session.commit()
    session.refresh(allocation)
    return allocation


def delete_allocations_for_report_line(session: Session, report_line_id: UUID) -> None:
    """Clears a report line's existing allocation rows so it can be safely
    re-derived from scratch (see allocate_fifo_service)."""
    (
        session.query(ReportLineConversionAllocationModel)
        .filter(ReportLineConversionAllocationModel.report_line_id == report_line_id)
        .delete()
    )
    session.commit()


def list_unconsumed_lots(
    session: Session, budget_id: UUID
) -> list[tuple[CurrencyConversionModel, float]]:
    """This budget's currency conversions with remaining (unallocated)
    balance, oldest-converted first — the FIFO order expenses draw down
    against. One grouped-aggregate query, not one sum-query per conversion."""
    allocated = (
        session.query(
            ReportLineConversionAllocationModel.conversion_id.label("conversion_id"),
            func.sum(ReportLineConversionAllocationModel.amount_allocated).label("allocated"),
        )
        .group_by(ReportLineConversionAllocationModel.conversion_id)
        .subquery()
    )
    remaining = (
        CurrencyConversionModel.local_amount - func.coalesce(allocated.c.allocated, 0.0)
    ).label("remaining")
    rows = (
        session.query(CurrencyConversionModel, remaining)
        .outerjoin(allocated, allocated.c.conversion_id == CurrencyConversionModel.id)
        .filter(CurrencyConversionModel.budget_id == budget_id)
        .order_by(CurrencyConversionModel.converted_at, CurrencyConversionModel.created_at)
        .all()
    )
    return [(conversion, remaining) for conversion, remaining in rows if remaining > FLOAT_EPSILON]


def sum_report_line_amounts(session: Session, budget_id: UUID) -> float:
    """Total of every report-line amount for this budget, regardless of
    allocation state — used to compute the ledger's unconsumed
    local-currency balance."""
    total = (
        session.query(func.sum(ReportLineModel.amount))
        .join(ReportModel, ReportLineModel.report_id == ReportModel.id)
        .filter(ReportModel.budget_id == budget_id)
        .scalar()
    )
    return total or 0.0


def list_unsatisfied_report_lines(
    session: Session, budget_id: UUID
) -> list[tuple[ReportLineModel, float]]:
    """This budget's report lines whose amount isn't yet fully covered by
    existing allocations, oldest-created first — walked to retroactively
    backfill allocations when a new conversion is recorded (see design.md's
    2026-07-26 amended note). One grouped-aggregate query, not one
    sum-query per report line."""
    allocated = (
        session.query(
            ReportLineConversionAllocationModel.report_line_id.label("report_line_id"),
            func.sum(ReportLineConversionAllocationModel.amount_allocated).label("allocated"),
        )
        .group_by(ReportLineConversionAllocationModel.report_line_id)
        .subquery()
    )
    remaining = (ReportLineModel.amount - func.coalesce(allocated.c.allocated, 0.0)).label(
        "remaining"
    )
    rows = (
        session.query(ReportLineModel, remaining)
        .join(ReportModel, ReportLineModel.report_id == ReportModel.id)
        .outerjoin(allocated, allocated.c.report_line_id == ReportLineModel.id)
        .filter(ReportModel.budget_id == budget_id, ReportLineModel.amount.isnot(None))
        .order_by(ReportLineModel.created_at, ReportLineModel.id)
        .all()
    )
    return [(line, remaining) for line, remaining in rows if remaining > FLOAT_EPSILON]
