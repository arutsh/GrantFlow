"""Tests for app/crud/conversation.py against a real in-memory SQLite DB —
mirrors ai's test_chat_session_crud.py (the template this migration follows).
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.crud.conversation import (
    get_conversation_messages,
    get_or_create_conversation,
    list_conversations,
    load_history,
    save_turn,
    to_chat_turns,
)
from app.models.base import Base
from app.models.message import Message
from app.services.orchestrator import TurnResult
from shared.ai_client import ChatTurn
from tests.factories.conversation import ConversationFactory, MessageFactory
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


class TestGetOrCreateConversation:
    async def test_creates_new_conversation_without_id(self, db):
        user = ValidUserFactory()
        conversation = await get_or_create_conversation(
            None, user["customer_id"], user["user_id"], db
        )
        assert str(conversation.customer_id) == user["customer_id"]
        assert str(conversation.user_id) == user["user_id"]
        assert conversation.message_count == 0

    async def test_returns_existing_conversation_for_own_customer(self, db):
        existing = ConversationFactory()
        db.add(existing)
        await db.flush()

        conversation = await get_or_create_conversation(
            str(existing.id), str(existing.customer_id), str(existing.user_id), db
        )
        assert str(conversation.id) == str(existing.id)

    async def test_unknown_id_silently_creates_new(self, db):
        user = ValidUserFactory()
        unknown_id = str(uuid.uuid4())
        conversation = await get_or_create_conversation(
            unknown_id, user["customer_id"], user["user_id"], db
        )
        assert str(conversation.id) != unknown_id
        assert str(conversation.customer_id) == user["customer_id"]

    async def test_foreign_customer_id_silently_creates_new(self, db):
        """Tenant isolation: another customer's conversation id must never be returned."""
        foreign = ConversationFactory()
        db.add(foreign)
        await db.flush()

        intruder = ValidUserFactory()
        conversation = await get_or_create_conversation(
            str(foreign.id), intruder["customer_id"], intruder["user_id"], db
        )
        assert str(conversation.id) != str(foreign.id)
        assert str(conversation.customer_id) == intruder["customer_id"]

    async def test_malformed_id_silently_creates_new_instead_of_raising(self, db):
        """A non-UUID conversation_id must not reach the GUID column's bind-param
        conversion (uuid.UUID(value)) as an uncaught ValueError — same graceful
        "unknown id" degradation as a well-formed-but-missing id."""
        user = ValidUserFactory()
        conversation = await get_or_create_conversation(
            "not-a-uuid", user["customer_id"], user["user_id"], db
        )
        assert str(conversation.customer_id) == user["customer_id"]


class TestLoadHistory:
    async def test_unknown_conversation_returns_empty(self, db):
        assert await load_history(str(uuid.uuid4()), db) == []

    async def test_returns_last_50_in_chronological_order(self, db):
        conversation = ConversationFactory()
        db.add(conversation)
        messages = MessageFactory.create_batch(55, conversation_id=str(conversation.id))
        db.add_all(messages)
        await db.flush()

        rows = await load_history(str(conversation.id), db)

        assert len(rows) == 50
        timestamps = [row.created_at for row in rows]
        assert timestamps == sorted(timestamps)
        oldest_five = {str(m.id) for m in sorted(messages, key=lambda m: m.created_at)[:5]}
        assert oldest_five.isdisjoint({str(row.id) for row in rows})


class TestToChatTurns:
    def test_projects_role_and_content_skips_non_conversational_rows(self):
        rows = [
            MessageFactory(role="user", content="hi"),
            MessageFactory(role="assistant", content="hello"),
            MessageFactory(role="tool", content="raw tool payload"),
        ]
        turns = to_chat_turns(rows)
        assert turns == [
            ChatTurn(role="user", content="hi"),
            ChatTurn(role="assistant", content="hello"),
        ]


