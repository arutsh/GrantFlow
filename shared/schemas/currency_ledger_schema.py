from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import date, datetime


class FundingReceiptBase(BaseModel):
    budget_id: UUID | None = None
    amount: float | None = None
    received_at: date | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    updated_at: datetime | None = None
    created_at: datetime | None = None


class FundingReceiptCreate(FundingReceiptBase):
    budget_id: UUID
    amount: float
    received_at: date


class FundingReceipt(FundingReceiptBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class CurrencyConversionBase(BaseModel):
    budget_id: UUID | None = None
    donor_amount: float | None = None
    local_amount: float | None = None
    converted_at: date | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    updated_at: datetime | None = None
    created_at: datetime | None = None


class CurrencyConversionCreate(CurrencyConversionBase):
    budget_id: UUID
    donor_amount: float
    local_amount: float
    converted_at: date


class CurrencyConversion(CurrencyConversionBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class LedgerBalance(BaseModel):
    """Per-currency balances only — never blended into one figure, per
    design.md's "Multi-currency aggregation always groups by currency"
    decision."""

    budget_id: UUID
    actual_currency: str | None
    donor_balance: float
    local_currency: str | None
    local_balance: float
