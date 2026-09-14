"""Regression test: cache lookup must accept uuid.UUID ids, not just str."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.user_cache import UserProfileModel
from app.services.user_cache import get_users_by_ids_cached


@pytest.fixture
async def user_cache_sessionmaker():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[UserProfileModel.__table__])
    yield async_sessionmaker(bind=engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.anyio
async def test_get_users_by_ids_cached_accepts_uuid_objects(user_cache_sessionmaker):
    user_id = uuid.uuid4()
    http_user = {
        "id": str(user_id),
        "email": "a@example.com",
        "first_name": "Alice",
        "last_name": "Smith",
        "status": "active",
        "role": "member",
    }

    with (
        patch("app.services.user_cache.AsyncSessionLocal", user_cache_sessionmaker),
        patch(
            "app.services.user_cache.get_users_by_ids",
            new_callable=AsyncMock,
            return_value={str(user_id): http_user},
        ),
    ):
        result = await get_users_by_ids_cached([user_id], "token")

    assert result[str(user_id)]["email"] == "a@example.com"
