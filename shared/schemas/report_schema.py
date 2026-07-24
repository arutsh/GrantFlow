from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import date, datetime
from enum import Enum

from shared.schemas.report_line_schema import ReportLine


class ReportStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


class ReportBase(BaseModel):
    budget_id: UUID | None = None
    name: str | None = None
    status: ReportStatus = ReportStatus.draft
    period_start: date | None = None
    period_end: date | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by: UUID | None = None
    review_notes: str | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    updated_at: datetime | None = None
    created_at: datetime | None = None


class ReportCreate(ReportBase):
    budget_id: UUID
    name: str


class ReportUpdate(ReportBase):
    id: UUID | None = None


class Report(ReportBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class ReportWithLines(Report):
    lines: list[ReportLine] = []


class ReportReviewRequest(BaseModel):
    decision: ReportStatus
    review_notes: str | None = None
