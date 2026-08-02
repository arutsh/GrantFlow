import asyncio
import structlog
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from fastapi import status, HTTPException
from sqlalchemy.exc import IntegrityError
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
from app.schemas.report_schema import ReportStatus
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


def is_budget_locked(budget) -> bool:
    """A confirmed budget's metadata and lines are frozen to keep reported
    figures accurate. Single source of truth for that rule — also used by
    budget_line_services._assert_budget_editable, so the two never drift."""
    return budget is not None and budget.status == BudgetStatus.confirmed


def _is_metadata_edit(budget: BudgetCreate) -> bool:
    """True if the payload touches anything beyond a bare status/start_date
    transition (confirm or revert-to-draft) or a currency-only update — i.e.
    name/duration/local_currency/funder/owner/donor_total_amount/
    estimated_exchange_rate fields. `actual_currency` is
    deliberately excluded: it's the donor-transfer currency the currency-
    ledger UI needs set, and the ledger's "set actual currency" prompt only
    ever appears on an already-confirmed budget (see budget-report-frontend
    tasks.md 6.7), so locking it the same as name/duration would make that
    flow permanently unreachable. A payload that also touches any other
    metadata field alongside actual_currency is still blocked as usual."""
    return any(
        value is not None
        for value in (
            budget.name,
            budget.duration_months,
            budget.local_currency,
            budget.external_funder_name,
            budget.funding_customer_id,
            budget.owner_id,
            budget.donor_total_amount,
            budget.estimated_exchange_rate,
        )
    )


def _resolve_updatable_budget(
    budget_id: UUID, valid_user: dict, is_confirm_attempt: bool, db
) -> tuple[BudgetModel, bool]:
    """Authorization for PATCH /budgets/{id}. Returns (budget, is_funder_confirm).

    The owner (or a superuser) may always act on their own budget. The one
    exception — a matching funder confirming a draft/ai_draft budget (see
    design.md's "Confirm access extends to the matching funder" decision) —
    is resolved here as an explicit authorization branch rather than by
    catching the owner-lookup's not-found error, so both paths are plain
    reads with no exception-driven control flow between them.
    """
    budget = get_budget(db, budget_id)
    if not budget:
        raise DomainError("Budget Not found", status.HTTP_400_BAD_REQUEST)

    if valid_user["role"] == "superuser" or str(budget.owner_id) == str(
        valid_user.get("customer_id")
    ):
        return budget, False

    if (
        is_confirm_attempt
        and budget.funding_customer_id
        and str(budget.funding_customer_id) == str(valid_user.get("customer_id"))
        and budget.status in (BudgetStatus.draft, BudgetStatus.ai_draft)
    ):
        return budget, True

    raise DomainError(
        "Budget Not found",
        status.HTTP_400_BAD_REQUEST,
    )


