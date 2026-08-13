# /services/budget/app/api/budget_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.session import SessionLocal
from app.schemas import BudgetLine, BudgetLineCreate, BudgetLineUpdate
from uuid import UUID
from app.services.budget_line_services import (
    create_budget_line_service,
    get_budget_lines_service,
    get_budget_line_by_id_service,
    update_budget_line_service,
    delete_budget_line_service,
)
from shared.observability import set_span_attributes
from shared.security.dependencies import get_validated_user  # noqa: F401

router = APIRouter(prefix="/budget-lines", tags=["Budget Lines"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[BudgetLine])
def get_budget_lines_view(db: Session = Depends(get_db), valid_user=Depends(get_validated_user)):
    return get_budget_lines_service(db, valid_user)


@router.post("/", response_model=BudgetLine)
def create_budget_line_view(
    budget_line: BudgetLineCreate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(budget_id=budget_line.budget_id)
    created_line = create_budget_line_service(db, valid_user, budget_line)
    set_span_attributes(budget_line_id=created_line.id)
    return created_line


@router.get("/by-budget/{budget_id}", response_model=List[BudgetLine])
def get_budget_lines_by_budget_view(
    budget_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(budget_id=budget_id)
    return get_budget_lines_service(db, budget_id=budget_id, valid_user=valid_user)


@router.get("/{budget_line_id}", response_model=BudgetLine)
def get_budget_line_by_id_view(
    budget_line_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(budget_line_id=budget_line_id)
    return get_budget_line_by_id_service(
        db,
        valid_user,
        budget_line_id,
    )


@router.patch("/{budget_line_id}/", response_model=BudgetLine)
def update_budget_line_view(
    budget_line_id: UUID,
    budget_line: BudgetLineUpdate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(budget_line_id=budget_line_id)
    return update_budget_line_service(
        db, valid_user=valid_user, budget_line_id=budget_line_id, new_budget_line=budget_line
    )


@router.delete("/{budget_line_id}/")
def delete_budget_line_view(
    budget_line_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(budget_line_id=budget_line_id)
    return delete_budget_line_service(budget_line_id=budget_line_id, valid_user=valid_user, db=db)
