"""Regression test: cache lookup must accept uuid.UUID ids, not just str."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.user_cache import UserProfileModel
from app.services.user_cache import get_users_by_ids_cached


@pytest.fixture
def user_cache_sessionmaker():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[UserProfileModel.__table__])
    return sessionmaker(bind=engine)


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
        patch("app.services.user_cache.SessionLocal", user_cache_sessionmaker),
        patch(
            "app.services.user_cache.get_users_by_ids",
            new_callable=AsyncMock,
            return_value={str(user_id): http_user},
        ),
    ):
        result = await get_users_by_ids_cached([user_id], "token")

    assert result[str(user_id)]["email"] == "a@example.com"
