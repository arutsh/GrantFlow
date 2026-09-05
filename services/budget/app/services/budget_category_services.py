from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from app.models.budget import BudgetCategoryModel
from app.crud.budget_category_crud import (
    get_budget_category,
    get_budget_categories_by_names,
    bulk_create_budget_categories,
    update_budget_category,
    delete_budget_category,
    list_budget_categories,
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

    name = category_name if category_name else "Miscellaneous"
    return get_or_create_categories_by_names_service(db, valid_user, budget_id, [name])[name]


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
        try:
            created = bulk_create_budget_categories(
                db, valid_user["user_id"], budget_id, names_and_codes
            )
        except IntegrityError:
            # budget_id is freshly created by the caller, so nothing else can
            # already reference it — this race almost impossible situation.
            db.rollback()
            created = get_budget_categories_by_names(db, budget_id, missing_names)
            if len(created) != len(missing_names):
                raise DomainError(
                    "Failed to create budget categories",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            result.update({category.name: category for category in created})
        else:
            # created rows are expired post-commit (expire_on_commit=True), so use
            # the already-known names instead of reading .name and triggering N+1 selects.
            result.update({name: category for (name, _), category in zip(names_and_codes, created)})

    return result


def _get_owned_budget_or_none(db: Session, valid_user: dict, budget_id: UUID):
    customer_id = valid_user.get("customer_id")
    return get_budget(db, budget_id, customer_id) if customer_id else None


def list_budget_categories_service(
    db: Session, valid_user: dict, budget_id: UUID
) -> list[BudgetCategoryModel]:
    budget = _get_owned_budget_or_none(db, valid_user, budget_id)
    if not budget:
        raise DomainError("Budget Not found", status.HTTP_400_BAD_REQUEST)
    return list_budget_categories(db, budget_id=budget_id)


def _get_owned_category_or_404(db: Session, valid_user: dict, category_id: UUID):
    customer_id = valid_user.get("customer_id")
    category = get_budget_category(db, category_id, customer_id) if customer_id else None
    if not category:
        raise DomainError("Budget Category not found", status.HTTP_404_NOT_FOUND)

    return category, category.budget


def update_budget_category_service(
    db: Session, valid_user: dict, category_id: UUID, update_data: dict
) -> BudgetCategoryModel:
    category, budget = _get_owned_category_or_404(db, valid_user, category_id)
    _assert_budget_editable(budget)

    if not update_data:
        return category

    name = update_data.get("name", category.name)
    code = update_data.get("code", category.code)

    try:
        return update_budget_category(db, category, valid_user["user_id"], name, code)
    except IntegrityError:
        db.rollback()
        raise DomainError(
            "A category with this name already exists in this budget",
            status.HTTP_400_BAD_REQUEST,
        )


def delete_budget_category_service(db: Session, valid_user: dict, category_id: UUID) -> bool:
    category, budget = _get_owned_category_or_404(db, valid_user, category_id)
    _assert_budget_editable(budget)

    return delete_budget_category(db, category)
