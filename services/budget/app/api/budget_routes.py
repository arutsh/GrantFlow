# /services/budget/app/api/budget_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
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
    GranteeDashboardSummary,
)
from app.schemas.budget_line_schema import BudgetLine
from app.schemas.with_lines_schema import CreateBudgetWithLinesRequest
from app.services.budget_line_services import get_viewable_budget_lines_service
from app.services.budget_services import (
    create_budget_service,
    create_budget_with_lines_service,
    get_viewable_budget_service,
    update_budget_service,
    restore_budget_service,
    list_budget_service,
    delete_budget_service,
    get_funded_budgets_summary_service,
    get_funded_grantees_service,
    get_funded_budgets_service,
    get_grantee_dashboard_summary_service,
)
from app.services.customer_client import require_donor
from app.crud.budget_crud import get_budgets_by_creator
from shared.observability import set_span_attributes
from shared.security.dependencies import get_validated_user

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
    result = await create_budget_service(budget, valid_user, db, include_user_datails=True)
    set_span_attributes(budget_id=result["id"])
    return result


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


@router.get("/dashboard/summary", response_model=GranteeDashboardSummary)
async def get_dashboard_summary_endpoint(
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    # get_grantee_dashboard_summary_service is a plain sync function running
    # five queries against a sync SQLAlchemy Session — calling it directly
    # here would block the event loop for every other request while it runs.
    return await run_in_threadpool(
        get_grantee_dashboard_summary_service, valid_user.get("customer_id"), db
    )


@router.get("/{budget_id}", response_model=BudgetWithLines)
async def get_budget_endpoint(
    budget_id: UUID,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(budget_id=budget_id)
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
    set_span_attributes(budget_id=budget_id)
    updated_budget = await update_budget_service(
        budget_id=budget_id, budget=budget, valid_user=valid_user, db=db
    )
    if not updated_budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return updated_budget


@router.post("/{budget_id}/restore", response_model=BudgetUpdate)
async def restore_budget_endpoint(
    budget_id: UUID,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(budget_id=budget_id)
    updated_budget = await restore_budget_service(budget_id=budget_id, valid_user=valid_user, db=db)
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
    set_span_attributes(budget_id=budget_id)
    return {
        "success": await delete_budget_service(budget_id=budget_id, valid_user=valid_user, db=db)
    }


@router.get("/by-creator/{user_id}")
def get_budgets_by_creator_endpoint(
    user_id: UUID,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    # Called by the users service to build a data-subject data-export — the
    # users service forwards the requesting user's own token, so this is
    # self-service only, same as delete_my_account. Unlike /customers/by_ids/,
    # this sits on the public router with no gateway-level path exclusion, so
    # it must enforce this itself rather than trust the "internal" convention.
    if str(valid_user["user_id"]) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to view this user's budgets")
    return [
        {"id": str(b.id), "name": b.name, "type": "budget", "created_at": b.created_at}
        for b in get_budgets_by_creator(db, user_id)
    ]