async def update_budget_service(budget_id: UUID, budget: BudgetCreate, valid_user: dict, db):

    if budget.funding_customer_id:
        validate_customer_can_fund(budget.funding_customer_id, raise_domain_error=True)

    # Broader than "a bare confirm with no other fields" — this also covers a
    # confirm bundled with a metadata edit, so both the archived/already-
    # confirmed guard below and the funder-metadata guard after the lookup
    # see the attempt regardless of what else is in the payload.
    is_confirm_attempt = budget.status == BudgetStatus.confirmed

    valid_budget, is_funder_confirm = _resolve_updatable_budget(
        budget_id, valid_user, is_confirm_attempt, db
    )

    if is_funder_confirm and _is_metadata_edit(budget):
        raise DomainError(
            "A funder can only confirm a budget, not edit its metadata",
            status.HTTP_400_BAD_REQUEST,
        )

    if is_confirm_attempt and valid_budget.status not in (
        BudgetStatus.draft,
        BudgetStatus.ai_draft,
    ):
        raise DomainError(
            "Only a draft or ai_draft budget can be confirmed",
            status.HTTP_400_BAD_REQUEST,
        )

    is_reverting = (
        valid_budget.status == BudgetStatus.confirmed
        and budget.status == BudgetStatus.draft
        and not _is_metadata_edit(budget)
    )

    if is_budget_locked(valid_budget) and (
        _is_metadata_edit(budget) or budget.start_date is not None
    ):
        raise DomainError(
            "Budget cannot be edited once it is confirmed",
            status.HTTP_400_BAD_REQUEST,
        )

    owner_id = None
    if valid_user["role"] == "superuser" and budget.owner_id:
        validate_customer_can_own(budget.owner_id, raise_domain_error=True)
        owner_id = budget.owner_id

    elif valid_user["role"] != "superuser" and not is_funder_confirm:
        # checks if customer has right to update the budget
        if (budget.owner_id and str(valid_budget.owner_id) != str(budget.owner_id)) or (
            str(valid_user["customer_id"]) != str(valid_budget.owner_id)
        ):
            raise PermissionDenied()

    if budget.status == BudgetStatus.confirmed:
        effective_start_date = budget.start_date or valid_budget.start_date
        if not effective_start_date:
            raise DomainError(
                "start_date must be set before a budget can be confirmed",
                status.HTTP_400_BAD_REQUEST,
            )

    # Set on every confirm transition (is_confirm_attempt is only reachable
    # here from draft/ai_draft, per the guard above) so a later revert +
    # reconfirm always overwrites the prior value, never left stale.
    confirmed_at = datetime.now(timezone.utc) if is_confirm_attempt else None

    if is_reverting:
        non_draft_reports = [r for r in valid_budget.reports if r.status != ReportStatus.draft]
        if non_draft_reports:
            raise DomainError(
                "Cannot revert to draft while the budget has a submitted, approved, "
                "or rejected report",
                status.HTTP_400_BAD_REQUEST,
            )
        # session.delete only — not crud.delete_report, which commits per
        # call. Batching these into the single commit below (alongside the
        # status change) turns the revert into one round trip instead of N,
        # and makes it atomic: if anything below still fails, nothing here
        # is persisted either.
        for report in list(valid_budget.reports):
            db.delete(report)

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
        donor_total_amount=budget.donor_total_amount,
        estimated_exchange_rate=budget.estimated_exchange_rate,
        confirmed_at=confirmed_at,
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
        try:
            return delete_budget(session=db, budget=valid_budget)
        except IntegrityError:
            db.rollback()
            raise DomainError(
                "Budget cannot be deleted while it has existing reports, funding receipts, "
                "or currency conversions",
                status.HTTP_400_BAD_REQUEST,
            )
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


def _compute_end_date(budget: BudgetModel):
    """Mirrors report_services.create_report_service's default period_end —
    the single source of truth for this formula, so the frontend displays
    end_date from here rather than reimplementing the math."""
    if not budget.start_date:
        return None
    return budget.start_date + relativedelta(months=budget.duration_months or 0)


def _compute_estimated_local_cap(budget: BudgetModel) -> float | None:
    """donor_total_amount × estimated_exchange_rate, derived at read time —
    never persisted (see design.md Decision 2). `null` when either input is
    unset or zero, not just when unset."""
    if not budget.donor_total_amount or not budget.estimated_exchange_rate:
        return None
    return budget.donor_total_amount * budget.estimated_exchange_rate


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
            "actual_currency": b.actual_currency,
            "start_date": b.start_date,
            "end_date": _compute_end_date(b),
            "total_amount": b.total_amount,
            "donor_total_amount": b.donor_total_amount,
            "estimated_exchange_rate": b.estimated_exchange_rate,
            "confirmed_at": b.confirmed_at,
            "estimated_local_cap": _compute_estimated_local_cap(b),
            "owner": customers_map.get(b.owner_id),
            # Preserve `id` from the budget's own funding_customer_id even
            # when the customer-name lookup is empty/failed, so a real
            # funder relationship still round-trips to the frontend's
            # isBudgetFunder check regardless of that lookup's health.
            "funder": customers_map.get(b.funding_customer_id)
            or (
                {"id": b.funding_customer_id, "name": b.external_funder_name}
                if b.funding_customer_id
                else {"name": b.external_funder_name}
            ),
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
