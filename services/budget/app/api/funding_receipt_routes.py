# /services/budget/app/api/funding_receipt_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import SessionLocal
from app.schemas.currency_ledger_schema import FundingReceipt, FundingReceiptCreate
from app.services.currency_ledger_services import (
    record_receipt_service,
    get_funding_receipt_service,
    list_funding_receipts_service,
)
from shared.security.dependencies import get_validated_user

router = APIRouter(prefix="/funding-receipts", tags=["Funding Receipts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=FundingReceipt)
def create_funding_receipt_view(
    receipt: FundingReceiptCreate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    return record_receipt_service(db, valid_user, receipt)


@router.get("/{receipt_id}", response_model=FundingReceipt)
def get_funding_receipt_view(
    receipt_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return get_funding_receipt_service(db, valid_user, receipt_id)


@router.get("/by-budget/{budget_id}", response_model=List[FundingReceipt])
def list_funding_receipts_view(
    budget_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return list_funding_receipts_service(db, valid_user, budget_id)
