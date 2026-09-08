"""Data-subject-rights spec, "Deleted user's financial records remain
attributable" scenario: budgets/reports elsewhere reference a user by ID
and resolve the display name via POST /users/by_ids/ (see
services/budget/app/services/user_client.py). That endpoint must keep
returning a soft-deleted user (with its tombstoned name), not silently
drop it, or a financial record's creator would render as a broken
reference instead of an anonymized one.

Uses a real in-memory sqlite session (unlike this module's other tests,
which mock the crud layer) because the behavior under test IS the crud
query's WHERE clause — mocking it would just assert the mock's behavior.
"""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.crud.user_crud import get_users_by_ids, soft_delete_user
from app.models.base import Base
from app.models.customer import CustomerModel
from app.models.user import UserModel
from shared.schemas.user_schema import UserRole, UserStatus


@pytest.fixture
async def db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # UserModel.customer is lazy="joined", so the customers table has to
    # exist even for a user with customer_id=None (LEFT OUTER JOIN still
    # needs the table on the right-hand side to be a real table).
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all, tables=[UserModel.__table__, CustomerModel.__table__]
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.mark.anyio
class TestDeletedUserStillResolvable:
    async def test_by_ids_lookup_still_returns_the_tombstoned_user(self, db):
        user = UserModel(
            email="real@example.com",
            first_name="Real",
            last_name="Name",
            role=UserRole.user,
            status=UserStatus.active,
            hashed_password="hash",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)  # id round-trips as UUID, not the str default (#277)

        await soft_delete_user(db, user)

        [resolved] = await get_users_by_ids(db, [user.id])
        assert resolved.id == user.id
        assert resolved.first_name == "Deleted"
        assert resolved.last_name == "User"
        assert resolved.email != "real@example.com"
