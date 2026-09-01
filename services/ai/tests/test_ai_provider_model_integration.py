"""Real-DB coverage for the provider/model catalog — guards against the bug
this table exists to fix: a model from one provider being accepted for a
different provider (e.g. claude-haiku-4-5 accepted for ollama)."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.crud.ai_provider_model import exists_for_provider
from app.models.ai_provider import AIProvider
from app.models.ai_provider_model import AIProviderModel
from app.models.base import Base

ANTHROPIC_ID = "bbbbbbbb-0000-0000-0000-000000000002"
OLLAMA_ID = "cccccccc-0000-0000-0000-000000000003"


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[AIProvider.__table__, AIProviderModel.__table__],
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        session.add_all(
            [
                AIProvider(id=ANTHROPIC_ID, name="anthropic", display_name="Anthropic",
                           key_prefix="sk-ant-", is_active=True),
                AIProvider(id=OLLAMA_ID, name="ollama", display_name="Ollama (Local)",
                           key_prefix=None, is_active=True),
                AIProviderModel(provider_id=ANTHROPIC_ID, name="claude-haiku-4-5",
                                display_name="Claude Haiku 4.5", is_active=True),
                AIProviderModel(provider_id=OLLAMA_ID, name="llama3.2",
                                display_name="Llama 3.2", is_active=True),
            ]
        )
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.anyio
async def test_model_valid_for_its_own_provider(db_session):
    assert await exists_for_provider(ANTHROPIC_ID, "claude-haiku-4-5", db_session) is True


@pytest.mark.anyio
async def test_model_rejected_for_a_different_provider(db_session):
    assert await exists_for_provider(OLLAMA_ID, "claude-haiku-4-5", db_session) is False
