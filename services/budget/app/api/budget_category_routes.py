# /services/budget/app/api/budget_category_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.schemas import BudgetCategory, BudgetCategoryUpdate
from app.services.budget_category_services import (
    list_budget_categories_service,
    update_budget_category_service,
    delete_budget_category_service,
)
from shared.observability import set_span_attributes
from shared.security.dependencies import get_validated_user  # noqa: F401

router = APIRouter(prefix="/budget-categories", tags=["Budget Categories"])


@router.get("/by-budget/{budget_id}", response_model=List[BudgetCategory])
async def list_budget_categories_view(
    budget_id: UUID, db: AsyncSession = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(budget_id=budget_id)
    return await list_budget_categories_service(db, valid_user, budget_id)


@router.patch("/{category_id}", response_model=BudgetCategory)
async def update_budget_category_view(
    category_id: UUID,
    payload: BudgetCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(budget_category_id=category_id)
    update_data = payload.model_dump(exclude_unset=True)
    return await update_budget_category_service(db, valid_user, category_id, update_data)


@router.delete("/{category_id}")
async def delete_budget_category_view(
    category_id: UUID, db: AsyncSession = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(budget_category_id=category_id)
    return await delete_budget_category_service(db, valid_user, category_id)
