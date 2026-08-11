from datetime import datetime

from pydantic import BaseModel, EmailStr


class ConsentState(BaseModel):
    data_processing_granted: bool
    data_processing_at: datetime | None
    marketing_granted: bool
    marketing_at: datetime | None


class ConsentUpdateRequest(BaseModel):
    marketing: bool


class EmailChangeRequest(BaseModel):
    new_email: EmailStr
