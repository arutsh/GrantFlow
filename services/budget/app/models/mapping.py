from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, JSON
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.budget import BudgetCategoryModel


class DonorTemplateModel(Base):
    __tablename__ = "donor_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Normalized structure fingerprint used to recognize a donor's layout
    # again (by any organization) and skip AI extraction on a match.
    fingerprint: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    # AI-derived (or fingerprint-matched) extraction mapping for this layout.
    detected_structure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Reserved for future template-versioning/export work; not diffed in v1.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    categories: Mapped[list["BudgetCategoryModel"]] = relationship(
        back_populates="donor_template", cascade="all, delete-orphan"
    )
