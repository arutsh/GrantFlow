from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload
from app.models.budget import BudgetModel
from app.models.report import ReportModel
from app.schemas.report_schema import ReportStatus
from uuid import UUID


async def create_report(
    session: AsyncSession,
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
    await session.commit()
    return report


async def get_report(
    session: AsyncSession, report_id: UUID, load_lines: bool = False
) -> ReportModel | None:
    query = select(ReportModel).where(ReportModel.id == report_id)
    if load_lines:
        query = query.options(selectinload(ReportModel.lines))
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_reports_by_creator(session: AsyncSession, user_id: UUID) -> list[ReportModel]:
    """Data-subject-rights export — see get_budgets_by_creator in
    budget_crud.py for the cross-service call this backs."""
    result = await session.execute(select(ReportModel).where(ReportModel.created_by == user_id))
    return list(result.scalars().all())


async def list_reports(session: AsyncSession, budget_id: UUID | None = None) -> list[ReportModel]:
    query = select(ReportModel)
    if budget_id:
        query = query.where(ReportModel.budget_id == budget_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def list_all_reports(
    session: AsyncSession,
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
        select(ReportModel)
        .join(BudgetModel, ReportModel.budget_id == BudgetModel.id)
        .options(contains_eager(ReportModel.budget))
    )
    if customer_id is not None:
        query = query.where(BudgetModel.owner_id == customer_id)
    if status:
        query = query.where(ReportModel.status == status)
    if budget_id:
        query = query.where(ReportModel.budget_id == budget_id)
    if funding_customer_id:
        query = query.where(BudgetModel.funding_customer_id == funding_customer_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def list_funded_reports(
    session: AsyncSession,
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
        select(ReportModel)
        .join(BudgetModel, ReportModel.budget_id == BudgetModel.id)
        .options(contains_eager(ReportModel.budget))
        .where(BudgetModel.funding_customer_id == funding_customer_id)
    )
    if status:
        query = query.where(ReportModel.status == status)
    if budget_id:
        query = query.where(ReportModel.budget_id == budget_id)
    if owner_id:
        query = query.where(BudgetModel.owner_id == owner_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def list_overlapping_reports(
    session: AsyncSession,
    budget_id: UUID,
    period_start: date,
    period_end: date,
    exclude_report_id: UUID | None = None,
) -> list[ReportModel]:
    """Any report for this budget whose period overlaps the given range,
    regardless of status — the non-overlap rule applies to all reports."""
    query = select(ReportModel).where(
        ReportModel.budget_id == budget_id,
        ReportModel.period_start <= period_end,
        ReportModel.period_end >= period_start,
    )
    if exclude_report_id:
        query = query.where(ReportModel.id != exclude_report_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_report(
    session: AsyncSession,
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
    await session.commit()
    return report


async def delete_report(session: AsyncSession, report: ReportModel) -> bool:
    await session.delete(report)
    await session.commit()
    return True


async def transition_status(
    session: AsyncSession,
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
    await session.commit()
    return report
