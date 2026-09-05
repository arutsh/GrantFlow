from sqlalchemy.orm import Session, contains_eager
from app.models.budget import BudgetCategoryModel, BudgetModel
from uuid import UUID


def create_budget_category(
    session: Session,
    user_id: UUID,
    budget_id: UUID,
    name: str,
    code: str | None = None,
) -> BudgetCategoryModel:
    budget_category = BudgetCategoryModel(
        name=name,
        code=code,
        budget_id=budget_id,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(budget_category)
    session.commit()
    session.refresh(budget_category)
    return budget_category


def get_budget_category_by_name(
    session: Session, budget_id: UUID, name: str
) -> BudgetCategoryModel | None:
    return (
        session.query(BudgetCategoryModel)
        .filter(BudgetCategoryModel.budget_id == budget_id, BudgetCategoryModel.name == name)
        .first()
    )


def get_budget_categories_by_names(
    session: Session, budget_id: UUID, names: list[str]
) -> list[BudgetCategoryModel]:
    return (
        session.query(BudgetCategoryModel)
        .filter(
            BudgetCategoryModel.budget_id == budget_id,
            BudgetCategoryModel.name.in_(names),
        )
        .all()
    )


def bulk_create_budget_categories(
    session: Session,
    user_id: UUID,
    budget_id: UUID,
    names_and_codes: list[tuple[str, str | None]],
) -> list[BudgetCategoryModel]:
    categories = [
        BudgetCategoryModel(
            name=name,
            code=code,
            budget_id=budget_id,
            created_by=user_id,
            updated_by=user_id,
        )
        for name, code in names_and_codes
    ]
    session.add_all(categories)
    session.commit()
    return categories


def get_budget_category(
    session: Session, category_id: UUID, customer_id: UUID | None = None
) -> BudgetCategoryModel | None:
    query = session.query(BudgetCategoryModel).filter(BudgetCategoryModel.id == category_id)
    if customer_id:
        query = (
            query.join(BudgetCategoryModel.budget)
            .filter(BudgetModel.owner_id == customer_id)
            .options(contains_eager(BudgetCategoryModel.budget))
        )
    return query.first()


def list_budget_categories(session: Session, budget_id: UUID | None = None, limit: int = 100):
    query = session.query(BudgetCategoryModel)
    if budget_id:
        query = query.filter(BudgetCategoryModel.budget_id == budget_id)
    return query.limit(limit).all()


def update_budget_category(
    session: Session,
    category: BudgetCategoryModel,
    user_id: UUID,
    name: str,
    code: str | None = None,
) -> BudgetCategoryModel:
    category.name = name
    category.code = code
    category.updated_by = user_id
    session.commit()
    session.refresh(category)
    return category


def delete_budget_category(session: Session, category: BudgetCategoryModel) -> bool:
    session.delete(category)
    session.commit()
    return True
