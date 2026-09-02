"""Route tests for PATCH /api/users/{user_id}/ covering the founder-becomes-
admin-on-new-company promotion (openspec/changes/new-company-user-admin).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import user_routes
from app.models.base import Base
from app.models.customer import CustomerModel
from app.models.user import UserModel
from tests.factories.user import UserModelFactory


@pytest.fixture
def db():
    """Overrides the conftest `db` fixture: this endpoint's auth checks
    (get_user, is_superuser) query the `users` table, which the shared
    fixture doesn't create (see services/users/tests/conftest.py).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[UserModel.__table__, CustomerModel.__table__])
    return sessionmaker(bind=engine)()


def _client_for(make_client, db, **user_kwargs):
    """make_client(db=db) only overrides app.db.session.get_db, but
    user_routes.py defines its own module-local get_db() (a duplicate that
    also opens a real SessionLocal) rather than importing the shared one —
    so every route in this file needs its dependency overridden separately
    or requests silently fall through to a real Postgres connection.
    """
    client = make_client(db=db, **user_kwargs)
    client.app.dependency_overrides[user_routes.get_db] = lambda: db
    return client


def _persist(db, obj):
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _make_pending_user(db, **overrides):
    # UserModelFactory already defaults to role=user, status=pending.
    return _persist(db, UserModelFactory.build(**overrides))


class TestUpdateUserOnboarding:
    def test_new_customer_name_promotes_founder_to_admin(self, make_client, db):
        pending_user = _make_pending_user(db)
        client = _client_for(make_client, db, user_id=pending_user.id, role="user")

        response = client.patch(
            f"/api/users/{pending_user.id}/",
            json={"new_customer_name": "Acme NGO"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["role"] == "admin"
        assert body["status"] == "active"
        assert body["customer_id"] is not None

        customer = (
            db.query(CustomerModel).filter(CustomerModel.id == body["customer_id"]).first()
        )
        assert customer is not None
        assert customer.name == "Acme NGO"
        assert customer.is_ngo is True

    def test_existing_customer_id_leaves_role_unchanged(self, make_client, db):
        customer = _persist(db, CustomerModel(name="Existing Org", country="GB", currency="GBP"))
        pending_user = _make_pending_user(db)
        client = _client_for(make_client, db, user_id=pending_user.id, role="user")

        response = client.patch(
            f"/api/users/{pending_user.id}/",
            json={"customer_id": str(customer.id)},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["role"] == "user"
        assert body["customer_id"] == str(customer.id)

    def test_client_supplied_role_is_overridden_when_creating_new_company(self, make_client, db):
        pending_user = _make_pending_user(db)
        client = _client_for(make_client, db, user_id=pending_user.id, role="user")

        response = client.patch(
            f"/api/users/{pending_user.id}/",
            # A non-superuser can't normally set role at all (not in
            # allowed_fields), but even a smuggled "superuser" must not
            # survive — the founder promotion always forces exactly "admin".
            json={"new_customer_name": "Sneaky Org", "role": "superuser"},
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"
