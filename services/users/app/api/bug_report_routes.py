from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.bug_report_schema import BugReport
from app.services.bug_report_services import submit_bug_report_service
from shared.security.dependencies import get_validated_user

router = APIRouter(prefix="/bug-reports", tags=["Bug Reports"])


@router.post("/", response_model=BugReport)
def submit_bug_report_endpoint(
    description: str = Form(...),
    page_path: str = Form(...),
    user_agent: str = Form(...),
    client_timestamp: datetime = Form(...),
    last_api_call: str | None = Form(None),
    screenshot: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    valid_user: dict = Depends(get_validated_user),
):
    return submit_bug_report_service(
        db,
        valid_user,
        description=description,
        page_path=page_path,
        user_agent=user_agent,
        client_timestamp=client_timestamp,
        last_api_call=last_api_call,
        screenshot=screenshot,
    )
