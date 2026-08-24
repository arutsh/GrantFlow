from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field
from app.schemas.budget_line_schema import BudgetCategory


# Donor Template Schemas
class DonorTemplateBase(BaseModel):
    name: str = Field(min_length=2)


class DonorTemplateCreate(DonorTemplateBase):
    pass


class DonorTemplate(DonorTemplateBase):
    id: int
    categories: List[BudgetCategory] = []
    model_config = {"from_attributes": True}
