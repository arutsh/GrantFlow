from sqlalchemy.orm import Session
from app.models.budget import BudgetCategoryModel
from uuid import UUID


def create_budget_category(
    session: Session,
    user_id: UUID,
    name: str,
    code: str | None = None,
    donor_template_id: int | None = None,
) -> BudgetCategoryModel:
    budget_category = BudgetCategoryModel(
        name=name,
        code=code,
        donor_template_id=donor_template_id,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(budget_category)
    session.commit()
    session.refresh(budget_category)
    return budget_category


def get_budget_category_by_name_and_template_id(
    session: Session, name: str, template_id: int | None
) -> BudgetCategoryModel | None:
    return (
        session.query(BudgetCategoryModel)
        .filter(
            BudgetCategoryModel.name == name, BudgetCategoryModel.donor_template_id == template_id
        )
        .first()
    )


def get_budget_categories_by_names_and_template_id(
    session: Session, names: list[str], template_id: int | None
) -> list[BudgetCategoryModel]:
    return (
        session.query(BudgetCategoryModel)
        .filter(
            BudgetCategoryModel.name.in_(names),
            BudgetCategoryModel.donor_template_id == template_id,
        )
        .all()
    )


def bulk_create_budget_categories(
    session: Session,
    user_id: UUID,
    names_and_codes: list[tuple[str, str | None]],
    donor_template_id: int | None = None,
) -> list[BudgetCategoryModel]:
    categories = [
        BudgetCategoryModel(
            name=name,
            code=code,
            donor_template_id=donor_template_id,
            created_by=user_id,
            updated_by=user_id,
        )
        for name, code in names_and_codes
    ]
    session.add_all(categories)
    session.commit()
    return categories


def get_budget_category(session: Session, category_id: UUID) -> BudgetCategoryModel | None:
    return session.query(BudgetCategoryModel).filter(BudgetCategoryModel.id == category_id).first()


def list_budget_categories(session: Session, template_id: int | None = None, limit: int = 100):
    query = session.query(BudgetCategoryModel)
    if template_id:
        query = query.filter(BudgetCategoryModel.donor_template_id == template_id)
    return query.limit(limit).all()


def update_budget_category(
    session: Session, category_id: UUID, name: str, code: str | None = None
) -> BudgetCategoryModel | None:
    existing_category = get_budget_category(session, category_id)
    if not existing_category:
        return None
    existing_category.name = name
    existing_category.code = code
    session.commit()
    session.refresh(existing_category)
    return existing_category


def delete_budget_category(session: Session, category_id: UUID) -> bool:
    category = get_budget_category(session, category_id)
    if category:
        session.delete(category)
        session.commit()
        return True
    return False
