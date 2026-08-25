from sqlalchemy.orm import Session
from uuid import UUID

from app.models.budget import BudgetCategoryModel
from app.crud.budget_category_crud import (
    get_budget_category,
    create_budget_category,
    get_budget_category_by_name_and_template_id,
    get_budget_categories_by_names_and_template_id,
    bulk_create_budget_categories,
)
from app.core.exceptions import DomainError
from fastapi import status


def get_or_create_category_service(
    db: Session, valid_user: dict, category_id: UUID | None = None, category_name: str | None = None
) -> BudgetCategoryModel:
    """The service to get or create a budget category.
    the idea is if category_id is not provided, then try to fetch 'Miscellaneous' category,
    if it does not exist, create it."""

    if category_id:
        category = get_budget_category(db, category_id)
        if not category:
            raise DomainError(
                "Budget Category not found",
                status.HTTP_404_NOT_FOUND,
            )
        return category

    donor_template_id = None
    name = "Miscellaneous"
    code = "MISC"
    if category_name:
        name = category_name
        code = "_".join(category_name.split()).upper()

    category = get_budget_category_by_name_and_template_id(db, name, donor_template_id)

    if category:
        return category

    return create_budget_category(db, valid_user["user_id"], name, code, donor_template_id)


def get_or_create_categories_by_names_service(
    db: Session, valid_user: dict, category_names: list[str]
) -> dict[str, BudgetCategoryModel]:
    """Batched form of get_or_create_category_service for a list of names — avoids N+1 lookups."""
    unique_names = list(dict.fromkeys(category_names))
    if not unique_names:
        return {}

    existing = get_budget_categories_by_names_and_template_id(db, unique_names, None)
    result = {category.name: category for category in existing}

    missing_names = [name for name in unique_names if name not in result]
    if missing_names:
        names_and_codes = [(name, "_".join(name.split()).upper()) for name in missing_names]
        created = bulk_create_budget_categories(db, valid_user["user_id"], names_and_codes, None)
        result.update({category.name: category for category in created})

    return result
