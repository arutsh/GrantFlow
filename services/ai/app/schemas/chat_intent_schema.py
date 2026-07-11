"""Structured turn output for the budget chat agent.

The agent's only job each turn is to classify intent and extract whatever
fields it can into one of these fixed shapes — it never decides whether to
act. `chat_orchestrator.py` reads the result and decides, in code, whether
enough information is present to actually call the budget service.
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class CreateBudgetIntent(BaseModel):
    intent: Literal["create_budget"]
    budget_name: str | None = None
    external_funder_name: str | None = None
    duration_months: int | None = None
    message_to_user: str


class AddLineIntent(BaseModel):
    intent: Literal["add_line"]
    category_name: str | None = None
    description: str | None = None
    amount: float | None = None
    message_to_user: str


class UpdateBudgetIntent(BaseModel):
    intent: Literal["update_budget"]
    name: str | None = None
    external_funder_name: str | None = None
    duration_months: int | None = None
    local_currency: str | None = None
    message_to_user: str


class GetSummaryIntent(BaseModel):
    intent: Literal["get_summary"]
    message_to_user: str


class ClarifyIntent(BaseModel):
    """Anything that isn't one of the budget actions, or too ambiguous to act on yet."""

    intent: Literal["clarify"]
    message_to_user: str


TurnIntent = Annotated[
    Union[
        CreateBudgetIntent,
        AddLineIntent,
        UpdateBudgetIntent,
        GetSummaryIntent,
        ClarifyIntent,
    ],
    Field(discriminator="intent"),
]

# Type-checker-friendly form for Agent(output_type=...) — PydanticAI expands a
# union into one output tool per member either way, so this is runtime-identical
# to passing TurnIntent, but it satisfies the `Sequence[...]` overload.
INTENT_OUTPUT_TYPES = [
    CreateBudgetIntent,
    AddLineIntent,
    UpdateBudgetIntent,
    GetSummaryIntent,
    ClarifyIntent,
]
