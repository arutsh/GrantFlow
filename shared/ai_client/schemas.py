from typing import Literal, Union

from pydantic import BaseModel

from shared.schemas.budget_with_lines_schema import BudgetLineInput

# Wire contract for POST /ai/decide (specs/ai-decide/spec.md). Both sides of
# that call import these classes directly — chat as the caller (AiClient),
# ai as the callee (decide_routes.py) — so there is one source of truth for
# the request/response shape instead of two hand-kept copies drifting apart.


class ToolDef(BaseModel):
    """One tool chat exposes to ai, as a JSON-schema-shaped description.

    `parameters` is the tool's argument schema (dict, not a Pydantic model)
    because ai only ever inspects it as JSON to hand to the LLM — it never
    validates against it, that happens on the chat side once a ToolCall
    comes back.
    """

    name: str
    description: str
    parameters: dict


class ChatTurn(BaseModel):
    """One replayed turn of conversation history sent to ai.

    role is deliberately just "user"/"assistant" — the two sides of an LLM
    turn — not an account permission level (admin/superuser live elsewhere,
    e.g. shared/security, and never belong in this schema).
    """

    role: Literal["user", "assistant"]
    content: str


class ToolCall(BaseModel):
    """ai's decision: call this tool with these params.

    ai never supplies resource IDs (e.g. budget_id) — those are injected by
    chat from the request's context_id, never trusted from the model.
    """

    name: str
    params: dict


class Reply(BaseModel):
    """ai's decision: no tool call, just say this back to the user."""

    text: str


# The decide() response is always exactly one of these two shapes, tagged by
# a "type" field on the wire ({"decision": {"type": "tool_call"|"reply", ...}})
# — AiClient.decide() reads that tag itself rather than relying on Pydantic to
# guess which model matches.
AiDecision = Union[ToolCall, Reply]


class DecideRequest(BaseModel):
    """Request body for POST /ai/decide — decide_routes.py uses this directly
    as its FastAPI request model, so the two sides can never drift apart.
    """

    message: str
    conversation_history: list[ChatTurn]
    available_tools: list[ToolDef]
    domain_context: dict | None = None


# Event union for AiClient.stream_parse_budget() (specs/chat-parse-budget.md).
# Unlike AiDecision, these are never tagged by a JSON field — the SSE `event:`
# name from ai's /ai/parse-budget/stream is what selects which class to build,
# so callers get one instance per frame and switch on isinstance(...).


class ParseProgress(BaseModel):
    status: str


class ParseDone(BaseModel):
    """ai's parsed-budget payload — same shape budget's `POST /budgets/with-lines`
    expects, minus the service-layer fields (`ai_available`, `prompt_version`)
    that only mattered to the old direct-to-ai response and are dropped here.
    """

    budget_name: str
    external_funder_name: str | None = None
    duration_months: int | None = None
    lines: list[BudgetLineInput]


class ParseError(BaseModel):
    """ai's own `error` frame is a raw string, not JSON (see parse_service.py) —
    callers build this directly from the frame's data without json.loads-ing it.
    """

    message: str


class ParseUnavailable(BaseModel):
    """ai always sends an empty body (`data: {}`) for this event — no fields."""


ParseEvent = Union[ParseProgress, ParseDone, ParseError, ParseUnavailable]
