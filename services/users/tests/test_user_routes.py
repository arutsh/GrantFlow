"""Route tests for PATCH /api/users/{user_id}/ covering the founder-becomes-
admin-on-new-company promotion (openspec/changes/new-company-user-admin).
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.customer import CustomerModel
from app.models.user import UserModel
from tests.factories.user import CustomerFactory, UserModelFactory


@pytest.fixture
async def db():
    """Overrides the conftest `db` fixture: this endpoint's auth checks
    (get_user, is_superuser) query the `users` table, which the shared
    fixture doesn't create (see services/users/tests/conftest.py).
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all, tables=[UserModel.__table__, CustomerModel.__table__]
        )
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


async def _persist(db, obj):
    db.add(obj)
    await db.commit()
    return obj


async def _make_pending_user(db, **overrides):
    # UserModelFactory already defaults to role=user, status=pending.
    return await _persist(db, UserModelFactory.build(**overrides))


@pytest.mark.anyio
class TestUpdateUserOnboarding:
    async def test_new_customer_name_promotes_founder_to_admin(self, make_client, db):
        pending_user = await _make_pending_user(db)
        client = make_client(db=db, user_id=pending_user.id, role="user")

        response = client.patch(
            f"/api/users/{pending_user.id}/",
            json={"new_customer_name": "Acme NGO"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["role"] == "admin"
        assert body["status"] == "active"
        assert body["customer_id"] is not None

        result = await db.execute(
            select(CustomerModel).where(CustomerModel.id == body["customer_id"])
        )
        customer = result.scalar_one_or_none()
        assert customer is not None
        assert customer.name == "Acme NGO"
        assert customer.is_ngo is True

    async def test_existing_customer_id_leaves_role_unchanged(self, make_client, db):
        customer = await _persist(db, CustomerFactory.build(name="Existing Org"))
        pending_user = await _make_pending_user(db)
        client = make_client(db=db, user_id=pending_user.id, role="user")

        response = client.patch(
            f"/api/users/{pending_user.id}/",
            json={"customer_id": str(customer.id)},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["role"] == "user"
        assert body["customer_id"] == str(customer.id)

    async def test_client_supplied_role_is_overridden_when_creating_new_company(
        self, make_client, db
    ):
        pending_user = await _make_pending_user(db)
        client = make_client(db=db, user_id=pending_user.id, role="user")

        response = client.patch(
            f"/api/users/{pending_user.id}/",
            # A non-superuser can't normally set role at all (not in
            # allowed_fields), but even a smuggled "superuser" must not
            # survive — the founder promotion always forces exactly "admin".
            json={"new_customer_name": "Sneaky Org", "role": "superuser"},
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"
