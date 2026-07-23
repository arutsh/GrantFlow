"""Tests for shared/ai_client/sse.py's frame reassembly."""

import pytest

from shared.ai_client.sse import iter_sse_frames


async def _chunks(*pieces: str):
    for piece in pieces:
        yield piece


class TestIterSseFrames:
    @pytest.mark.anyio
    async def test_single_frame_per_chunk(self):
        frames = [
            frame
            async for frame in iter_sse_frames(
                _chunks(
                    'event: progress\ndata: {"status": "Parsing..."}\n\n',
                    'event: done\ndata: {"budget_name": "Trip"}\n\n',
                )
            )
        ]

        assert frames == [
            ("progress", '{"status": "Parsing..."}'),
            ("done", '{"budget_name": "Trip"}'),
        ]

    @pytest.mark.anyio
    async def test_frame_split_mid_line_is_reassembled(self):
        frames = [
            frame
            async for frame in iter_sse_frames(
                _chunks(
                    "event: prog",
                    'ress\ndata: {"stat',
                    'us": "Parsing..."}\n',
                    "\n",
                    "event: error\ndata: unexpected error\n\n",
                )
            )
        ]

        assert frames == [
            ("progress", '{"status": "Parsing..."}'),
            ("error", "unexpected error"),
        ]

    @pytest.mark.anyio
    async def test_error_and_unavailable_data_passed_through_raw(self):
        frames = [
            frame
            async for frame in iter_sse_frames(
                _chunks(
                    "event: unavailable\ndata: {}\n\n",
                    "event: error\ndata: not valid json\n\n",
                )
            )
        ]

        assert frames == [
            ("unavailable", "{}"),
            ("error", "not valid json"),
        ]

    @pytest.mark.anyio
    async def test_data_without_a_preceding_event_is_dropped(self):
        frames = [frame async for frame in iter_sse_frames(_chunks("data: orphaned\n\n"))]

        assert frames == []
