"""Regression test: ConversationOut/MessageOut must accept the UUID GUID columns return."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.schemas.chat import ConversationOut, MessageOut
from tests.factories.conversation import ConversationFactory, MessageFactory

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


async def test_conversation_out_validates_real_orm_row(db):
    conversation = ConversationFactory()
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)

    out = ConversationOut.model_validate(conversation)

    assert out.id == conversation.id


async def test_message_out_validates_real_orm_row(db):
    message = MessageFactory()
    db.add(message)
    await db.flush()
    await db.refresh(message)

    out = MessageOut.model_validate(message)

    assert out.id == message.id
