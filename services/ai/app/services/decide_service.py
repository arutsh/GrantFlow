"""Stateless decision service backing POST /ai/decide (specs/ai-decide/spec.md).

Builds a fresh PydanticAI Agent per request (same key-isolation pattern as
chat_agent.build_agent), exposes the caller-supplied tools as an
ExternalToolset (tools this agent never executes itself), and classifies the
result as either a tool call or a plain-text reply. No conversation state is
held between calls, and no domain service is ever contacted from here.
"""

from dataclasses import replace

from pydantic_ai import Agent, DeferredToolRequests, ExternalToolset, ToolDefinition
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from app.services.provider import ResolvedModel
from shared.ai_client.schemas import AiDecision, ChatTurn, Reply, ToolCall, ToolDef

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
) -> AiDecision:
    """Classify one turn: a tool call (with params) or a plain-text reply."""
    if domain_context:
        message = f"[context: {domain_context}]\n{message}"

    agent = build_agent(resolved_model, tools)
    message_history = _history_to_model_messages(history)

    result = await agent.run(message, message_history=message_history)
    output = result.output

    if isinstance(output, str):
        return Reply(text=output)

    if len(output.calls) > 1:
        raise UnexpectedModelBehavior(
            f"model requested {len(output.calls)} tool calls in one turn, expected at most 1"
        )

    call = output.calls[0]
    return ToolCall(name=call.tool_name, params=call.args_as_dict())
