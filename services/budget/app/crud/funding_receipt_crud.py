from datetime import date

from sqlalchemy.orm import Session
from app.models.currency_ledger import FundingReceiptModel
from uuid import UUID


def create_funding_receipt(
    session: Session,
    user_id: UUID,
    budget_id: UUID,
    amount: float,
    received_at: date,
) -> FundingReceiptModel:
    receipt = FundingReceiptModel(
        budget_id=budget_id,
        amount=amount,
        received_at=received_at,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(receipt)
    session.commit()
    session.refresh(receipt)
    return receipt


def get_funding_receipt(session: Session, receipt_id: UUID) -> FundingReceiptModel | None:
    return session.query(FundingReceiptModel).filter(FundingReceiptModel.id == receipt_id).first()


def list_funding_receipts(
    session: Session, budget_id: UUID | None = None
) -> list[FundingReceiptModel]:
    query = session.query(FundingReceiptModel)
    if budget_id:
        query = query.filter(FundingReceiptModel.budget_id == budget_id)
    return query.order_by(FundingReceiptModel.received_at).all()
