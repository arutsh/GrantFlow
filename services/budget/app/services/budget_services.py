import asyncio
import structlog
from fastapi import status, HTTPException
from app.crud.budget_crud import (
    create_budget,
    get_budget,
    update_budget,
    list_budgets,
    delete_budget,
    get_funded_budgets_summary,
    get_funded_grantees,
)
from app.crud.budget_line_crud import delete_budget_line
from app.core.exceptions import DomainError, PermissionDenied

from app.services.customer_client import validate_customer_can_fund, validate_customer_can_own
from app.schemas.budget_schema import BudgetCreate, BudgetStatus
from app.schemas.with_lines_schema import CreateBudgetWithLinesRequest
from uuid import UUID

from typing import List
from app.models import BudgetModel

from app.services.user_client import get_customers_by_ids
from app.services.user_cache import get_users_by_ids_cached

logger = structlog.get_logger(__name__)


async def create_budget_service(
    budget: BudgetCreate,
    valid_user: dict,
    db,
    include_user_datails: bool = False,
    budget_status: BudgetStatus | None = None,
):

    if budget.funding_customer_id:
        validate_customer_can_fund(budget.funding_customer_id, raise_domain_error=True)

    owner_id = valid_user.get("customer_id")

    if valid_user["role"] == "superuser":
        if not budget.owner_id:
            # FIXME: Temp workaround to allow superusers to create budgets
            # without specifying an owner_id.
            budget.owner_id = "444b3399-88ef-454f-b353-f160d3c9b44e"
            # raise DomainError(
            #     "Superuser must specify owner_id (not associated with a customer).",
            #     status.HTTP_422_UNPROCESSABLE_ENTITY,
            # )
        # TODO revisit this, do we really need to validate if user is ngo or donor?
        # validate_customer_type(budget.owner_id, "ngo", raise_domain_error=True)

        owner_id = budget.owner_id
    new_budget = create_budget(
        session=db,
        user_id=valid_user["user_id"],
        name=budget.name,
        funding_customer_id=budget.funding_customer_id,
        external_funder_name=budget.external_funder_name,
        owner_id=owner_id,
        status=budget_status,
    )
    if not include_user_datails:
        return new_budget
    result = await populate_budget_with_user_details([new_budget], valid_user=valid_user)

    return result[0]


async def update_budget_service(budget_id: UUID, budget: BudgetCreate, valid_user: dict, db):

    if budget.funding_customer_id:
        validate_customer_can_fund(budget.funding_customer_id, raise_domain_error=True)

    valid_budget = await get_budget_service(budget_id=budget_id, valid_user=valid_user, db=db)

    owner_id = valid_user["customer_id"]

    if valid_user["role"] == "superuser" and budget.owner_id:
        validate_customer_can_own(budget.owner_id, raise_domain_error=True)
        owner_id = budget.owner_id

    elif valid_user["role"] != "superuser":
        # checks if customer has right to update the budget
        if (budget.owner_id and valid_budget.owner_id != budget.owner_id) or (
            valid_user["customer_id"] != valid_budget.owner_id
        ):
            raise PermissionDenied()

    if budget.status == BudgetStatus.confirmed:
        effective_start_date = budget.start_date or valid_budget.start_date
        if not effective_start_date:
            raise DomainError(
                "start_date must be set before a budget can be confirmed",
                status.HTTP_400_BAD_REQUEST,
            )

    return update_budget(
        session=db,
        budget_id=budget_id,
        name=budget.name,
        status=budget.status,
        duration_months=budget.duration_months,
        local_currency=budget.local_currency,
        actual_currency=budget.actual_currency,
        start_date=budget.start_date,
        owner_id=owner_id,
        funding_customer_id=budget.funding_customer_id,
        external_funder_name=budget.external_funder_name,
    )


async def get_budget_service(budget_id, valid_user, db, include_user_details: bool = False):

    budget = (
        get_budget(db, budget_id)
        if valid_user["role"] == "superuser"
        else get_budget(db, budget_id, valid_user["customer_id"])
    )
    if not budget:
        raise DomainError(
            "Budget Not found",
            status.HTTP_400_BAD_REQUEST,
        )
    if not include_user_details:
        return budget
    result = await populate_budget_with_user_details([budget], valid_user)
    return result[0]


def _can_view_budget(budget: BudgetModel, valid_user: dict) -> bool:
    if valid_user["role"] == "superuser":
        return True
    customer_id = valid_user.get("customer_id")
    if not customer_id:
        return False
    return str(budget.owner_id) == str(customer_id) or str(budget.funding_customer_id) == str(
        customer_id
    )


async def get_viewable_budget_service(
    budget_id, valid_user, db, include_user_details: bool = False
):
    """Like get_budget_service, but a donor who funds this budget (not just its
    owner) can also view it. Used only by the read/detail route — update and
    delete keep the stricter owner-only get_budget_service unchanged."""
    budget = get_budget(db, budget_id)
    if not budget or not _can_view_budget(budget, valid_user):
        raise DomainError(
            "Budget Not found",
            status.HTTP_400_BAD_REQUEST,
        )
    if not include_user_details:
        return budget
    result = await populate_budget_with_user_details([budget], valid_user)
    return result[0]


