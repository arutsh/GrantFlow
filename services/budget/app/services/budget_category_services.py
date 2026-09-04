from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from app.models.budget import BudgetCategoryModel
from app.crud.budget_category_crud import (
    get_budget_category,
    create_budget_category,
    get_budget_category_by_name,
    get_budget_categories_by_names,
    bulk_create_budget_categories,
    update_budget_category,
    delete_budget_category,
)
from app.crud.budget_crud import get_budget
from app.core.exceptions import DomainError
from fastapi import status


def _assert_budget_editable(budget) -> None:
    # Local import to avoid a cycle: budget_services imports this module.
    from app.services.budget_services import assert_budget_editable

    assert_budget_editable(budget, "categories")


def get_or_create_category_service(
    db: Session,
    valid_user: dict,
    budget_id: UUID,
    category_id: UUID | None = None,
    category_name: str | None = None,
) -> BudgetCategoryModel:
    """Get an existing category by id/name, or create "Miscellaneous", scoped to budget_id."""
    if category_id:
        category = get_budget_category(db, category_id)
        if not category or category.budget_id != budget_id:
            raise DomainError(
                "Budget Category not found",
                status.HTTP_404_NOT_FOUND,
            )
        return category

    name = "Miscellaneous"
    code = "MISC"
    if category_name:
        name = category_name
        code = "_".join(category_name.split()).upper()

    category = get_budget_category_by_name(db, budget_id, name)

    if category:
        return category

    return create_budget_category(db, valid_user["user_id"], budget_id, name, code)


def get_or_create_categories_by_names_service(
    db: Session, valid_user: dict, budget_id: UUID, category_names: list[str]
) -> dict[str, BudgetCategoryModel]:
    """Batched form of get_or_create_category_service for a list of names — avoids N+1 lookups."""
    unique_names = list(dict.fromkeys(category_names))
    if not unique_names:
        return {}

    existing = get_budget_categories_by_names(db, budget_id, unique_names)
    result = {category.name: category for category in existing}

    missing_names = [name for name in unique_names if name not in result]
    if missing_names:
        names_and_codes: list[tuple[str, str | None]] = [
            (name, "_".join(name.split()).upper()) for name in missing_names
        ]
        created = bulk_create_budget_categories(
            db, valid_user["user_id"], budget_id, names_and_codes
        )
        result.update({category.name: category for category in created})

    return result


def _get_owned_category_or_404(db: Session, valid_user: dict, budget_id: UUID, category_id: UUID):
    category = get_budget_category(db, category_id, budget_id)
    if not category:
        raise DomainError("Budget Category not found", status.HTTP_404_NOT_FOUND)

    customer_id = valid_user.get("customer_id")
    budget = get_budget(db, budget_id, customer_id) if customer_id else None
    if not budget:
        raise DomainError("Budget Category not found", status.HTTP_404_NOT_FOUND)

    return category, budget


def update_budget_category_service(
    db: Session,
    valid_user: dict,
    budget_id: UUID,
    category_id: UUID,
    name: str,
    code: str | None = None,
) -> BudgetCategoryModel:
    _, budget = _get_owned_category_or_404(db, valid_user, budget_id, category_id)
    _assert_budget_editable(budget)

    try:
        updated = update_budget_category(db, category_id, valid_user["user_id"], name, code)
    except IntegrityError:
        db.rollback()
        raise DomainError(
            "A category with this name already exists in this budget",
            status.HTTP_400_BAD_REQUEST,
        )
    if not updated:
        raise DomainError("Budget Category not found", status.HTTP_404_NOT_FOUND)
    return updated


def delete_budget_category_service(
    db: Session, valid_user: dict, budget_id: UUID, category_id: UUID
) -> bool:
    _, budget = _get_owned_category_or_404(db, valid_user, budget_id, category_id)
    _assert_budget_editable(budget)

    return delete_budget_category(db, category_id)
