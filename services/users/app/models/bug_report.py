import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.utils.db import GUID
from shared.db.audit_mixin import AuditMixin


class BugReportModel(Base, AuditMixin):
    __tablename__ = "bug_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, index=True, default=lambda: uuid.uuid4()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    page_path: Mapped[str] = mapped_column(String, nullable=False)
    user_agent: Mapped[str] = mapped_column(String, nullable=False)
    client_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    screenshot_storage_key: Mapped[str | None] = mapped_column(String, nullable=True)
