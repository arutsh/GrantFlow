"""Stateless decision service backing POST /ai/decide (specs/ai-decide/spec.md).

Builds a fresh PydanticAI Agent per request (never shared across requests, so
a customer's key/model is never mixed with another's), exposes the
caller-supplied tools as an ExternalToolset (tools this agent never executes
itself), and classifies the result as either a tool call or a plain-text
reply. No conversation state is held between calls, and no domain service is
ever contacted from here.
"""

import time
from dataclasses import replace

from pydantic_ai import Agent, DeferredToolRequests, ExternalToolset, ToolDefinition
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from app.core.logging import get_logger
from app.services.audit import write_audit_log
from app.services.provider import ResolvedModel
from shared.ai_client.schemas import AiDecision, ChatTurn, Reply, ToolCall, ToolDef

logger = get_logger(__name__)

# No external prompt template/version for this endpoint (SYSTEM_PROMPT below is
# a fixed constant, unlike parse_service's Jinja-templated, versioned prompts) —
# bump this if SYSTEM_PROMPT's meaning changes enough to affect audit analysis.
PROMPT_VERSION = "decide-v1"

# ExternalToolset hardcodes max_retries=0 per tool, so a malformed or
# schema-invalid tool call raises immediately instead of letting the model
# self-correct. Retrying is only worth it where it's free: self-hosted
# providers with no per-call billing. Anthropic is deliberately absent — a
# retry there re-bills the customer's own BYOK key for another completion.
_TOOL_CALL_RETRIES_BY_PROVIDER = {
    "ollama": 3,
}


class _RetryableExternalToolset(ExternalToolset):
    """ExternalToolset with a configurable per-tool retry budget.

    ExternalToolset.get_tools() always returns max_retries=0 with no
    constructor override, so this re-stamps each tool after the fact.
    """

    def __init__(self, tool_defs: list[ToolDefinition], *, max_retries: int):
        super().__init__(tool_defs=tool_defs)
        self._max_retries = max_retries

    async def get_tools(self, ctx):
        tools = await super().get_tools(ctx)
        return {name: replace(tool, max_retries=self._max_retries) for name, tool in tools.items()}


SYSTEM_PROMPT = """You are a domain-neutral decision engine used by several different services.
Given the user's message, the conversation so far, and a list of tools you may call, decide ONE
of the following:
- Call at most one tool, and only when every one of its required parameters is already known from
  the message or conversation history.
- Otherwise, reply in plain text — ask for whatever information is missing, or answer directly if
  no tool applies to what the user asked.

Never invent a parameter value the user did not provide. Never call more than one tool per turn.
Your plain-text replies are shown to the user verbatim: natural language only, no JSON, no tool
names, no code blocks."""


def _history_to_model_messages(history: list[ChatTurn]) -> list[ModelRequest | ModelResponse]:
    """Bridge chat's plain role/content pairs into pydantic-ai's own message envelopes.

    pydantic-ai needs ModelRequest (things sent to the model) / ModelResponse
    (things the model said) rather than flat dicts, since it has to
    losslessly re-serialize history for whichever provider is active. Only
    plain text is ever replayed here — no prior tool calls, no attachments —
    so a single part per turn is enough.
    """
    messages: list[ModelRequest | ModelResponse] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


def _build_toolset(tools: list[ToolDef], provider_name: str) -> ExternalToolset:
    tool_defs = [
        ToolDefinition(
            name=tool.name,
            description=tool.description,
            parameters_json_schema=tool.parameters,
        )
        for tool in tools
    ]
    max_retries = _TOOL_CALL_RETRIES_BY_PROVIDER.get(provider_name, 0)
    return _RetryableExternalToolset(tool_defs, max_retries=max_retries)


def build_agent(resolved_model: ResolvedModel, tools: list[ToolDef]) -> "Agent[None, str]":
    """Return a fresh Agent bound to the resolved model and this request's toolset.

    A new Agent (and toolset) is built per request so the model (Anthropic
    key / Ollama URL) is never shared across requests.
    """
    agent = Agent(
        resolved_model.model,
        toolsets=[_build_toolset(tools, resolved_model.provider_name)],
        output_type=[str, DeferredToolRequests],
        system_prompt=SYSTEM_PROMPT,
        model_settings={"temperature": 0.1},
        retries=3,
    )
    agent.instrument = True
    return agent


async def decide(
    resolved_model: ResolvedModel,
    message: str,
    history: list[ChatTurn],
    tools: list[ToolDef],
    domain_context: dict | None,
    *,
    customer_id: str,
    user_id: str,
) -> AiDecision:
    """Classify one turn: a tool call (with params) or a plain-text reply.

    Writes one ai_audit_logs entry per call, success or failure — this is the
    only place that happens for this endpoint (decide_routes.py stays a thin
    HTTP layer). Mirrors parse_service's audit pattern: capture usage/timing,
    log in a finally block, then re-raise so callers' error handling (e.g.
    decide_routes.py's 502 on UnexpectedModelBehavior/AgentRunError) is
    unaffected.
    """
    if domain_context:
        message = f"[context: {domain_context}]\n{message}"

    agent = build_agent(resolved_model, tools)
    message_history = _history_to_model_messages(history)

    start = time.monotonic()
    success = True
    error_message: str | None = None
    output_json: dict | None = None
    input_tokens = 0
    output_tokens = 0

    try:
        result = await agent.run(message, message_history=message_history)
        usage = result.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0
        output = result.output

        if isinstance(output, str):
            decision: AiDecision = Reply(text=output)
        elif len(output.calls) > 1:
            # A weaker model can echo an already-satisfied field (e.g. reusing
            # update_budget's duration_months because an unrelated number in
            # the message looks similar) alongside the tool the user actually
            # meant. Which call is "the real one" isn't reliably the first —
            # executing any of them risks silently doing the wrong thing (or
            # dropping the one the user wanted), so this degrades to a plain
            # reply instead of guessing. Logged as a warning (not an audit
            # failure) since no system error occurred, just model ambiguity.
            logger.warning(
                "model_multi_tool_call",
                tool_names=[call.tool_name for call in output.calls],
                customer_id=customer_id,
            )
            decision = Reply(
                text="I wasn't able to do that cleanly — could you try rephrasing your "
                "request, one step at a time?"
            )
        else:
            call = output.calls[0]
            decision = ToolCall(name=call.tool_name, params=call.args_as_dict())

        output_json = decision.model_dump()
        return decision
    except Exception as exc:
        success = False
        error_message = str(exc)
        raise
    finally:
        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            await write_audit_log(
                customer_id=customer_id,
                user_id=user_id,
                prompt_version=PROMPT_VERSION,
                input_text=message,
                output_json=output_json,
                provider=resolved_model.provider_name,
                model=resolved_model.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                success=success,
                error_message=error_message,
                duration_ms=duration_ms,
            )
        except Exception as audit_exc:
            logger.error(
                "audit_log_write_failed",
                error=str(audit_exc),
                customer_id=customer_id,
                user_id=user_id,
            )
