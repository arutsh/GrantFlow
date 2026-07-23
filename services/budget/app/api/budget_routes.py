# /services/budget/app/api/budget_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import uuid4, UUID  # noqa: F401

from app.db.session import SessionLocal
from app.schemas.budget_schema import (
    BudgetCreate,
    BudgetUpdate,
    BudgetWithLines,
    FundedBudgetsSummary,
    GranteeSummary,
    FundedBudgetListItem,
)
from app.schemas.budget_line_schema import BudgetLine
from app.schemas.with_lines_schema import CreateBudgetWithLinesRequest
from app.services.budget_line_services import get_viewable_budget_lines_service
from app.services.budget_services import (
    create_budget_service,
    create_budget_with_lines_service,
    get_viewable_budget_service,
    update_budget_service,
    list_budget_service,
    delete_budget_service,
    get_funded_budgets_summary_service,
    get_funded_grantees_service,
    get_funded_budgets_service,
)
from app.services.customer_client import require_donor
from shared.security.dependencies import get_validated_user  # noqa: F401

router = APIRouter(prefix="/budgets", tags=["Public Budgets"])
private_router = APIRouter(prefix="/budgets", tags=["Private Budgets"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
async def create_budget_endpoint(
    budget: BudgetCreate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    return await create_budget_service(budget, valid_user, db, include_user_datails=True)


@router.get("/funded/summary", response_model=FundedBudgetsSummary)
async def get_funded_budgets_summary_endpoint(
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    require_donor(valid_user)
    return get_funded_budgets_summary_service(valid_user["customer_id"], db)


@router.get("/funded/grantees", response_model=list[GranteeSummary])
async def get_funded_grantees_endpoint(
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    require_donor(valid_user)
    return await get_funded_grantees_service(valid_user["customer_id"], valid_user, db)


@router.get("/funded/", response_model=list[FundedBudgetListItem])
async def get_funded_budgets_endpoint(
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    require_donor(valid_user)
    return await get_funded_budgets_service(valid_user["customer_id"], valid_user, db)


@router.get("/{budget_id}", response_model=BudgetWithLines)
async def get_budget_endpoint(
    budget_id: UUID,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    budget = await get_viewable_budget_service(budget_id, valid_user, db, include_user_details=True)
    if budget:
        budget_lines = get_viewable_budget_lines_service(
            db=db, valid_user=valid_user, budget_id=budget_id
        )
        budget["lines"] = [BudgetLine.model_validate(line) for line in budget_lines]
    return budget


@router.patch("/{budget_id}", response_model=BudgetUpdate)
async def update_budget_endpoint(
    budget_id: UUID,
    budget: BudgetUpdate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    updated_budget = await update_budget_service(
        budget_id=budget_id, budget=budget, valid_user=valid_user, db=db
    )
    if not updated_budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return updated_budget


@router.get("/")
async def get_all_budgets_endpoint(
    db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):

    return await list_budget_service(db=db, valid_user=valid_user, include_user_details=True)


@router.post("/with-lines")
async def create_budget_with_lines_endpoint(
    request: CreateBudgetWithLinesRequest,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    return await create_budget_with_lines_service(request, valid_user, db)


@router.delete("/{budget_id}")
async def delete_budget_endpoint(
    budget_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return {
        "success": await delete_budget_service(budget_id=budget_id, valid_user=valid_user, db=db)
    }
