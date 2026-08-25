from sqlalchemy.orm import Session
from app.models.budget import BudgetLineModel, BudgetModel
from uuid import UUID

from app.schemas import BudgetLineCreate


def create_budget_line(
    session: Session,
    user_id: UUID,
    budget_id: UUID,
    category_id: UUID | None,
    description: str,
    amount: float,
    extra_fields: dict | None = None,
) -> BudgetLineModel:
    """
    Create a budget line after validating NGO and Donor IDs.
    """
    # Validate external customer IDs

    budget_line = BudgetLineModel(
        budget_id=budget_id,
        category_id=category_id,
        description=description,
        amount=amount,
        extra_fields=extra_fields,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(budget_line)
    session.commit()
    session.refresh(budget_line)
    return budget_line


def bulk_create_budget_lines(
    session: Session,
    user_id: UUID,
    budget_id: UUID,
    lines: list[dict],
) -> list[BudgetLineModel]:
    """Create multiple budget lines with a single insert + commit."""
    budget_lines = [
        BudgetLineModel(
            budget_id=budget_id,
            category_id=line["category_id"],
            description=line["description"],
            amount=line["amount"],
            extra_fields=line.get("extra_fields"),
            created_by=user_id,
            updated_by=user_id,
        )
        for line in lines
    ]
    session.add_all(budget_lines)
    session.commit()
    for budget_line in budget_lines:
        session.refresh(budget_line)
    return budget_lines


def get_budget_line(session: Session, budget_line_id: UUID) -> BudgetLineModel | None:
    return session.query(BudgetLineModel).filter(BudgetLineModel.id == budget_line_id).first()


def list_budget_lines(
    session: Session,
    budget_id: UUID | None = None,
    customer_id: UUID | None = None,
    limit: int = 100,
):
    query = session.query(BudgetLineModel)
    if budget_id:
        query = query.filter(BudgetLineModel.budget_id == budget_id)
    if customer_id:
        query = query.join(BudgetLineModel.budget).filter(BudgetModel.owner_id == customer_id)
    return query.limit(limit).all()


def list_budget_lines_by_category(
    session: Session, category_id: UUID | None = None, limit: int = 100
):
    query = session.query(BudgetLineModel)
    if category_id:
        query = query.filter(BudgetLineModel.category_id == category_id)
    return query.limit(limit).all()


def update_budget_line(
    session: Session, existing_line, new_budget_line: BudgetLineCreate
) -> BudgetLineModel | None:
    if new_budget_line.description is not None:
        existing_line.description = new_budget_line.description
    if new_budget_line.amount is not None:
        existing_line.amount = new_budget_line.amount
    if new_budget_line.extra_fields is not None:
        existing_line.extra_fields = {
            **(existing_line.extra_fields or {}),
            **new_budget_line.extra_fields,
        }
    session.commit()
    session.refresh(existing_line)
    return existing_line


def delete_budget_line(session: Session, budget_line: BudgetLineModel) -> bool:
    session.delete(budget_line)
    session.commit()
    return True
