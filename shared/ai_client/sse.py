from typing import AsyncIterable, AsyncIterator


async def iter_sse_frames(chunks: AsyncIterable[str]) -> AsyncIterator[tuple[str, str]]:
    """Reassemble a raw `text/event-stream` body into (event, data) pairs.

    A single frame's `event:`/`data:` lines can arrive split across more than
    one chunk from the wire — this hand-buffers on newlines so a frame is
    only ever yielded once both lines are fully available. Frames with a
    `data:` line but no preceding `event:` are dropped (matches every
    upstream emitter in this codebase, which always sends `event:` first).
    """
    buffer = ""
    current_event = ""
    async for chunk in chunks:
        buffer += chunk
        lines = buffer.split("\n")
        buffer = lines.pop()

        for line in lines:
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                data = line[6:]
                if current_event:
                    yield current_event, data
                current_event = ""
