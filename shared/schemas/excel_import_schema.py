from pydantic import BaseModel

from shared.schemas.budget_with_lines_schema import BudgetLineInput


class ExcelPrepareImportResult(BaseModel):
    """Response for POST /budgets/excel/prepare-import. `matched=True`: use
    `lines`/`currency` directly. `matched=False`: caller must run AI
    extraction against `rows`."""

    matched: bool
    donor_template_id: int | None = None
    donor_template_name: str | None = None
    lines: list[BudgetLineInput] | None = None
    currency: str | None = None
    fingerprint: str | None = None
    rows: list[list[str | None]] | None = None
