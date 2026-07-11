"""Tests for the SSE adapter (chat_stream.py).

build_chat_sse_stream delegates all decision-making to chat_orchestrator.run_turn
(tested separately in test_chat_orchestrator.py) — these tests only check the SSE
framing, so run_turn is mocked directly rather than driving a real agent.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.chat_orchestrator import TurnResult
from app.services.chat_stream import build_chat_sse_stream, _sse


def _collect(frames: list[str]) -> dict[str, list[dict]]:
    """Parse SSE frames into {event_type: [data_dict, ...]}."""
    result: dict[str, list[dict]] = {}
    current_event = ""
    for line in "\n".join(frames).splitlines():
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: "):
            data = json.loads(line[6:])
            result.setdefault(current_event, []).append(data)
    return result


async def _run(turn_result: TurnResult | Exception, on_complete=None) -> list[str]:
    run_turn_mock = (
        AsyncMock(side_effect=turn_result)
        if isinstance(turn_result, Exception)
        else AsyncMock(return_value=turn_result)
    )
    frames = []
    with patch("app.services.chat_stream.run_turn", run_turn_mock):
        async for frame in build_chat_sse_stream(
            agent=AsyncMock(),
            message="hi",
            deps=AsyncMock(),
            message_history=[],
            context_budget_id=None,
            on_complete=on_complete or AsyncMock(),
        ):
            frames.append(frame)
    return frames


class TestSseFmt:
    def test_sse_helper_format(self):
        frame = _sse("thinking")
        assert frame.startswith("event: thinking\n")
        assert frame.endswith("\n\n")

    def test_sse_with_data(self):
        frame = _sse("text", {"delta": "hello"})
        assert '"delta": "hello"' in frame or '"delta":"hello"' in frame


class TestBuildChatSseStream:
    @pytest.mark.anyio
    async def test_thinking_event_emitted_first(self):
        turn_result = TurnResult(reply="Done.", new_messages=[], budget_id=None)
        frames = await _run(turn_result)
        assert frames[0].startswith("event: thinking")

    @pytest.mark.anyio
    async def test_done_event_emitted_last_with_reply(self):
        turn_result = TurnResult(reply="Budget created.", new_messages=[], budget_id="b-1")
        frames = await _run(turn_result)
        assert frames[-1].startswith("event: done")
        events = _collect(frames)
        assert events["done"][0]["response"] == "Budget created."
        assert events["text"][0]["delta"] == "Budget created."

    @pytest.mark.anyio
    async def test_done_event_carries_budget_id_when_set(self):
        turn_result = TurnResult(reply="Created.", new_messages=[], budget_id="b-99")
        events = _collect(await _run(turn_result))
        assert events["done"][0]["budget_id"] == "b-99"

    @pytest.mark.anyio
    async def test_done_event_omits_budget_id_when_none(self):
        turn_result = TurnResult(reply="What funder?", new_messages=[], budget_id=None)
        events = _collect(await _run(turn_result))
        assert "budget_id" not in events["done"][0]

    @pytest.mark.anyio
    async def test_no_tool_call_events_when_no_action_taken(self):
        turn_result = TurnResult(reply="What's the funder?", new_messages=[], budget_id=None)
        frames = await _run(turn_result)
        events = _collect(frames)
        assert "tool_call" not in events
        assert "action_result" not in events

    @pytest.mark.anyio
    async def test_tool_call_and_action_result_emitted_when_action_taken(self):
        turn_result = TurnResult(
            reply="Budget created.",
            new_messages=[],
            budget_id="b-1",
            tool_name="create_budget",
            tool_output="Budget created.",
        )
        frames = await _run(turn_result)
        events = _collect(frames)
        assert events["tool_call"][0]["tool_name"] == "create_budget"
        assert events["action_result"][0]["output"] == "Budget created."
        lines = "\n".join(frames).splitlines()
        order = [line[7:].strip() for line in lines if line.startswith("event: ")]
        assert order.index("tool_call") < order.index("action_result") < order.index("text")

    @pytest.mark.anyio
    async def test_error_event_on_orchestrator_exception(self):
        frames = await _run(RuntimeError("LLM failure"))
        assert any("event: error" in f for f in frames)

    @pytest.mark.anyio
    async def test_on_complete_called_with_turn_result(self):
        turn_result = TurnResult(reply="Hello!", new_messages=["m"], budget_id="b-1")
        on_complete = AsyncMock()
        await _run(turn_result, on_complete=on_complete)
        on_complete.assert_called_once_with(turn_result)
