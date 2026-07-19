"""Per-tool parameter models for the budget toolset.

These are what ai's tool-call params are validated against before dispatch —
never the raw budget REST schemas. Field names are the curated, model-facing
names (e.g. `budget_name`, not budget's own `name`); `tool_registry.py` maps
them onto the REST payload. None of these carry a resource id — `budget_id`
is injected by the orchestrator from the request's `context_id`, never
accepted here from the model.
"""

from pydantic import BaseModel, model_validator


class CreateBudgetParams(BaseModel):
    budget_name: str
    external_funder_name: str
    duration_months: int | None = None


class AddBudgetLineParams(BaseModel):
    category_name: str
    amount: float
    description: str | None = None


class UpdateBudgetParams(BaseModel):
    name: str | None = None
    external_funder_name: str | None = None
    duration_months: int | None = None
    local_currency: str | None = None

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        # `is not None`, not truthiness — duration_months=0 is a legitimate
        # provided value, not an absent one.
        fields = (self.name, self.external_funder_name, self.duration_months, self.local_currency)
        if all(v is None for v in fields):
            raise ValueError("At least one field to update must be provided")
        return self


class GetBudgetSummaryParams(BaseModel):
    pass


TOOL_PARAM_MODELS: dict[str, type[BaseModel]] = {
    "create_budget": CreateBudgetParams,
    "add_budget_line": AddBudgetLineParams,
    "update_budget": UpdateBudgetParams,
    "get_budget_summary": GetBudgetSummaryParams,
}
