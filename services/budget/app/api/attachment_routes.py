# /services/budget/app/api/attachment_routes.py
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import SessionLocal
from app.schemas.attachment_schema import Attachment
from app.services.attachment_services import (
    upload_attachment_service,
    list_attachments_service,
    download_attachment_service,
    get_attachment_download_url_service,
    delete_attachment_service,
)
from shared.observability import set_span_attributes
from shared.security.dependencies import get_validated_user  # noqa: F401
from shared.storage.storage_service import safe_content_disposition

router = APIRouter(prefix="/attachments", tags=["Attachments"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=Attachment)
def upload_attachment_view(
    report_line_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(report_line_id=report_line_id)
    uploaded = upload_attachment_service(db, valid_user, report_line_id, file)
    set_span_attributes(attachment_id=uploaded.id)
    return uploaded


@router.get("/by-report-line/{report_line_id}", response_model=List[Attachment])
def list_attachments_by_report_line_view(
    report_line_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(report_line_id=report_line_id)
    return list_attachments_service(db, valid_user, report_line_id)


@router.get("/{attachment_id}/content")
def download_attachment_view(
    attachment_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(attachment_id=attachment_id)
    attachment, stream = download_attachment_service(db, valid_user, attachment_id)
    return StreamingResponse(
        stream,
        media_type=attachment.content_type,
        headers={"Content-Disposition": safe_content_disposition(attachment.filename)},
    )


@router.get("/{attachment_id}/download-url")
def download_attachment_url_view(
    attachment_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(attachment_id=attachment_id)
    url = get_attachment_download_url_service(db, valid_user, attachment_id)
    return RedirectResponse(url, status_code=307)


@router.delete("/{attachment_id}")
def delete_attachment_view(
    attachment_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(attachment_id=attachment_id)
    return {"success": delete_attachment_service(db, valid_user, attachment_id)}
