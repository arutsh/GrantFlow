from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BugReportCreate(BaseModel):
    description: str
    page_path: str
    user_agent: str
    client_timestamp: datetime


class BugReport(BaseModel):
    id: UUID
    user_id: UUID
    description: str
    page_path: str
    user_agent: str
    client_timestamp: datetime
    screenshot_storage_key: str | None = None

    model_config = {"from_attributes": True}
