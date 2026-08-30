import os
import uuid
from datetime import datetime

from fastapi import UploadFile, status

from app.core.exceptions import DomainError
from app.core.logging import get_logger
from app.crud.bug_report_crud import create_bug_report
from app.services.celery_client import enqueue_bug_report_notification
from app.services.storage_client import storage_client

logger = get_logger(__name__)

MAX_SCREENSHOT_SIZE = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


def _sniff_content_type(data: bytes) -> str | None:
    """Identify a file's actual type from its magic bytes — the client-supplied
    Content-Type header is trivially spoofable."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _storage_key(bug_report_id: uuid.UUID, filename: str) -> str:
    return f"bug-reports/{bug_report_id}/{uuid.uuid4()}_{filename}"


def _validate_and_read_screenshot(file: UploadFile) -> tuple[bytes, str]:
    if not file.filename or file.content_type not in ALLOWED_CONTENT_TYPES:
        raise DomainError(
            "Unsupported file type; allowed types are PNG, JPEG, WebP",
            status.HTTP_400_BAD_REQUEST,
        )

    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_SCREENSHOT_SIZE:
        raise DomainError("Screenshot exceeds the 5MB upload limit", status.HTTP_400_BAD_REQUEST)

    data = file.file.read()
    if _sniff_content_type(data) != file.content_type:
        raise DomainError(
            "File content does not match its declared type", status.HTTP_400_BAD_REQUEST
        )
    return data, file.filename


def submit_bug_report_service(
    db,
    valid_user: dict,
    description: str,
    page_path: str,
    user_agent: str,
    client_timestamp: datetime,
    screenshot: UploadFile | None = None,
):
    bug_report_id = uuid.uuid4()
    screenshot_storage_key = None
    if screenshot is not None:
        data, filename = _validate_and_read_screenshot(screenshot)
        screenshot_storage_key = _storage_key(bug_report_id, filename)
        storage_client.save(screenshot_storage_key, data, content_type=screenshot.content_type)

    bug_report = create_bug_report(
        db,
        bug_report_id=bug_report_id,
        user_id=valid_user["user_id"],
        description=description,
        page_path=page_path,
        user_agent=user_agent,
        client_timestamp=client_timestamp,
        screenshot_storage_key=screenshot_storage_key,
    )

    # Report is already committed; notification failure must not fail the request.
    try:
        enqueue_bug_report_notification(
            bug_report_id=bug_report.id,
            description=description,
            page_path=page_path,
            user_agent=user_agent,
            client_timestamp=client_timestamp.isoformat(),
            screenshot_storage_key=screenshot_storage_key,
        )
    except Exception:
        logger.exception(
            "bug_report_notification_enqueue_failed", bug_report_id=str(bug_report.id)
        )

    return bug_report
