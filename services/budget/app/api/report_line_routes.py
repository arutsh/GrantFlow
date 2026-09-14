# /services/budget/app/api/report_line_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.schemas.report_line_schema import ReportLine, ReportLineCreate, ReportLineUpdate
from app.services.report_line_services import (
    create_report_line_service,
    get_report_line_by_id_service,
    list_report_lines_service,
    update_report_line_service,
    delete_report_line_service,
)
from shared.observability import set_span_attributes
from shared.security.dependencies import get_validated_user  # noqa: F401

router = APIRouter(prefix="/report-lines", tags=["Report Lines"])


@router.post("/", response_model=ReportLine)
async def create_report_line_view(
    report_line: ReportLineCreate,
    db: AsyncSession = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(report_id=report_line.report_id)
    created_line = await create_report_line_service(db, valid_user, report_line)
    set_span_attributes(report_line_id=created_line.id)
    return created_line


@router.get("/by-report/{report_id}", response_model=List[ReportLine])
async def list_report_lines_by_report_view(
    report_id: UUID, db: AsyncSession = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(report_id=report_id)
    return await list_report_lines_service(db, valid_user, report_id)


@router.get("/{report_line_id}", response_model=ReportLine)
async def get_report_line_view(
    report_line_id: UUID,
    db: AsyncSession = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(report_line_id=report_line_id)
    return await get_report_line_by_id_service(db, valid_user, report_line_id)


@router.patch("/{report_line_id}", response_model=ReportLine)
async def update_report_line_view(
    report_line_id: UUID,
    report_line: ReportLineUpdate,
    db: AsyncSession = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(report_line_id=report_line_id)
    return await update_report_line_service(db, valid_user, report_line_id, report_line)


@router.delete("/{report_line_id}")
async def delete_report_line_view(
    report_line_id: UUID,
    db: AsyncSession = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(report_line_id=report_line_id)
    return {"success": await delete_report_line_service(db, valid_user, report_line_id)}
