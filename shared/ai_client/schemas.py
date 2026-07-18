from typing import Literal, Union

from pydantic import BaseModel

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
