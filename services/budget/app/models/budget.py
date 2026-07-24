# /services/budget/app/models/budget.py
from __future__ import annotations
import uuid
from datetime import date
from sqlalchemy import String, ForeignKey, Float, JSON, Integer, Date, Enum as SQLEnum, text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.utils.db import GUID

from app.models.base import Base

from shared.db.audit_mixin import AuditMixin
from typing import TYPE_CHECKING
from app.schemas.budget_schema import BudgetStatus

if TYPE_CHECKING:
    from app.models.mapping import DonorTemplateModel
    from app.models.report import ReportModel, ReportLineModel


class BudgetModel(Base, AuditMixin):
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        index=True,
        default=lambda: str(uuid.uuid4()),  # auto-generate UUID4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    funding_customer_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    external_funder_name: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    local_currency: Mapped[str | None] = mapped_column(String(3), nullable=False, default="GBP")
    actual_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[BudgetStatus] = mapped_column(
        SQLEnum(BudgetStatus, name="budget_status"),
        nullable=False,
        default=BudgetStatus.draft,
        server_default=text(f"'{BudgetStatus.draft.value}'"),
    )
    donor_template_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("donor_templates.id"), nullable=True
    )
    total_amount: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=0, server_default=text("0")
    )
    lines: Mapped[list["BudgetLineModel"]] = relationship(
        "BudgetLineModel", back_populates="budget"
    )
    reports: Mapped[list["ReportModel"]] = relationship("ReportModel", back_populates="budget")


class BudgetLineModel(Base, AuditMixin):
    __tablename__ = "budget_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, index=True, default=lambda: uuid.uuid4()
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("budgets.id"), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("budget_categories.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    # store arbitrary metadata (JSON column, default empty dict)
    extra_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    budget: Mapped["BudgetModel"] = relationship("BudgetModel", back_populates="lines")
    category: Mapped["BudgetCategoryModel"] = relationship(
        "BudgetCategoryModel", back_populates="lines"
    )
    report_lines: Mapped[list["ReportLineModel"]] = relationship(
        "ReportLineModel", back_populates="budget_line"
    )


class BudgetCategoryModel(Base, AuditMixin):
    __tablename__ = "budget_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, index=True, default=lambda: uuid.uuid4()
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    donor_template_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("donor_templates.id", ondelete="CASCADE"), nullable=True
    )

    donor_template: Mapped["DonorTemplateModel"] = relationship(
        "DonorTemplateModel", back_populates="categories"
    )

    lines: Mapped[list["BudgetLineModel"]] = relationship(
        "BudgetLineModel", back_populates="category"
    )
