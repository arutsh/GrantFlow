from datetime import date, datetime, timezone

from sqlalchemy.orm import Session, contains_eager
from app.crud.budget_crud import budget_visible_to_customer_clause
from app.models.budget import BudgetModel
from app.models.report import ReportModel
from app.schemas.report_schema import ReportStatus
from uuid import UUID


def create_report(
    session: Session,
    user_id: UUID,
    budget_id: UUID,
    name: str,
    period_start: date,
    period_end: date,
) -> ReportModel:
    report = ReportModel(
        budget_id=budget_id,
        name=name,
        period_start=period_start,
        period_end=period_end,
        status=ReportStatus.draft,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def get_report(session: Session, report_id: UUID) -> ReportModel | None:
    return session.query(ReportModel).filter(ReportModel.id == report_id).first()


def list_reports(session: Session, budget_id: UUID | None = None) -> list[ReportModel]:
    query = session.query(ReportModel)
    if budget_id:
        query = query.filter(ReportModel.budget_id == budget_id)
    return query.all()


def list_all_reports(
    session: Session,
    customer_id: UUID | str | None,
    status: ReportStatus | None = None,
    budget_id: UUID | None = None,
    funding_customer_id: UUID | None = None,
) -> list[ReportModel]:
    """Cross-budget report listing for the reports directory (GET /reports/).

    customer_id=None means "no visibility restriction" (superuser); otherwise
    scoped to every budget the customer owns OR funds — the same combined
    owner-or-funder rule already used by get_viewable_budget for a single
    budget (see design.md Decision 7), not two separate owner/donor routes;
    budget_visible_to_customer_clause is the single source of truth for that
    rule in SQL form, so it can't drift from budget_services._can_view_budget.
    Eager-loads Budget via contains_eager (not joinedload, which would issue
    a second join on top of the one already needed for the filter) so the
    service layer can attach budget name/status/funder without a per-row
    lookup.
    """
    query = (
        session.query(ReportModel)
        .join(BudgetModel, ReportModel.budget_id == BudgetModel.id)
        .options(contains_eager(ReportModel.budget))
    )
    if customer_id is not None:
        query = query.filter(budget_visible_to_customer_clause(customer_id))
    if status:
        query = query.filter(ReportModel.status == status)
    if budget_id:
        query = query.filter(ReportModel.budget_id == budget_id)
    if funding_customer_id:
        query = query.filter(BudgetModel.funding_customer_id == funding_customer_id)
    return query.all()


def list_overlapping_reports(
    session: Session,
    budget_id: UUID,
    period_start: date,
    period_end: date,
    exclude_report_id: UUID | None = None,
) -> list[ReportModel]:
    """Any report for this budget whose period overlaps the given range,
    regardless of status — the non-overlap rule applies to all reports."""
    query = session.query(ReportModel).filter(
        ReportModel.budget_id == budget_id,
        ReportModel.period_start <= period_end,
        ReportModel.period_end >= period_start,
    )
    if exclude_report_id:
        query = query.filter(ReportModel.id != exclude_report_id)
    return query.all()


def update_report(
    session: Session,
    report: ReportModel,
    name: str | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> ReportModel:
    if name is not None:
        report.name = name
    if period_start is not None:
        report.period_start = period_start
    if period_end is not None:
        report.period_end = period_end
    session.commit()
    session.refresh(report)
    return report


def delete_report(session: Session, report: ReportModel) -> bool:
    session.delete(report)
    session.commit()
    return True


def transition_status(
    session: Session,
    report: ReportModel,
    new_status: ReportStatus,
    user_id: UUID | None = None,
    review_notes: str | None = None,
) -> ReportModel:
    report.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == ReportStatus.submitted:
        report.submitted_at = now
    elif new_status in (ReportStatus.approved, ReportStatus.rejected):
        report.reviewed_at = now
        report.reviewed_by = user_id
        report.review_notes = review_notes
    session.commit()
    session.refresh(report)
    return report
