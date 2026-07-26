import os
import uuid
from fastapi import UploadFile, status
from uuid import UUID

from app.crud.attachment_crud import (
    create_attachment,
    get_attachment,
    list_attachments,
    delete_attachment,
)
from app.core.exceptions import DomainError
from app.schemas.report_schema import ReportStatus
from app.services.report_line_services import _get_report_line_or_404
from app.services.report_services import (
    _get_owned_report,
    _get_viewable_budget,
    _get_report_or_404,
)
from app.services.storage_client import storage_client

MAX_ATTACHMENT_SIZE = 15 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/heic"}


def _get_attachment_or_404(db, attachment_id: UUID):
    attachment = get_attachment(db, attachment_id)
    if not attachment:
        raise DomainError("Attachment Not found", status.HTTP_400_BAD_REQUEST)
    return attachment


def _storage_key(budget_id: UUID, report_line_id: UUID, filename: str) -> str:
    return f"attachments/{budget_id}/{report_line_id}/{uuid.uuid4()}_{filename}"


def _sniff_content_type(data: bytes) -> str | None:
    """Identify a file's actual type from its magic bytes. The client-supplied
    Content-Type header is trivially spoofable, so the allowlist check must
    also hold against what the bytes actually are, not just what the upload
    claims to be."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if (
        len(data) >= 12
        and data[4:8] == b"ftyp"
        and data[8:12]
        in (
            b"heic",
            b"heix",
            b"hevc",
            b"hevx",
            b"mif1",
            b"msf1",
        )
    ):
        return "image/heic"
    return None


def upload_attachment_service(db, valid_user: dict, report_line_id: UUID, file: UploadFile):
    report_line = _get_report_line_or_404(db, report_line_id)
    report = _get_owned_report(db, valid_user, report_line.report_id)
    if report.status != ReportStatus.draft:
        raise DomainError(
            "Attachments can only be uploaded to a draft report", status.HTTP_400_BAD_REQUEST
        )

    if not file.filename or file.content_type not in ALLOWED_CONTENT_TYPES:
        raise DomainError(
            "Unsupported file type; allowed types are PDF, JPEG, PNG, HEIC",
            status.HTTP_400_BAD_REQUEST,
        )

    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_ATTACHMENT_SIZE:
        raise DomainError("File exceeds the 15MB upload limit", status.HTTP_400_BAD_REQUEST)

    data = file.file.read()
    if _sniff_content_type(data) != file.content_type:
        raise DomainError(
            "File content does not match its declared type", status.HTTP_400_BAD_REQUEST
        )

    filename = file.filename
    storage_key = _storage_key(report.budget_id, report_line_id, filename)
    storage_client.save(storage_key, data, content_type=file.content_type)

    return create_attachment(
        session=db,
        user_id=valid_user["user_id"],
        report_line_id=report_line_id,
        filename=filename,
        content_type=file.content_type,
        size=len(data),
        storage_key=storage_key,
    )


def list_attachments_service(db, valid_user: dict, report_line_id: UUID):
    report_line = _get_report_line_or_404(db, report_line_id)
    report = _get_report_or_404(db, report_line.report_id)
    _get_viewable_budget(db, valid_user, report.budget_id)
    return list_attachments(db, report_line_id=report_line_id)


def download_attachment_service(db, valid_user: dict, attachment_id: UUID):
    attachment = _get_attachment_or_404(db, attachment_id)
    report_line = _get_report_line_or_404(db, attachment.report_line_id)
    report = _get_report_or_404(db, report_line.report_id)
    _get_viewable_budget(db, valid_user, report.budget_id)
    stream = storage_client.open_stream(attachment.storage_key)
    return attachment, stream


def get_attachment_download_url_service(db, valid_user: dict, attachment_id: UUID) -> str:
    attachment = _get_attachment_or_404(db, attachment_id)
    report_line = _get_report_line_or_404(db, attachment.report_line_id)
    report = _get_report_or_404(db, report_line.report_id)
    _get_viewable_budget(db, valid_user, report.budget_id)
    return storage_client.presigned_download_url(
        attachment.storage_key,
        content_type=attachment.content_type,
        filename=attachment.filename,
    )


def delete_attachment_service(db, valid_user: dict, attachment_id: UUID):
    attachment = _get_attachment_or_404(db, attachment_id)
    report_line = _get_report_line_or_404(db, attachment.report_line_id)
    report = _get_owned_report(db, valid_user, report_line.report_id)
    if report.status != ReportStatus.draft:
        raise DomainError(
            "Attachments can only be deleted on a draft report", status.HTTP_400_BAD_REQUEST
        )
    # Remove the DB reference before the blob: if the blob delete below
    # fails, the result is an orphaned blob (harmless, cleaned up later),
    # never a dangling row that still looks downloadable.
    storage_key = attachment.storage_key
    delete_attachment(db, attachment)
    storage_client.delete(storage_key)
    return True
