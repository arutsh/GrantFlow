from sqlalchemy.orm import Session
from app.models.report import ReportLineModel
from uuid import UUID


def create_report_line(
    session: Session,
    user_id: UUID,
    report_id: UUID,
    budget_line_id: UUID,
    description: str,
    amount: float,
    extra_fields: dict | None = None,
) -> ReportLineModel:
    report_line = ReportLineModel(
        report_id=report_id,
        budget_line_id=budget_line_id,
        description=description,
        amount=amount,
        extra_fields=extra_fields,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(report_line)
    session.commit()
    session.refresh(report_line)
    return report_line


def get_report_line(session: Session, report_line_id: UUID) -> ReportLineModel | None:
    return session.query(ReportLineModel).filter(ReportLineModel.id == report_line_id).first()


def list_report_lines(session: Session, report_id: UUID | None = None) -> list[ReportLineModel]:
    query = session.query(ReportLineModel)
    if report_id:
        query = query.filter(ReportLineModel.report_id == report_id)
    return query.all()


def update_report_line(
    session: Session,
    report_line: ReportLineModel,
    description: str | None = None,
    amount: float | None = None,
    extra_fields: dict | None = None,
) -> ReportLineModel:
    if description is not None:
        report_line.description = description
    if amount is not None:
        report_line.amount = amount
    if extra_fields is not None:
        report_line.extra_fields = {**(report_line.extra_fields or {}), **extra_fields}
    session.commit()
    session.refresh(report_line)
    return report_line


def delete_report_line(session: Session, report_line: ReportLineModel) -> bool:
    session.delete(report_line)
    session.commit()
    return True
