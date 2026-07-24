# /services/budget/app/api/report_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import SessionLocal
from app.schemas.report_schema import (
    Report,
    ReportCreate,
    ReportUpdate,
    ReportWithLines,
    ReportReviewRequest,
)
from app.services.report_services import (
    create_report_service,
    get_report_service,
    list_reports_service,
    update_report_service,
    delete_report_service,
    submit_report_service,
    review_report_service,
    reopen_report_service,
)
from shared.security.dependencies import get_validated_user  # noqa: F401

router = APIRouter(prefix="/reports", tags=["Reports"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=Report)
def create_report_view(
    report: ReportCreate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    return create_report_service(db, valid_user, report)


@router.get("/by-budget/{budget_id}", response_model=List[Report])
def list_reports_by_budget_view(
    budget_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return list_reports_service(db, valid_user, budget_id)


@router.get("/{report_id}", response_model=ReportWithLines)
def get_report_view(
    report_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return get_report_service(db, valid_user, report_id)


@router.patch("/{report_id}", response_model=Report)
def update_report_view(
    report_id: UUID,
    report: ReportUpdate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    return update_report_service(db, valid_user, report_id, report)


@router.delete("/{report_id}")
def delete_report_view(
    report_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return {"success": delete_report_service(db, valid_user, report_id)}


@router.post("/{report_id}/submit", response_model=Report)
def submit_report_view(
    report_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return submit_report_service(db, valid_user, report_id)


@router.post("/{report_id}/review", response_model=Report)
def review_report_view(
    report_id: UUID,
    review: ReportReviewRequest,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    return review_report_service(db, valid_user, report_id, review.decision, review.review_notes)


@router.post("/{report_id}/reopen", response_model=Report)
def reopen_report_view(
    report_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return reopen_report_service(db, valid_user, report_id)
