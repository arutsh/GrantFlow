from datetime import date, datetime, timezone

from sqlalchemy.orm import Session, contains_eager
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


def get_reports_by_creator(session: Session, user_id: UUID) -> list[ReportModel]:
    """Data-subject-rights export — see get_budgets_by_creator in
    budget_crud.py for the cross-service call this backs."""
    return session.query(ReportModel).filter(ReportModel.created_by == user_id).all()


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
    """Cross-budget report listing for the owner's reports directory
    (GET /reports/) — every report on a budget this customer OWNS (the
    grantee/owner side; see list_funded_reports for the donor/funder side).

    Mirrors /budgets/ vs /budgets/funded/'s existing owner/donor route split rather
    than the combined owner-or-funder rule get_viewable_budget uses for a
    single budget's access check. Eager-loads Budget via contains_eager (not
    joinedload, which would issue a second join on top of the one already
    needed for the filter) so the service layer can attach budget name/
    status/funder without a per-row lookup.
    """
    query = (
        session.query(ReportModel)
        .join(BudgetModel, ReportModel.budget_id == BudgetModel.id)
        .options(contains_eager(ReportModel.budget))
    )
    if customer_id is not None:
        query = query.filter(BudgetModel.owner_id == customer_id)
    if status:
        query = query.filter(ReportModel.status == status)
    if budget_id:
        query = query.filter(ReportModel.budget_id == budget_id)
    if funding_customer_id:
        query = query.filter(BudgetModel.funding_customer_id == funding_customer_id)
    return query.all()


def list_funded_reports(
    session: Session,
    funding_customer_id: UUID | str,
    status: ReportStatus | None = None,
    budget_id: UUID | None = None,
    owner_id: UUID | None = None,
) -> list[ReportModel]:
    """Cross-budget report listing scoped to budgets this donor funds
    (GET /reports/funded/) — the funder-side counterpart to
    list_all_reports, showing each grantee's reports against the budgets
    this donor funds. `owner_id` narrows to one grantee, mirroring
    list_all_reports's `funding_customer_id` narrowing on the owner side.
    """
    query = (
        session.query(ReportModel)
        .join(BudgetModel, ReportModel.budget_id == BudgetModel.id)
        .options(contains_eager(ReportModel.budget))
        .filter(BudgetModel.funding_customer_id == funding_customer_id)
    )
    if status:
        query = query.filter(ReportModel.status == status)
    if budget_id:
        query = query.filter(ReportModel.budget_id == budget_id)
    if owner_id:
        query = query.filter(BudgetModel.owner_id == owner_id)
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
