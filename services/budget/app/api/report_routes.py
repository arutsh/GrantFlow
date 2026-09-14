# /services/budget/app/api/report_routes.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.schemas.report_schema import (
    Report,
    ReportCreate,
    ReportUpdate,
    ReportWithLines,
    ReportWithBudgetInfo,
    ReportReviewRequest,
    ReportStatus,
)
from app.services.report_services import (
    create_report_service,
    get_report_service,
    list_reports_service,
    list_all_reports_service,
    list_funded_reports_service,
    update_report_service,
    delete_report_service,
    submit_report_service,
    review_report_service,
    reopen_report_service,
)
from app.services.customer_client import require_donor
from app.crud.report_crud import get_reports_by_creator
from shared.observability import set_span_attributes
from shared.security.dependencies import get_validated_user

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/", response_model=Report)
async def create_report_view(
    report: ReportCreate,
    db: AsyncSession = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(budget_id=report.budget_id)
    created_report = await create_report_service(db, valid_user, report)
    set_span_attributes(report_id=created_report.id)
    return created_report


@router.get("/", response_model=List[ReportWithBudgetInfo])
async def list_all_reports_view(
    status: ReportStatus | None = Query(default=None),
    budget_id: UUID | None = Query(default=None),
    funding_customer_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    return await list_all_reports_service(
        db,
        valid_user,
        status=status,
        budget_id=budget_id,
        funding_customer_id=funding_customer_id,
    )


@router.get("/funded/", response_model=List[ReportWithBudgetInfo])
async def list_funded_reports_view(
    status: ReportStatus | None = Query(default=None),
    budget_id: UUID | None = Query(default=None),
    owner_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    require_donor(valid_user)
    return await list_funded_reports_service(
        db,
        valid_user,
        status=status,
        budget_id=budget_id,
        owner_id=owner_id,
    )


@router.get("/by-budget/{budget_id}", response_model=List[Report])
async def list_reports_by_budget_view(
    budget_id: UUID, db: AsyncSession = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(budget_id=budget_id)
    return await list_reports_service(db, valid_user, budget_id)


@router.get("/by-creator/{user_id}")
async def get_reports_by_creator_endpoint(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    # Called by the users service to build a data-subject data-export — the
    # users service forwards the requesting user's own token, so this is
    # self-service only, same as delete_my_account. Unlike /customers/by_ids/,
    # this sits on the public router with no gateway-level path exclusion, so
    # it must enforce this itself rather than trust the "internal" convention.
    if str(valid_user["user_id"]) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to view this user's reports")
    reports = await get_reports_by_creator(db, user_id)
    return [
        {"id": str(r.id), "name": r.name, "type": "report", "created_at": r.created_at}
        for r in reports
    ]


@router.get("/{report_id}", response_model=ReportWithLines)
async def get_report_view(
    report_id: UUID, db: AsyncSession = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(report_id=report_id)
    return await get_report_service(db, valid_user, report_id)


@router.patch("/{report_id}", response_model=Report)
async def update_report_view(
    report_id: UUID,
    report: ReportUpdate,
    db: AsyncSession = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(report_id=report_id)
    return await update_report_service(db, valid_user, report_id, report)


@router.delete("/{report_id}")
async def delete_report_view(
    report_id: UUID, db: AsyncSession = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(report_id=report_id)
    return {"success": await delete_report_service(db, valid_user, report_id)}


@router.post("/{report_id}/submit", response_model=Report)
async def submit_report_view(
    report_id: UUID, db: AsyncSession = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(report_id=report_id)
    return await submit_report_service(db, valid_user, report_id)


@router.post("/{report_id}/review", response_model=Report)
async def review_report_view(
    report_id: UUID,
    review: ReportReviewRequest,
    db: AsyncSession = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(report_id=report_id)
    return await review_report_service(
        db, valid_user, report_id, review.decision, review.review_notes
    )


@router.post("/{report_id}/reopen", response_model=Report)
async def reopen_report_view(
    report_id: UUID, db: AsyncSession = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(report_id=report_id)
    return await reopen_report_service(db, valid_user, report_id)
