from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.schemas.mapping_schema import (
    DonorTemplateCreate,
    DonorTemplate,
)
from app.db.session import SessionLocal
from app.crud.budget_donor_template_crud import (
    create_donor_template,
    get_donor_template,
    list_donor_templates,
)
from app.schemas.budget_line_schema import BudgetCategoryCreate, BudgetCategory
from app.crud.budget_category_crud import create_budget_category, list_budget_categories
from shared.observability import set_span_attributes
from shared.security.dependencies import get_validated_user  # noqa: F401

router = APIRouter(prefix="/donor-mapping", tags=["Donor Mapping"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_template_or_404(db: Session, template_id: int):
    template = get_donor_template(db, template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    return template


# --- Templates ---
@router.post("/templates", response_model=DonorTemplate)
def create_template(
    payload: DonorTemplateCreate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    created_template = create_donor_template(db, payload.name)
    set_span_attributes(donor_template_id=created_template.id)
    return created_template


@router.get("/templates", response_model=List[DonorTemplate])
def list_templates(db: Session = Depends(get_db), valid_user=Depends(get_validated_user)):
    return list_donor_templates(db)


@router.post("/categories", response_model=BudgetCategory)
def create_budget_category_endpoint(
    payload: BudgetCategoryCreate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(donor_template_id=payload.donor_template_id)
    if payload.donor_template_id is not None:
        _get_template_or_404(db, payload.donor_template_id)
    created_category = create_budget_category(
        db,
        user_id=valid_user["user_id"],
        name=payload.name,
        code=payload.code,
        donor_template_id=payload.donor_template_id,
    )
    set_span_attributes(budget_category_id=created_category.id)
    return created_category


@router.get("/categories", response_model=List[BudgetCategory])
def list_budget_categories_view(
    db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return list_budget_categories(db)


@router.get("/categories/{template_id}", response_model=List[BudgetCategory])
def list_budget_categories_by_template(
    template_id: int, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(donor_template_id=template_id)
    return list_budget_categories(db, template_id)
