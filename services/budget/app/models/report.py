# /services/budget/app/models/report.py
from __future__ import annotations
import uuid
from datetime import date, datetime
from sqlalchemy import String, ForeignKey, Float, JSON, Date, DateTime, Enum as SQLEnum, text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.utils.db import GUID

from app.models.base import Base

from shared.db.audit_mixin import AuditMixin
from typing import TYPE_CHECKING
from app.schemas.report_schema import ReportStatus

if TYPE_CHECKING:
    from app.models.budget import BudgetModel, BudgetLineModel


class ReportModel(Base, AuditMixin):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("budgets.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(ReportStatus, name="report_status"),
        nullable=False,
        default=ReportStatus.draft,
        server_default=text(f"'{ReportStatus.draft.value}'"),
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(String, nullable=True)

    budget: Mapped["BudgetModel"] = relationship("BudgetModel", back_populates="reports")
    lines: Mapped[list["ReportLineModel"]] = relationship(
        "ReportLineModel", back_populates="report"
    )


class ReportLineModel(Base, AuditMixin):
    __tablename__ = "report_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, index=True, default=lambda: uuid.uuid4()
    )
    report_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("reports.id"), nullable=False)
    budget_line_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("budget_lines.id"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    report: Mapped["ReportModel"] = relationship("ReportModel", back_populates="lines")
    budget_line: Mapped["BudgetLineModel"] = relationship(
        "BudgetLineModel", back_populates="report_lines"
    )