async def list_budget_service(valid_user, db, include_user_details: bool = False):
    if valid_user["role"] == "superuser":
        return list_budgets(db)

    customer_id = valid_user.get("customer_id")
    if not customer_id:
        return []

    budgets = list_budgets(db, customer_id=customer_id)
    if not include_user_details:
        return budgets
    return await populate_budget_with_user_details(budgets=budgets, valid_user=valid_user)


def get_funded_budgets_summary_service(funding_customer_id: UUID, db) -> dict:
    return get_funded_budgets_summary(db, funding_customer_id)


# TODO return in pydantic?
async def get_funded_grantees_service(funding_customer_id: UUID, valid_user: dict, db) -> list:
    grantees = get_funded_grantees(db, funding_customer_id)
    owner_ids = [g["owner_id"] for g in grantees if g["owner_id"]]
    try:
        customers_map = await get_customers_by_ids(owner_ids, valid_user.get("token", ""))
    except Exception as exc:
        logger.warning("get_funded_grantees_service: customer lookup failed", error=str(exc))
        customers_map = {}
    return [
        {
            "id": g["owner_id"],
            "name": (customers_map.get(g["owner_id"]) or {}).get("name"),
            "country": (customers_map.get(g["owner_id"]) or {}).get("country"),
            "budgets_count": g["budgets_count"],
            "total_allocated_by_currency": g["total_allocated_by_currency"],
        }
        for g in grantees
    ]


async def get_funded_budgets_service(funding_customer_id: UUID, valid_user: dict, db) -> list:
    budgets = list_budgets(db, funding_customer_id=funding_customer_id)
    return await populate_budget_with_user_details(budgets=budgets, valid_user=valid_user)


async def delete_budget_service(budget_id: UUID, valid_user: dict, db):
    # fetch valid budget, if user does not have access relevant error will be raised
    valid_budget = await get_budget_service(budget_id=budget_id, valid_user=valid_user, db=db)

    if valid_budget:
        return delete_budget(session=db, budget=valid_budget)
    return False


async def create_budget_with_lines_service(
    request: CreateBudgetWithLinesRequest,
    valid_user: dict,
    db,
):
    # Deferred import to avoid circular dependency
    from app.services.budget_line_services import create_budget_line_service
    from app.schemas import BudgetLineCreate

    new_budget = None
    created_lines = []
    try:
        owner_id = request.owner_id or valid_user.get("customer_id")
        new_budget = await create_budget_service(
            BudgetCreate(
                name=request.budget_name,
                external_funder_name=request.external_funder_name,
                owner_id=owner_id,
                duration_months=request.duration_months,
            ),
            valid_user,
            db,
            budget_status=BudgetStatus.ai_draft,
        )

        for line_input in request.lines:
            line = create_budget_line_service(
                db,
                valid_user,
                BudgetLineCreate(
                    budget_id=new_budget.id,
                    description=line_input.description,
                    amount=line_input.amount,
                    category_name=line_input.category_name,
                    extra_fields=line_input.extra_fields,
                ),
            )
            created_lines.append(line)

        from app.schemas.budget_line_schema import BudgetLine

        enriched = await get_budget_service(
            new_budget.id, valid_user, db, include_user_details=True
        )
        enriched["lines"] = [BudgetLine.model_validate(ln) for ln in created_lines]
        return enriched

    except (HTTPException, DomainError):
        # Validation/permission errors — roll back any lines created before re-raising
        for line in reversed(created_lines):
            delete_budget_line(db, line)
        if new_budget:
            delete_budget(db, new_budget)
        raise
    except Exception as e:
        # Unexpected DB/infra error — compensating transaction then 500
        for line in reversed(created_lines):
            delete_budget_line(db, line)
        if new_budget:
            delete_budget(db, new_budget)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create budget with lines. Changes have been rolled back.",
        ) from e


async def populate_budget_with_user_details(budgets: List[BudgetModel], valid_user: dict):
    # Collect unique user and customer IDs
    user_ids = {b.created_by for b in budgets if b.created_by}
    user_ids |= {b.updated_by for b in budgets if b.updated_by}
    customer_ids = {b.funding_customer_id for b in budgets if b.funding_customer_id}
    customer_ids |= {b.owner_id for b in budgets if b.owner_id}
    user_ids = user_ids if user_ids else set()
    customer_ids = customer_ids if customer_ids else set()
    # Fetch users/customers concurrently (users from cache with fallback, customers from HTTP)
    users_task = asyncio.create_task(
        get_users_by_ids_cached(list(user_ids), valid_user.get("token", ""))
    )
    customers_task = asyncio.create_task(
        get_customers_by_ids(list(customer_ids), valid_user.get("token", ""))
    )
    try:
        users_map, customers_map = await asyncio.gather(users_task, customers_task)
    except Exception:
        users_map, customers_map = {}, {}

    # Merge enriched data
    enriched = [
        {
            "id": b.id,
            "name": b.name,
            "status": b.status,
            "duration_months": b.duration_months,
            "local_currency": b.local_currency,
            "total_amount": b.total_amount,
            "owner": customers_map.get(b.owner_id),
            "funder": customers_map.get(b.funding_customer_id) or {"name": b.external_funder_name},
            "trace": {
                "created": {
                    "user": users_map.get(b.created_by),
                    "event_date": b.created_at,
                },
                "updated": {
                    "user": users_map.get(b.updated_by),
                    "event_date": b.updated_at,
                },
            },
        }
        for b in budgets
    ]
    return enriched
