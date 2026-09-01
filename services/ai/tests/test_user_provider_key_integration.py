"""Real-DB coverage: the mocked tests in test_user_provider_key.py don't
exercise flush ordering, which is where the delete-with-replacement unique
index violation was hiding (see delete() in the crud module)."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.crud.user_provider_key import create, delete, list_for_customer, set_default
from app.models.ai_provider import AIProvider
from app.models.base import Base
from app.models.user_provider_key import UserProviderKey

CUSTOMER_ID = "cccccccc-0000-0000-0000-000000000003"
USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all, tables=[AIProvider.__table__, UserProviderKey.__table__]
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        session.add(
            AIProvider(
                id="bbbbbbbb-0000-0000-0000-000000000002",
                name="anthropic",
                display_name="Anthropic",
                key_prefix="sk-ant-",
                is_active=True,
            )
        )
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.anyio
async def test_delete_default_with_named_replacement_against_real_db(db_session):
    first = await create(
        CUSTOMER_ID,
        USER_ID,
        "bbbbbbbb-0000-0000-0000-000000000002",
        "First",
        "enc1",
        "claude-sonnet-4-6",
        None,
        True,
        db_session,
    )
    second = await create(
        CUSTOMER_ID,
        USER_ID,
        "bbbbbbbb-0000-0000-0000-000000000002",
        "Second",
        "enc2",
        "claude-sonnet-4-6",
        None,
        False,
        db_session,
    )

    await delete(CUSTOMER_ID, str(first.id), db_session, new_default_id=str(second.id))

    remaining = await list_for_customer(CUSTOMER_ID, db_session)
    assert len(remaining) == 1
    assert remaining[0].id == second.id
    assert remaining[0].is_default is True


@pytest.mark.anyio
async def test_deleting_last_remaining_config_against_real_db(db_session):
    only = await create(
        CUSTOMER_ID,
        USER_ID,
        "bbbbbbbb-0000-0000-0000-000000000002",
        "Only",
        "enc1",
        "claude-sonnet-4-6",
        None,
        True,
        db_session,
    )

    await delete(CUSTOMER_ID, str(only.id), db_session)

    remaining = await list_for_customer(CUSTOMER_ID, db_session)
    assert remaining == []


@pytest.mark.anyio
async def test_create_second_default_against_real_db(db_session):
    first = await create(
        CUSTOMER_ID,
        USER_ID,
        "bbbbbbbb-0000-0000-0000-000000000002",
        "First",
        "enc1",
        "claude-sonnet-4-6",
        None,
        True,
        db_session,
    )
    second = await create(
        CUSTOMER_ID,
        USER_ID,
        "bbbbbbbb-0000-0000-0000-000000000002",
        "Second",
        "enc2",
        "claude-sonnet-4-6",
        None,
        True,
        db_session,
    )

    remaining = await list_for_customer(CUSTOMER_ID, db_session)
    by_id = {str(c.id): c for c in remaining}
    assert by_id[str(first.id)].is_default is False
    assert by_id[str(second.id)].is_default is True


@pytest.mark.anyio
async def test_set_default_switch_against_real_db(db_session):
    first = await create(
        CUSTOMER_ID,
        USER_ID,
        "bbbbbbbb-0000-0000-0000-000000000002",
        "First",
        "enc1",
        "claude-sonnet-4-6",
        None,
        True,
        db_session,
    )
    second = await create(
        CUSTOMER_ID,
        USER_ID,
        "bbbbbbbb-0000-0000-0000-000000000002",
        "Second",
        "enc2",
        "claude-sonnet-4-6",
        None,
        False,
        db_session,
    )

    await set_default(CUSTOMER_ID, str(second.id), db_session)

    remaining = await list_for_customer(CUSTOMER_ID, db_session)
    by_id = {str(c.id): c for c in remaining}
    assert by_id[str(first.id)].is_default is False
    assert by_id[str(second.id)].is_default is True
