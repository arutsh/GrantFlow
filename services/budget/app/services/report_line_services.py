from fastapi import status
from uuid import UUID

from app.crud.budget_line_crud import get_budget_line
from app.crud.report_line_crud import (
    create_report_line,
    get_report_line,
    list_report_lines,
    update_report_line,
    delete_report_line,
)
from app.core.exceptions import DomainError
from app.schemas.report_schema import ReportStatus
from app.schemas.report_line_schema import ReportLineCreate, ReportLineUpdate
from app.services.report_services import (
    _get_owned_report,
    _get_viewable_budget,
    _get_report_or_404,
)


def _get_report_line_or_404(db, report_line_id: UUID):
    report_line = get_report_line(db, report_line_id)
    if not report_line:
        raise DomainError("Report Line Not found", status.HTTP_400_BAD_REQUEST)
    return report_line


def create_report_line_service(db, valid_user: dict, report_line: ReportLineCreate):
    report = _get_owned_report(db, valid_user, report_line.report_id)
    if report.status != ReportStatus.draft:
        raise DomainError(
            "Report lines can only be added to a draft report", status.HTTP_400_BAD_REQUEST
        )

    budget_line = get_budget_line(db, report_line.budget_line_id)
    if not budget_line or budget_line.budget_id != report.budget_id:
        raise DomainError(
            "budget_line_id must belong to the same budget as the report",
            status.HTTP_400_BAD_REQUEST,
        )

    return create_report_line(
        session=db,
        user_id=valid_user["user_id"],
        report_id=report.id,
        budget_line_id=report_line.budget_line_id,
        description=report_line.description,
        amount=report_line.amount,
        extra_fields=report_line.extra_fields,
    )


def get_report_line_by_id_service(db, valid_user: dict, report_line_id: UUID):
    report_line = _get_report_line_or_404(db, report_line_id)
    report = _get_report_or_404(db, report_line.report_id)
    _get_viewable_budget(db, valid_user, report.budget_id)
    return report_line


def list_report_lines_service(db, valid_user: dict, report_id: UUID):
    report = _get_report_or_404(db, report_id)
    _get_viewable_budget(db, valid_user, report.budget_id)
    return list_report_lines(db, report_id=report_id)


def update_report_line_service(
    db, valid_user: dict, report_line_id: UUID, report_line_update: ReportLineUpdate
):
    report_line = _get_report_line_or_404(db, report_line_id)
    report = _get_owned_report(db, valid_user, report_line.report_id)
    if report.status != ReportStatus.draft:
        raise DomainError(
            "Report lines can only be edited on a draft report", status.HTTP_400_BAD_REQUEST
        )

    return update_report_line(
        session=db,
        report_line=report_line,
        description=report_line_update.description,
        amount=report_line_update.amount,
        extra_fields=report_line_update.extra_fields,
    )


def delete_report_line_service(db, valid_user: dict, report_line_id: UUID):
    report_line = _get_report_line_or_404(db, report_line_id)
    report = _get_owned_report(db, valid_user, report_line.report_id)
    if report.status != ReportStatus.draft:
        raise DomainError(
            "Report lines can only be deleted on a draft report", status.HTTP_400_BAD_REQUEST
        )
    return delete_report_line(db, report_line)
