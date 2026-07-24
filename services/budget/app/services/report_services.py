from dateutil.relativedelta import relativedelta
from fastapi import status
from uuid import UUID

from app.crud.budget_crud import get_budget
from app.crud.report_crud import (
    create_report,
    get_report,
    list_reports,
    list_overlapping_reports,
    update_report,
    delete_report,
    transition_status,
)
from app.core.exceptions import DomainError, PermissionDenied
from app.models.budget import BudgetModel
from app.schemas.budget_schema import BudgetStatus
from app.schemas.report_schema import ReportCreate, ReportUpdate, ReportStatus
from app.services.budget_services import _can_view_budget


def _get_report_or_404(db, report_id: UUID):
    report = get_report(db, report_id)
    if not report:
        raise DomainError("Report Not found", status.HTTP_400_BAD_REQUEST)
    return report


def _get_budget_or_404(db, budget_id: UUID) -> BudgetModel:
    budget = get_budget(db, budget_id)
    if not budget:
        raise DomainError("Budget Not found", status.HTTP_400_BAD_REQUEST)
    return budget


def _get_viewable_budget(db, valid_user: dict, budget_id: UUID) -> BudgetModel:
    budget = _get_budget_or_404(db, budget_id)
    if valid_user["role"] != "superuser" and not _can_view_budget(budget, valid_user):
        raise DomainError("Budget Not found", status.HTTP_400_BAD_REQUEST)
    return budget


def _is_owner(budget: BudgetModel, valid_user: dict) -> bool:
    return valid_user["role"] == "superuser" or str(budget.owner_id) == str(
        valid_user.get("customer_id")
    )


def _can_review(budget: BudgetModel, valid_user: dict) -> bool:
    if valid_user["role"] == "superuser":
        return True
    customer_id = valid_user.get("customer_id")
    if budget.funding_customer_id:
        return str(budget.funding_customer_id) == str(customer_id)
    return str(budget.owner_id) == str(customer_id)


def _validate_period(period_start, period_end) -> None:
    if period_end < period_start:
        raise DomainError("period_end cannot be before period_start", status.HTTP_400_BAD_REQUEST)


def _get_owned_report(db, valid_user: dict, report_id: UUID):
    report = _get_report_or_404(db, report_id)
    budget = _get_viewable_budget(db, valid_user, report.budget_id)
    if not _is_owner(budget, valid_user):
        raise PermissionDenied()
    return report


def create_report_service(db, valid_user: dict, report: ReportCreate):
    budget = _get_viewable_budget(db, valid_user, report.budget_id)

    if budget.status != BudgetStatus.confirmed:
        raise DomainError(
            "Reports can only be created against a confirmed budget",
            status.HTTP_400_BAD_REQUEST,
        )

    period_start = report.period_start
    period_end = report.period_end
    if bool(period_start) != bool(period_end):
        raise DomainError(
            "period_start and period_end must be provided together, or neither",
            status.HTTP_400_BAD_REQUEST,
        )
    if not period_start and not period_end:
        if not budget.start_date:
            # update_budget_service enforces start_date before confirming a budget,
            # but this guards against any future path that sets confirmed directly.
            raise DomainError(
                "Budget has no start_date set; cannot default the report period",
                status.HTTP_400_BAD_REQUEST,
            )
        period_start = budget.start_date
        period_end = budget.start_date + relativedelta(months=budget.duration_months or 0)

    _validate_period(period_start, period_end)

    overlapping = list_overlapping_reports(db, budget.id, period_start, period_end)
    if overlapping:
        raise DomainError(
            "Report period overlaps an existing report for this budget",
            status.HTTP_400_BAD_REQUEST,
        )

    return create_report(
        session=db,
        user_id=valid_user["user_id"],
        budget_id=budget.id,
        name=report.name,
        period_start=period_start,
        period_end=period_end,
    )


def get_report_service(db, valid_user: dict, report_id: UUID):
    report = _get_report_or_404(db, report_id)
    _get_viewable_budget(db, valid_user, report.budget_id)
    return report


def list_reports_service(db, valid_user: dict, budget_id: UUID):
    _get_viewable_budget(db, valid_user, budget_id)
    return list_reports(db, budget_id=budget_id)


def update_report_service(db, valid_user: dict, report_id: UUID, report_update: ReportUpdate):
    report = _get_owned_report(db, valid_user, report_id)
    if report.status != ReportStatus.draft:
        raise DomainError("Only a draft report can be updated", status.HTTP_400_BAD_REQUEST)

    period_start = report_update.period_start or report.period_start
    period_end = report_update.period_end or report.period_end
    if report_update.period_start or report_update.period_end:
        _validate_period(period_start, period_end)
        overlapping = list_overlapping_reports(
            db, report.budget_id, period_start, period_end, exclude_report_id=report.id
        )
        if overlapping:
            raise DomainError(
                "Report period overlaps an existing report for this budget",
                status.HTTP_400_BAD_REQUEST,
            )

    return update_report(
        session=db,
        report=report,
        name=report_update.name,
        period_start=report_update.period_start,
        period_end=report_update.period_end,
    )


def delete_report_service(db, valid_user: dict, report_id: UUID):
    report = _get_owned_report(db, valid_user, report_id)
    if report.status != ReportStatus.draft:
        raise DomainError("Only a draft report can be deleted", status.HTTP_400_BAD_REQUEST)
    return delete_report(db, report)


def submit_report_service(db, valid_user: dict, report_id: UUID):
    report = _get_owned_report(db, valid_user, report_id)
    if report.status != ReportStatus.draft:
        raise DomainError("Only a draft report can be submitted", status.HTTP_400_BAD_REQUEST)
    return transition_status(db, report, ReportStatus.submitted)


def review_report_service(
    db,
    valid_user: dict,
    report_id: UUID,
    decision: ReportStatus,
    review_notes: str | None = None,
):
    if decision not in (ReportStatus.approved, ReportStatus.rejected):
        raise DomainError(
            "Review decision must be approved or rejected", status.HTTP_400_BAD_REQUEST
        )

    report = _get_report_or_404(db, report_id)
    # Visibility gate first (owner-or-funder), same info-hiding as every other
    # report endpoint: a total stranger gets "not found", not a permission
    # error that would confirm the report exists. Only a user who can already
    # see the report (but isn't the funder) reaches the review-specific check
    # below and gets PermissionDenied — that discloses nothing new to them.
    budget = _get_viewable_budget(db, valid_user, report.budget_id)
    if not _can_review(budget, valid_user):
        raise PermissionDenied()

    if report.status != ReportStatus.submitted:
        raise DomainError("Only a submitted report can be reviewed", status.HTTP_400_BAD_REQUEST)

    return transition_status(
        db, report, decision, user_id=valid_user["user_id"], review_notes=review_notes
    )


def reopen_report_service(db, valid_user: dict, report_id: UUID):
    report = _get_owned_report(db, valid_user, report_id)
    if report.status != ReportStatus.rejected:
        raise DomainError(
            "Only a rejected report can be reopened to draft", status.HTTP_400_BAD_REQUEST
        )
    return transition_status(db, report, ReportStatus.draft)
