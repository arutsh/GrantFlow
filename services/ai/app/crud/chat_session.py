"""CRUD for AIChatSession and AIChatMessage."""

import json
import uuid
from datetime import datetime, timezone
from typing import Sequence

from pydantic_ai.messages import ModelMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import AIChatMessage
from app.models.chat_session import AIChatSession

_MAX_HISTORY_MESSAGES = 50


async def get_or_create_session(
    session_id: str | None,
    customer_id: str,
    user_id: str,
    db: AsyncSession,
) -> AIChatSession:
    """Return existing session or create a new one."""
    now = datetime.now(timezone.utc)

    if session_id:
        result = await db.execute(select(AIChatSession).where(AIChatSession.id == session_id))
        session = result.scalar_one_or_none()
        if session and str(session.customer_id) == customer_id:
            return session

    session = AIChatSession(
        id=str(uuid.uuid4()),
        customer_id=customer_id,
        user_id=user_id,
        message_count=0,
        last_activity_at=now,
        created_at=now,
    )
    db.add(session)
    await db.flush()
    return session


async def load_message_history(session_id: str, db: AsyncSession) -> list[AIChatMessage]:
    """Load the most recent messages for a session (up to _MAX_HISTORY_MESSAGES)."""
    result = await db.execute(
        select(AIChatMessage)
        .where(AIChatMessage.session_id == session_id)
        .order_by(AIChatMessage.created_at.desc())
        .limit(_MAX_HISTORY_MESSAGES)
    )
    rows = result.scalars().all()
    return list(reversed(rows))


def db_messages_to_pydantic_ai(rows: Sequence[AIChatMessage]) -> list[ModelMessage]:
    """Deserialise stored message rows back into PydanticAI ModelMessage objects.

    Messages are stored as JSON blobs (the serialised PydanticAI message format).
    Rows that fail to deserialise are silently skipped.
    """
    from pydantic_ai.messages import ModelMessagesTypeAdapter

    messages: list[ModelMessage] = []
    for row in rows:
        try:
            parsed = ModelMessagesTypeAdapter.validate_json(row.content)
            messages.extend(parsed)
        except Exception:
            pass
    return messages


async def save_turn(
    session: AIChatSession,
    user_text: str,
    new_messages: list[ModelMessage],
    db: AsyncSession,
) -> None:
    """Persist the user message and all new agent messages; update session metadata."""
    now = datetime.now(timezone.utc)

    user_row = AIChatMessage(
        id=str(uuid.uuid4()),
        session_id=str(session.id),
        role="user",
        content=user_text,
        created_at=now,
    )
    db.add(user_row)

    for msg in new_messages:
        try:
            from pydantic_ai.messages import ModelMessagesTypeAdapter

            content = ModelMessagesTypeAdapter.dump_json([msg]).decode()
        except Exception:
            content = json.dumps({"raw": str(msg)})

        role = "assistant" if hasattr(msg, "parts") and _is_response(msg) else "tool"
        row = AIChatMessage(
            id=str(uuid.uuid4()),
            session_id=str(session.id),
            role=role,
            content=content,
            created_at=now,
        )
        db.add(row)

    session.message_count = (session.message_count or 0) + 1 + len(new_messages)
    session.last_activity_at = now
    await db.commit()


def _is_response(msg: ModelMessage) -> bool:
    from pydantic_ai.messages import ModelResponse

    return isinstance(msg, ModelResponse)
