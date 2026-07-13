"""Safety-net tests for app/crud/chat_session.py against a real in-memory SQLite DB.

These pin down the semantics the chat service's conversation store must
replicate after the migration (chunk 5b): silent session creation for
unknown/foreign ids (tenant isolation), 50-message history cap, chronological
replay, and turn persistence.
"""

import uuid

import pytest
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.crud.chat_session import (
    db_messages_to_pydantic_ai,
    get_or_create_session,
    load_message_history,
    save_turn,
)
from app.models.base import Base
from app.models.chat_message import AIChatMessage
from tests.factories.chat import AIChatMessageFactory, AIChatSessionFactory
from tests.factories.user import ValidUserFactory

pytestmark = pytest.mark.anyio


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


class TestGetOrCreateSession:

    async def test_creates_new_session_without_id(self, db):
        user = ValidUserFactory()
        session = await get_or_create_session(None, user["customer_id"], user["user_id"], db)
        assert str(session.customer_id) == user["customer_id"]
        assert str(session.user_id) == user["user_id"]
        assert session.message_count == 0

    async def test_returns_existing_session_for_own_customer(self, db):
        existing = AIChatSessionFactory()
        db.add(existing)
        await db.flush()

        session = await get_or_create_session(
            str(existing.id), str(existing.customer_id), str(existing.user_id), db
        )
        assert str(session.id) == str(existing.id)

    async def test_unknown_session_id_silently_creates_new(self, db):
        user = ValidUserFactory()
        unknown_id = str(uuid.uuid4())
        session = await get_or_create_session(
            unknown_id, user["customer_id"], user["user_id"], db
        )
        assert str(session.id) != unknown_id
        assert str(session.customer_id) == user["customer_id"]

    async def test_foreign_customer_session_silently_creates_new(self, db):
        """Tenant isolation: another customer's session id must never be returned."""
        foreign = AIChatSessionFactory()
        db.add(foreign)
        await db.flush()

        intruder = ValidUserFactory()
        session = await get_or_create_session(
            str(foreign.id), intruder["customer_id"], intruder["user_id"], db
        )
        assert str(session.id) != str(foreign.id)
        assert str(session.customer_id) == intruder["customer_id"]


class TestLoadMessageHistory:

    async def test_unknown_session_returns_empty(self, db):
        assert await load_message_history(str(uuid.uuid4()), db) == []

    async def test_returns_last_50_in_chronological_order(self, db):
        session = AIChatSessionFactory()
        db.add(session)
        messages = AIChatMessageFactory.create_batch(55, session_id=str(session.id))
        db.add_all(messages)
        await db.flush()

        rows = await load_message_history(str(session.id), db)

        assert len(rows) == 50
        timestamps = [row.created_at for row in rows]
        assert timestamps == sorted(timestamps)
        # the 5 oldest of the 55 are excluded
        oldest_five = {str(m.id) for m in sorted(messages, key=lambda m: m.created_at)[:5]}
        assert oldest_five.isdisjoint({str(row.id) for row in rows})


class TestDbMessagesToPydanticAi:

    def test_bad_json_rows_are_skipped_valid_survive(self):
        valid_content = ModelMessagesTypeAdapter.dump_json(
            [ModelRequest(parts=[UserPromptPart(content="hi")])]
        ).decode()
        valid_row = AIChatMessageFactory(content=valid_content)
        garbage_row = AIChatMessageFactory(content="not json {")

        messages = db_messages_to_pydantic_ai([garbage_row, valid_row])

        assert len(messages) == 1
        assert isinstance(messages[0], ModelRequest)


class TestSaveTurn:

    async def test_persists_user_row_and_agent_messages(self, db):
        user = ValidUserFactory()
        session = await get_or_create_session(None, user["customer_id"], user["user_id"], db)
        before = session.last_activity_at
        new_messages = [
            ModelRequest(parts=[UserPromptPart(content="hi")]),
            ModelResponse(parts=[TextPart(content="hello")]),
        ]

        await save_turn(session, "hi", new_messages, db)

        result = await db.execute(
            select(AIChatMessage)
            .where(AIChatMessage.session_id == str(session.id))
            .order_by(AIChatMessage.created_at)
        )
        rows = result.scalars().all()
        assert len(rows) == 3
        roles = sorted(row.role for row in rows)
        assert roles == ["assistant", "tool", "user"]
        user_row = next(row for row in rows if row.role == "user")
        assert user_row.content == "hi"
        assert session.message_count == 3
        assert session.last_activity_at >= before
