# /services/budget/app/api/report_line_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import SessionLocal
from app.schemas.report_line_schema import ReportLine, ReportLineCreate, ReportLineUpdate
from app.services.report_line_services import (
    create_report_line_service,
    get_report_line_by_id_service,
    list_report_lines_service,
    update_report_line_service,
    delete_report_line_service,
)
from shared.security.dependencies import get_validated_user  # noqa: F401

router = APIRouter(prefix="/report-lines", tags=["Report Lines"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=ReportLine)
def create_report_line_view(
    report_line: ReportLineCreate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    return create_report_line_service(db, valid_user, report_line)


@router.get("/by-report/{report_id}", response_model=List[ReportLine])
def list_report_lines_by_report_view(
    report_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return list_report_lines_service(db, valid_user, report_id)


@router.get("/{report_line_id}", response_model=ReportLine)
def get_report_line_view(
    report_line_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return get_report_line_by_id_service(db, valid_user, report_line_id)


@router.patch("/{report_line_id}", response_model=ReportLine)
def update_report_line_view(
    report_line_id: UUID,
    report_line: ReportLineUpdate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    return update_report_line_service(db, valid_user, report_line_id, report_line)


@router.delete("/{report_line_id}")
def delete_report_line_view(
    report_line_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return {"success": delete_report_line_service(db, valid_user, report_line_id)}
