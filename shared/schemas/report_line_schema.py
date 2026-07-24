from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Any


class ReportLineBase(BaseModel):
    report_id: UUID | None = None
    budget_line_id: UUID | None = None
    description: str | None = None
    amount: float | None = None
    extra_fields: dict[str, Any] | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    updated_at: datetime | None = None
    created_at: datetime | None = None


class ReportLineCreate(ReportLineBase):
    report_id: UUID
    budget_line_id: UUID
    description: str
    amount: float


class ReportLineUpdate(BaseModel):
    report_id: UUID
    description: str | None = None
    amount: float | None = None
    extra_fields: dict[str, Any] | None = None


class ReportLine(ReportLineBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)
