from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class AttachmentBase(BaseModel):
    report_line_id: UUID | None = None
    filename: str | None = None
    content_type: str | None = None
    size: int | None = None
    storage_key: str | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    updated_at: datetime | None = None
    created_at: datetime | None = None


class Attachment(AttachmentBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)
