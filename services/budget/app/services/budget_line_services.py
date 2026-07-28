from fastapi import status
from app.crud.budget_crud import (
    get_budget,
    list_budgets,
    recalculate_budget_total,
)
from app.crud.budget_line_crud import (
    create_budget_line,
    get_budget_line,
    list_budget_lines,
    update_budget_line,
    delete_budget_line,
)
from app.core.exceptions import DomainError, PermissionDenied
from app.services.budget_category_services import get_or_create_category_service
from app.services.budget_services import is_budget_locked
from uuid import UUID
from app.schemas import BudgetLineCreate, BudgetLineUpdate


def _assert_budget_editable(budget) -> None:
    if is_budget_locked(budget):
        raise DomainError(
            "Budget lines cannot be changed once the budget is confirmed",
            status.HTTP_400_BAD_REQUEST,
        )


def create_budget_line_service(
    db,
    valid_user: dict,
    budget_line: BudgetLineCreate,
):

    budget = (
        get_budget(db, budget_line.budget_id)
        if valid_user["role"] == "superuser"
        else get_budget(db, budget_line.budget_id, valid_user["customer_id"])
    )
    if not budget:
        raise DomainError(
            "Budget Not found",
            status.HTTP_400_BAD_REQUEST,
        )
    _assert_budget_editable(budget)
    category = get_or_create_category_service(
        db, valid_user, category_id=budget_line.category_id, category_name=budget_line.category_name
    )

    created_line = create_budget_line(
        db,
        user_id=valid_user["user_id"],
        budget_id=budget_line.budget_id,
        category_id=category.id,
        description=budget_line.description,
        amount=budget_line.amount,
        extra_fields=budget_line.extra_fields,
    )
    recalculate_budget_total(db, budget_line.budget_id)
    return created_line


def get_viewable_budget_lines_service(db, valid_user, budget_id):
    """Like get_budget_lines_service for a single budget_id, but also allows a
    donor who funds this budget (not just its owner) to view its lines. Used
    only by the read/detail route — line create/update/delete keep the
    stricter owner-only checks in this file unchanged."""
    from app.services.budget_services import _can_view_budget

    budget = get_budget(db, budget_id)
    if not budget or not _can_view_budget(budget, valid_user):
        raise DomainError(
            "Budget Not found",
            status.HTTP_400_BAD_REQUEST,
        )
    return list_budget_lines(db, budget_id=budget_id)


def get_budget_lines_service(
    db,
    valid_user,
    budget_id=None,
):
    if budget_id:
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

        return list_budget_lines(db, budget_id=budget_id)
    else:
        if valid_user["role"] == "superuser":
            return list_budget_lines(db)
        return list_budget_lines(db, customer_id=valid_user["customer_id"])


def get_budget_line_by_id_service(
    db,
    valid_user: dict,
    budget_line_id: UUID,
):
    budget_line = get_budget_line(db, budget_line_id)
    if not budget_line:
        raise DomainError(
            "Budget Line not found",
            status.HTTP_404_NOT_FOUND,
        )

    budget = (
        get_budget(db, budget_line.budget_id)
        if valid_user["role"] == "superuser"
        else get_budget(db, budget_line.budget_id, valid_user["customer_id"])
    )
    if not budget:
        raise PermissionDenied()

    return budget_line


def list_budget_service(valid_user, db):
    if valid_user["role"] == "superuser":
        return list_budgets(db)

    return list_budgets(db, customer_id=valid_user["customer_id"])


def update_budget_line_service(
    db,
    valid_user: dict,
    budget_line_id: UUID,
    new_budget_line: BudgetLineUpdate,
):
    budget_line = get_budget_line_by_id_service(
        db, valid_user=valid_user, budget_line_id=budget_line_id
    )
    if not budget_line:
        raise DomainError(
            "Budget Line not found",
            status.HTTP_404_NOT_FOUND,
        )
    budget = get_budget(db, budget_line.budget_id)
    _assert_budget_editable(budget)
    updated_line = update_budget_line(
        db, existing_line=budget_line, new_budget_line=new_budget_line
    )
    if not updated_line:
        raise DomainError(
            "Budget Line not found",
            status.HTTP_404_NOT_FOUND,
        )
    recalculate_budget_total(db, updated_line.budget_id)
    return updated_line


def delete_budget_line_service(budget_line_id: UUID, valid_user: dict, db):
    # fetch valid budget, if user does not have access relevant error will be raised
    valid_budget_line = get_budget_line_by_id_service(
        db=db, valid_user=valid_user, budget_line_id=budget_line_id
    )

    if valid_budget_line:
        budget_id = valid_budget_line.budget_id
        budget = get_budget(db, budget_id)
        _assert_budget_editable(budget)
        result = delete_budget_line(session=db, budget_line=valid_budget_line)
        recalculate_budget_total(db, budget_id)
        return result
    return False