class TestSaveTurn:
    async def test_persists_reply_only_turn(self, db):
        user = ValidUserFactory()
        conversation = await get_or_create_conversation(
            None, user["customer_id"], user["user_id"], db
        )
        before = conversation.last_activity_at
        turn_result = TurnResult(reply="hello there")

        await save_turn(conversation, "hi", turn_result, db)

        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == str(conversation.id))
            .order_by(Message.created_at)
        )
        rows = result.scalars().all()
        assert len(rows) == 2
        assert rows[0].role == "user" and rows[0].content == "hi"
        assert rows[1].role == "assistant" and rows[1].content == "hello there"
        assert rows[1].tool_name is None
        assert conversation.message_count == 2
        assert conversation.last_activity_at >= before

    async def test_persists_tool_turn_with_metadata(self, db):
        user = ValidUserFactory()
        conversation = await get_or_create_conversation(
            None, user["customer_id"], user["user_id"], db
        )
        turn_result = TurnResult(
            reply="Budget created.",
            tool_name="create_budget",
            tool_params={"budget_name": "USAID Grant", "external_funder_name": "USAID"},
            tool_result="Budget 'USAID Grant' created successfully.",
            created_resource_id="budget-123",
        )

        await save_turn(conversation, "create a budget", turn_result, db)

        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == str(conversation.id))
            .order_by(Message.created_at)
        )
        rows = result.scalars().all()
        assistant_row = rows[1]
        assert assistant_row.tool_name == "create_budget"
        assert assistant_row.tool_params == {
            "budget_name": "USAID Grant",
            "external_funder_name": "USAID",
        }
        assert assistant_row.tool_result == {
            "message": "Budget 'USAID Grant' created successfully.",
            "budget_id": "budget-123",
        }


class TestListAndGetMessages:
    async def test_list_conversations_scoped_to_customer(self, db):
        user = ValidUserFactory()
        mine = ConversationFactory(customer_id=user["customer_id"])
        other = ConversationFactory()
        db.add_all([mine, other])
        await db.flush()

        rows = await list_conversations(user["customer_id"], db)

        ids = {str(row.id) for row in rows}
        assert str(mine.id) in ids
        assert str(other.id) not in ids

    async def test_list_conversations_respects_limit(self, db):
        user = ValidUserFactory()
        db.add_all(ConversationFactory.create_batch(5, customer_id=user["customer_id"]))
        await db.flush()

        rows = await list_conversations(user["customer_id"], db, limit=2)

        assert len(rows) == 2

    async def test_get_messages_denied_for_foreign_conversation(self, db):
        foreign = ConversationFactory()
        db.add(foreign)
        await db.flush()

        intruder = ValidUserFactory()
        result = await get_conversation_messages(str(foreign.id), intruder["customer_id"], db)

        assert result is None

    async def test_get_messages_denied_for_malformed_id(self, db):
        """Same graceful degradation as get_or_create_conversation — a non-UUID
        id must not raise deep inside the GUID column's bind-param conversion."""
        result = await get_conversation_messages("not-a-uuid", "some-customer-id", db)

        assert result is None

    async def test_get_messages_returns_chronological_for_owner(self, db):
        conversation = ConversationFactory()
        db.add(conversation)
        messages = MessageFactory.create_batch(3, conversation_id=str(conversation.id))
        db.add_all(messages)
        await db.flush()

        result = await get_conversation_messages(
            str(conversation.id), str(conversation.customer_id), db
        )

        assert len(result) == 3
        timestamps = [row.created_at for row in result]
        assert timestamps == sorted(timestamps)

    async def test_get_messages_limit_keeps_most_recent_not_oldest(self, db):
        conversation = ConversationFactory()
        db.add(conversation)
        messages = MessageFactory.create_batch(5, conversation_id=str(conversation.id))
        db.add_all(messages)
        await db.flush()

        result = await get_conversation_messages(
            str(conversation.id), str(conversation.customer_id), db, limit=2
        )

        assert len(result) == 2
        newest_two = {str(m.id) for m in sorted(messages, key=lambda m: m.created_at)[-2:]}
        assert {str(row.id) for row in result} == newest_two
        timestamps = [row.created_at for row in result]
        assert timestamps == sorted(timestamps)
