import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.services.decide_service import decide
from app.services.provider import ResolvedModel
from shared.ai_client.schemas import ChatTurn, Reply, ToolCall, ToolDef

CREATE_BUDGET_TOOL = ToolDef(
    name="create_budget",
    description="Create a new budget",
    parameters={
        "type": "object",
        "properties": {"budget_name": {"type": "string"}},
        "required": ["budget_name"],
    },
)
DELETE_BUDGET_TOOL = ToolDef(
    name="delete_budget",
    description="Delete a budget",
    parameters={
        "type": "object",
        "properties": {"budget_id": {"type": "string"}},
        "required": ["budget_id"],
    },
)


def _resolved(model) -> ResolvedModel:
    return ResolvedModel(model=model, provider_name="test", model_name="test")


class TestDecideToolCall:
    @pytest.mark.anyio
    async def test_tool_schema_reaches_model(self):
        seen: dict = {}

        def respond(messages, agent_info: AgentInfo) -> ModelResponse:
            seen["tools"] = agent_info.function_tools
            return ModelResponse(parts=[TextPart(content="ok")])

        await decide(
            resolved_model=_resolved(FunctionModel(respond)),
            message="hi",
            history=[],
            tools=[CREATE_BUDGET_TOOL],
            domain_context=None,
        )

        assert len(seen["tools"]) == 1
        assert seen["tools"][0].name == "create_budget"
        assert seen["tools"][0].parameters_json_schema == CREATE_BUDGET_TOOL.parameters

    @pytest.mark.anyio
    async def test_deferred_call_maps_to_tool_call(self):
        def respond(messages, agent_info: AgentInfo) -> ModelResponse:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="create_budget",
                        args={"budget_name": "USAID Grant"},
                        tool_call_id="call-1",
                    )
                ]
            )

        result = await decide(
            resolved_model=_resolved(FunctionModel(respond)),
            message="make a budget called USAID Grant",
            history=[],
            tools=[CREATE_BUDGET_TOOL],
            domain_context=None,
        )

        assert isinstance(result, ToolCall)
        assert result.name == "create_budget"
        assert result.params == {"budget_name": "USAID Grant"}

    @pytest.mark.anyio
    async def test_multiple_tool_calls_raises(self):
        def respond(messages, agent_info: AgentInfo) -> ModelResponse:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="create_budget",
                        args={"budget_name": "USAID Grant"},
                        tool_call_id="call-1",
                    ),
                    ToolCallPart(
                        tool_name="delete_budget",
                        args={"budget_id": "b-1"},
                        tool_call_id="call-2",
                    ),
                ]
            )

        with pytest.raises(UnexpectedModelBehavior):
            await decide(
                resolved_model=_resolved(FunctionModel(respond)),
                message="make a budget then delete another",
                history=[],
                tools=[CREATE_BUDGET_TOOL, DELETE_BUDGET_TOOL],
                domain_context=None,
            )


class TestDecideReply:
    @pytest.mark.anyio
    async def test_text_output_maps_to_reply(self):
        def respond(messages, agent_info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[TextPart(content="What's the funder name?")])

        result = await decide(
            resolved_model=_resolved(FunctionModel(respond)),
            message="make a budget",
            history=[],
            tools=[CREATE_BUDGET_TOOL],
            domain_context=None,
        )

        assert isinstance(result, Reply)
        assert result.text == "What's the funder name?"

    @pytest.mark.anyio
    async def test_history_is_replayed(self):
        seen: dict = {}

        def respond(messages, agent_info: AgentInfo) -> ModelResponse:
            seen["messages"] = messages
            return ModelResponse(parts=[TextPart(content="ok")])

        history = [
            ChatTurn(role="user", content="hi"),
            ChatTurn(role="assistant", content="hello, how can I help?"),
        ]
        await decide(
            resolved_model=_resolved(FunctionModel(respond)),
            message="make a budget",
            history=history,
            tools=[],
            domain_context=None,
        )

        # 2 replayed history messages + 1 new request message
        assert len(seen["messages"]) == 3

    @pytest.mark.anyio
    async def test_domain_context_folded_into_message(self):
        seen: dict = {}

        def respond(messages, agent_info: AgentInfo) -> ModelResponse:
            seen["messages"] = messages
            return ModelResponse(parts=[TextPart(content="ok")])

        await decide(
            resolved_model=_resolved(FunctionModel(respond)),
            message="add a line",
            history=[],
            tools=[],
            domain_context={"page": "budgets", "context_id": "b-1"},
        )

        last_request = seen["messages"][-1]
        prompt_part = last_request.parts[-1]
        assert "b-1" in prompt_part.content
        assert "add a line" in prompt_part.content
