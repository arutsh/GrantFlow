from pydantic import BaseModel
from typing import Any
from uuid import UUID


class BudgetLineInput(BaseModel):
    category_name: str
    description: str
    amount: float
    extra_fields: dict[str, Any] | None = None


class CreateBudgetWithLinesRequest(BaseModel):
    budget_name: str
    external_funder_name: str
    owner_id: UUID | None = None
    duration_months: int | None = None
    local_currency: str | None = None
    actual_currency: str | None = None
    donor_total_amount: float | None = None
    estimated_exchange_rate: float | None = None
    lines: list[BudgetLineInput]
    # Excel-import provenance, set only by chat's /chat/import-excel orchestration.
    donor_template_id: int | None = None
    excel_import_fingerprint: str | None = None
    excel_import_structure: dict[str, Any] | None = None
    excel_import_lines_locked_count: int | None = None
