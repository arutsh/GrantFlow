# /services/budget/app/api/currency_conversion_routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import SessionLocal
from app.schemas.currency_ledger_schema import (
    CurrencyConversion,
    CurrencyConversionCreate,
    LedgerBalance,
)
from app.services.currency_ledger_services import (
    record_conversion_service,
    get_currency_conversion_service,
    list_currency_conversions_service,
    get_ledger_balance_service,
)
from shared.observability import set_span_attributes
from shared.security.dependencies import get_validated_user

router = APIRouter(prefix="/currency-conversions", tags=["Currency Conversions"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=CurrencyConversion)
def create_currency_conversion_view(
    conversion: CurrencyConversionCreate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(budget_id=conversion.budget_id)
    created_conversion = record_conversion_service(db, valid_user, conversion)
    set_span_attributes(conversion_id=created_conversion.id)
    return created_conversion


@router.get("/balance/{budget_id}", response_model=LedgerBalance)
def get_ledger_balance_view(
    budget_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(budget_id=budget_id)
    return get_ledger_balance_service(db, valid_user, budget_id)


@router.get("/{conversion_id}", response_model=CurrencyConversion)
def get_currency_conversion_view(
    conversion_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(conversion_id=conversion_id)
    return get_currency_conversion_service(db, valid_user, conversion_id)


@router.get("/by-budget/{budget_id}", response_model=List[CurrencyConversion])
def list_currency_conversions_view(
    budget_id: UUID, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(budget_id=budget_id)
    return list_currency_conversions_service(db, valid_user, budget_id)
