"""Turn orchestrator: runs the intent-extraction agent, then decides — in
code, never in the model — whether enough information is present to actually
call the budget service.

Budget context is client-driven: the page the user is on supplies
`context_budget_id` per request, and when a turn creates a budget the new id
is handed back to the client (via TurnResult.budget_id → the SSE `done`
event) so it can be passed in on subsequent turns. The server stores no
budget state, and the model is never asked to supply or guess a resource ID.
"""

from dataclasses import dataclass

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage

from app.schemas.chat_intent_schema import (
    AddLineIntent,
    ClarifyIntent,
    CreateBudgetIntent,
    GetSummaryIntent,
    TurnIntent,
    UpdateBudgetIntent,
)
from app.services.chat_agent import (
    ChatDeps,
    add_budget_line,
    create_budget,
    get_budget_summary,
    update_budget,
)

_NO_ACTIVE_BUDGET = "There's no budget in progress in this conversation yet."


@dataclass
class TurnResult:
    reply: str
    new_messages: list[ModelMessage]
    budget_id: str | None
    tool_name: str | None = None
    tool_output: str | None = None


async def run_turn(
    agent: "Agent[None, TurnIntent]",
    message: str,
    deps: ChatDeps,
    message_history: list[ModelMessage],
    context_budget_id: str | None,
    page: str | None = None,
) -> TurnResult:
    """Classify the turn, then act on it directly from code if enough is known."""
    if page:
        message = f"[user is on page: {page}]\n{message}"

    result = await agent.run(message, message_history=message_history)
    turn: TurnIntent = result.output
    new_messages = result.new_messages()

    if isinstance(turn, CreateBudgetIntent):
        if turn.budget_name is None or turn.external_funder_name is None:
            return TurnResult(turn.message_to_user, new_messages, context_budget_id)
        ok, msg, new_id = await create_budget(
            deps, turn.budget_name, turn.external_funder_name, turn.duration_months
        )
        return TurnResult(
            msg,
            new_messages,
            new_id if ok else context_budget_id,
            tool_name="create_budget",
            tool_output=msg,
        )

    if isinstance(turn, AddLineIntent):
        if context_budget_id is None:
            return TurnResult(
                f"{_NO_ACTIVE_BUDGET} Want me to create one first?",
                new_messages,
                context_budget_id,
            )
        if turn.category_name is None or turn.amount is None:
            return TurnResult(turn.message_to_user, new_messages, context_budget_id)
        ok, msg = await add_budget_line(
            deps,
            context_budget_id,
            turn.description or turn.category_name,
            turn.amount,
            turn.category_name,
        )
        return TurnResult(
            msg, new_messages, context_budget_id, tool_name="add_budget_line", tool_output=msg
        )

    if isinstance(turn, UpdateBudgetIntent):
        if context_budget_id is None:
            return TurnResult(f"{_NO_ACTIVE_BUDGET} to update.", new_messages, context_budget_id)
        ok, msg = await update_budget(
            deps,
            context_budget_id,
            turn.name,
            turn.external_funder_name,
            turn.duration_months,
            turn.local_currency,
        )
        return TurnResult(
            msg, new_messages, context_budget_id, tool_name="update_budget", tool_output=msg
        )

    if isinstance(turn, GetSummaryIntent):
        if context_budget_id is None:
            return TurnResult(f"{_NO_ACTIVE_BUDGET} to summarise.", new_messages, context_budget_id)
        ok, msg = await get_budget_summary(deps, context_budget_id)
        return TurnResult(
            msg, new_messages, context_budget_id, tool_name="get_budget_summary", tool_output=msg
        )

    assert isinstance(turn, ClarifyIntent)
    return TurnResult(turn.message_to_user, new_messages, context_budget_id)
