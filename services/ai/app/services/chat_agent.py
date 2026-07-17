"""PydanticAI intent-extraction agent for the budget chat.

The model's only job each turn is to classify intent and extract whatever
fields it can from the message into a fixed schema (TurnIntent) — it never
decides whether or when to call the budget service. `chat_orchestrator.py`
owns that decision: it checks which required fields are present, and only
then calls the plain REST helper functions below directly. Because
`output_type` is a Pydantic union (not `str`) and no function tools are
registered, PydanticAI forces `tool_choice='required'` on the single output
schema — the model is structurally unable to reply with free-form prose.

Usage:
    agent = build_agent(resolved_model)
    result = await agent.run(message, message_history=history)
    turn: TurnIntent = result.output
"""

from dataclasses import dataclass
from typing import cast

import httpx
from pydantic_ai import Agent

from app.core.logging import get_logger
from app.schemas.chat_intent_schema import INTENT_OUTPUT_TYPES, TurnIntent

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a budget assistant for GrandFlow, a grant management platform used by
non-profit organisations. Your ONLY job is to read the user's message and the conversation so far,
then output ONE structured turn describing what they want. You never take action yourself — you
only classify and extract.

Rules:
- Pick exactly one intent: create_budget, add_line, update_budget, get_summary, or clarify.
- Only fill in fields you can actually read from the conversation. Leave anything unclear as null
  — never invent, guess, or default a value the user did not give you.
- Never invent line items, categories, or amounts the user did not ask for.
- Use "clarify" for anything that isn't one of the four budget actions, or when you need more
  information before you can even tell which intent applies.
- message_to_user is shown to the user verbatim: plain, concise, natural language. Never put JSON,
  tool names, IDs, or code blocks in it — you don't have and don't need any resource IDs, the
  system tracks those for you.
- Amounts are in the budget's local currency unless the user specifies otherwise."""


@dataclass
class ChatDeps:
    http: httpx.AsyncClient
    customer_id: str
    user_id: str
    token: str
    budget_service_url: str


def _auth(deps: ChatDeps) -> dict:
    return {"Authorization": f"Bearer {deps.token}"}


def _url(deps: ChatDeps, path: str) -> str:
    return f"{deps.budget_service_url.rstrip('/')}/{path.lstrip('/')}"


# ---------------------------------------------------------------------------
# REST helpers — plain functions called directly by chat_orchestrator.py once
# it has decided a turn has enough information to act. Never raise: return a
# descriptive string on failure so the orchestrator can relay it to the user.
# ---------------------------------------------------------------------------


async def create_budget(
    deps: ChatDeps,
    budget_name: str,
    external_funder_name: str,
    duration_months: int | None = None,
) -> tuple[bool, str, str | None]:
    """Create a new, empty budget. Returns (success, message, new_budget_id)."""
    payload: dict = {"name": budget_name, "external_funder_name": external_funder_name}
    if duration_months is not None:
        payload["duration_months"] = duration_months

    try:
        resp = await deps.http.post(_url(deps, "/budgets/"), json=payload, headers=_auth(deps))
        resp.raise_for_status()
        data = resp.json()
        budget_id = data.get("id")
        return True, f"Budget '{budget_name}' created successfully (id: {budget_id}).", budget_id
    except httpx.HTTPStatusError as exc:
        logger.warning("create_budget_error", status=exc.response.status_code)
        return False, f"Failed to create budget: {exc.response.text[:200]}", None
    except Exception as exc:
        logger.error("create_budget_exception", error=str(exc))
        return False, f"Unexpected error creating budget: {exc}", None


async def update_budget(
    deps: ChatDeps,
    budget_id: str,
    name: str | None = None,
    external_funder_name: str | None = None,
    duration_months: int | None = None,
    local_currency: str | None = None,
) -> tuple[bool, str]:
    """Update fields on an existing budget. Returns (success, message)."""
    payload = {
        k: v
        for k, v in {
            "name": name,
            "external_funder_name": external_funder_name,
            "duration_months": duration_months,
            "local_currency": local_currency,
        }.items()
        if v is not None
    }
    if not payload:
        return False, "No fields to update were provided."

    try:
        resp = await deps.http.patch(
            _url(deps, f"/budgets/{budget_id}"), json=payload, headers=_auth(deps)
        )
        resp.raise_for_status()
        return True, f"Budget {budget_id} updated successfully."
    except httpx.HTTPStatusError as exc:
        logger.warning("update_budget_error", status=exc.response.status_code)
        return False, f"Failed to update budget: {exc.response.text[:200]}"
    except Exception as exc:
        logger.error("update_budget_exception", error=str(exc))
        return False, f"Unexpected error updating budget: {exc}"


async def add_budget_line(
    deps: ChatDeps,
    budget_id: str,
    description: str,
    amount: float,
    category_name: str,
) -> tuple[bool, str]:
    """Add a new line item to a budget. Returns (success, message)."""
    payload = {
        "budget_id": budget_id,
        "description": description,
        "amount": amount,
        "category_name": category_name,
    }
    try:
        resp = await deps.http.post(_url(deps, "/budget-lines/"), json=payload, headers=_auth(deps))
        resp.raise_for_status()
        data = resp.json()
        line_id = data.get("id", "unknown")
        return True, f"Line '{description}' ({amount}) added to budget (line id: {line_id})."
    except httpx.HTTPStatusError as exc:
        logger.warning("add_budget_line_error", status=exc.response.status_code)
        return False, f"Failed to add budget line: {exc.response.text[:200]}"
    except Exception as exc:
        logger.error("add_budget_line_exception", error=str(exc))
        return False, f"Unexpected error adding budget line: {exc}"


async def get_budget_summary(deps: ChatDeps, budget_id: str) -> tuple[bool, str]:
    """Fetch a read-only summary of a budget including its lines. Returns (success, message)."""
    try:
        resp = await deps.http.get(_url(deps, f"/budgets/{budget_id}"), headers=_auth(deps))
        resp.raise_for_status()
        data = resp.json()
        name = data.get("name", "unknown")
        lines = data.get("lines", [])
        total = sum(ln.get("amount", 0) for ln in lines)
        preview = ", ".join(
            f"{ln.get('description', '?')} ({ln.get('amount', 0)})" for ln in lines[:5]
        )
        suffix = f" … and {len(lines) - 5} more" if len(lines) > 5 else ""
        return True, f"Budget '{name}': {len(lines)} lines, total {total}. {preview}{suffix}"
    except httpx.HTTPStatusError as exc:
        logger.warning("get_budget_summary_error", status=exc.response.status_code)
        return False, f"Could not retrieve budget: {exc.response.text[:200]}"
    except Exception as exc:
        logger.error("get_budget_summary_exception", error=str(exc))
        return False, f"Unexpected error fetching budget: {exc}"


def build_agent(resolved_model) -> "Agent[None, TurnIntent]":
    """Return a fresh Agent bound to the resolved PydanticAI model.

    A new Agent is created per-request (cheap) so that the model
    (Anthropic key / Ollama URL) is never shared across requests.
    """
    agent = Agent(
        resolved_model.model,
        output_type=INTENT_OUTPUT_TYPES,
        system_prompt=SYSTEM_PROMPT,
        model_settings={"temperature": 0.1},
        retries=3,
    )
    agent.instrument = True
    return cast("Agent[None, TurnIntent]", agent)
