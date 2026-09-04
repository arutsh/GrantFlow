# /services/budget/app/schemas/budget.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import UUID
from shared.schemas.audit_mixin import AuditMixinBase


# Budget Line schema
class BudgetCategoryBase(BaseModel):
    name: str
    code: Optional[str] = None
    budget_id: UUID


class BudgetCategoryCreate(BudgetCategoryBase):
    pass


class BudgetCategoryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None


class BudgetCategory(BudgetCategoryBase, AuditMixinBase):
    id: UUID

    model_config = {"from_attributes": True}


class BudgetLineBase(BaseModel):

    budget_id: UUID
    description: str
    amount: float
    extra_fields: Optional[Dict[str, Any]] = None
    category_id: Optional[UUID] = None


class BudgetLineCreate(BudgetLineBase):
    category_name: str | None = None


class BudgetLineUpdate(BaseModel):
    budget_id: UUID
    description: str | None = None
    amount: Optional[float] = None
    extra_fields: Optional[Dict[str, Any]] = None
    category_id: Optional[UUID] = None


class BudgetLine(BudgetLineBase, AuditMixinBase):
    id: UUID
    category: Optional[BudgetCategory] = None
    model_config = {"from_attributes": True}


class BudgetLinesResponse(BaseModel):
    budget_lines: List[BudgetLine]
