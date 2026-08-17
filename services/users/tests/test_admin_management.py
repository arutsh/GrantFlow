"""Route tests for the admin-management-page change:
company-user-administration (invite/remove/role/company-update) and
superuser-tenant-administration (company deactivation), plus the
donor-grantee-relationship self-reference guard surfaced by it.
"""

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import auth_routes, user_routes
from app.core.exceptions import DomainError
from app.crud.donor_grantee_crud import create_donor_grantee
from app.models.base import Base
from app.models.customer import CustomerModel, DonorGranteeModel
from app.models.session import SessionModel
from app.models.user import UserModel
from tests.factories.user import CustomerFactory, UserModelFactory


@pytest.fixture
def db():
    """Overrides the shared conftest `db` fixture: these routes touch the
    `users`/`user_sessions` tables too (see test_user_routes.py for the same
    reasoning)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            UserModel.__table__,
            CustomerModel.__table__,
            DonorGranteeModel.__table__,
            SessionModel.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def _client_for(make_client, db, **user_kwargs):
    """user_routes.py and auth_routes.py each define their own module-local
    get_db() (duplicates that also open a real SessionLocal) rather than
    importing the shared one — every route in either file needs its
    dependency overridden separately or requests fall through to Postgres."""
    client = make_client(db=db, **user_kwargs)
    client.app.dependency_overrides[user_routes.get_db] = lambda: db
    client.app.dependency_overrides[auth_routes.get_db] = lambda: db
    return client


def _persist(db, obj):
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _make_customer(db, **overrides):
    return _persist(db, CustomerFactory.build(**overrides))


def _make_user(db, customer, **overrides):
    return _persist(db, UserModelFactory.build(customer_id=customer.id, **overrides))


def _admin_client(make_client, db, customer, **overrides):
    admin = _make_user(db, customer, role="admin", status="active", **overrides)
    return admin, _client_for(
        make_client, db, user_id=admin.id, role="admin", customer_id=str(customer.id)
    )


class TestInviteUser:
    def test_admin_invites_teammate(self, make_client, db):
        customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)

        resp = client.post("/api/users/invite", json={"email": "teammate@example.com"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "teammate@example.com"
        assert body["status"] == "pending"

        created = db.query(UserModel).filter(UserModel.email == "teammate@example.com").first()
        assert created is not None
        assert str(created.customer_id) == str(customer.id)
        assert created.hashed_password is None
        assert created.email_verification_token_hash is not None

    def test_non_admin_cannot_invite(self, make_client, db):
        customer = _make_customer(db)
        member = _make_user(db, customer, role="user", status="active")
        client = _client_for(
            make_client, db, user_id=member.id, role="user", customer_id=str(customer.id)
        )

        resp = client.post("/api/users/invite", json={"email": "x@example.com"})

        assert resp.status_code == 403

    def test_invited_user_appears_pending_in_company_list(self, make_client, db):
        customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)

        client.post("/api/users/invite", json={"email": "pending@example.com"})
        resp = client.get("/api/users/")

        assert resp.status_code == 200
        statuses = {u["email"]: u["status"] for u in resp.json()}
        assert statuses["pending@example.com"] == "pending"

    def test_company_list_is_scoped_to_own_customer(self, make_client, db):
        customer = _make_customer(db)
        other_customer = _make_customer(db)
        _make_user(db, other_customer, email="other-co@example.com")
        _, client = _admin_client(make_client, db, customer)

        resp = client.get("/api/users/")

        emails = {u["email"] for u in resp.json()}
        assert "other-co@example.com" not in emails


class TestAcceptInvite:
    def _invite(self, client, email="invitee@example.com"):
        with patch("app.api.user_routes.settings.EXPOSE_VERIFICATION_TOKEN_FOR_TESTS", True):
            resp = client.post("/api/users/invite", json={"email": email})
        return resp.json()["debug_token"]

    def test_valid_token_sets_password(self, make_client, db):
        customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)
        token = self._invite(client)

        resp = client.post(
            "/api/users/accept-invite",
            json={"email": "invitee@example.com", "token": token, "password": "correct-horse-1"},
        )

        assert resp.status_code == 200
        assert resp.json()["email_verified"] is True

        user = db.query(UserModel).filter(UserModel.email == "invitee@example.com").first()
        assert user.hashed_password is not None
        assert user.email_verified is True
        assert user.status == "active"
        assert user.email_verification_token_hash is None

    def test_expired_or_unknown_token_is_rejected(self, make_client, db):
        customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)
        self._invite(client)

        resp = client.post(
            "/api/users/accept-invite",
            json={
                "email": "invitee@example.com",
                "token": "not-the-real-token",
                "password": "correct-horse-1",
            },
        )

        assert resp.status_code == 400

    def test_already_accepted_token_cannot_be_reused(self, make_client, db):
        customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)
        token = self._invite(client)
        client.post(
            "/api/users/accept-invite",
            json={"email": "invitee@example.com", "token": token, "password": "correct-horse-1"},
        )

        resp = client.post(
            "/api/users/accept-invite",
            json={"email": "invitee@example.com", "token": token, "password": "another-pass-1"},
        )

        assert resp.status_code == 400


class TestRemoveUser:
    def test_admin_removes_teammate(self, make_client, db):
        customer = _make_customer(db)
        admin, client = _admin_client(make_client, db, customer)
        teammate = _make_user(db, customer, role="user", status="active")

        resp = client.delete(f"/api/users/{teammate.id}/remove")

        assert resp.status_code == 200
        db.refresh(teammate)
        assert teammate.deleted_at is not None
        assert teammate.email.endswith("@deleted.invalid")

    def test_admin_removes_another_admin_with_admins_remaining(self, make_client, db):
        customer = _make_customer(db)
        admin, client = _admin_client(make_client, db, customer)
        other_admin = _make_user(db, customer, role="admin", status="active")

        resp = client.delete(f"/api/users/{other_admin.id}/remove")

        assert resp.status_code == 200

    def test_cannot_remove_user_from_another_company(self, make_client, db):
        customer = _make_customer(db)
        other_customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)
        outsider = _make_user(db, other_customer, role="user", status="active")

        resp = client.delete(f"/api/users/{outsider.id}/remove")

        assert resp.status_code == 403

    def test_cannot_remove_last_admin(self, make_client, db):
        customer = _make_customer(db)
        admin, client = _admin_client(make_client, db, customer)

        resp = client.delete(f"/api/users/{admin.id}/remove")

        assert resp.status_code == 400
        db.refresh(admin)
        assert admin.deleted_at is None


class TestUpdateUserRole:
    def test_admin_promotes_teammate(self, make_client, db):
        customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)
        teammate = _make_user(db, customer, role="user", status="active")

        resp = client.patch(f"/api/users/{teammate.id}/role", json={"role": "admin"})

        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_admin_demotes_another_admin_with_admins_remaining(self, make_client, db):
        customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)
        other_admin = _make_user(db, customer, role="admin", status="active")

        resp = client.patch(f"/api/users/{other_admin.id}/role", json={"role": "user"})

        assert resp.status_code == 200
        assert resp.json()["role"] == "user"

    def test_cannot_demote_last_admin(self, make_client, db):
        customer = _make_customer(db)
        admin, client = _admin_client(make_client, db, customer)

        resp = client.patch(f"/api/users/{admin.id}/role", json={"role": "user"})

        assert resp.status_code == 400

    def test_cannot_grant_superuser(self, make_client, db):
        customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)
        teammate = _make_user(db, customer, role="user", status="active")

        resp = client.patch(f"/api/users/{teammate.id}/role", json={"role": "superuser"})

        assert resp.status_code == 400

    def test_demotion_revokes_the_targets_existing_sessions(self, make_client, db):
        # Otherwise a demoted admin's stale token could self-promote back.
        customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)
        other_admin = _make_user(db, customer, role="admin", status="active")
        live_session = _persist(
            db, SessionModel(user_id=other_admin.id, revoked=False)
        )

        resp = client.patch(f"/api/users/{other_admin.id}/role", json={"role": "user"})

        assert resp.status_code == 200
        db.refresh(live_session)
        assert live_session.revoked is True

    def test_promotion_revokes_the_targets_existing_sessions(self, make_client, db):
        customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)
        teammate = _make_user(db, customer, role="user", status="active")
        live_session = _persist(db, SessionModel(user_id=teammate.id, revoked=False))

        resp = client.patch(f"/api/users/{teammate.id}/role", json={"role": "admin"})

        assert resp.status_code == 200
        db.refresh(live_session)
        assert live_session.revoked is True


class TestUpdateCompany:
    def test_admin_updates_company_name(self, make_client, db):
        customer = _make_customer(db, name="Old Name")
        _, client = _admin_client(make_client, db, customer)

        resp = client.patch(f"/api/customers/{customer.id}", json={"name": "New Name"})

        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_admin_changes_donor_grantee_classification(self, make_client, db):
        customer = _make_customer(db, is_ngo=False, is_donor=False)
        _, client = _admin_client(make_client, db, customer)

        resp = client.patch(
            f"/api/customers/{customer.id}", json={"is_donor": True, "is_ngo": True}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["is_donor"] is True
        assert body["is_ngo"] is True

    def test_admin_cannot_update_another_company(self, make_client, db):
        customer = _make_customer(db)
        other_customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)

        resp = client.patch(f"/api/customers/{other_customer.id}", json={"name": "Hijacked"})

        assert resp.status_code == 403


class TestDeactivateCompany:
    def test_superuser_deactivates_directly(self, make_client, db):
        customer = _make_customer(db)
        client = _client_for(make_client, db, role="superuser")

        resp = client.post(f"/api/customers/{customer.id}/deactivate")

        assert resp.status_code == 200
        db.refresh(customer)
        assert customer.deactivated_at is not None

    def test_superuser_deactivates_while_impersonating(self, make_client, db):
        customer = _make_customer(db)
        client = _client_for(
            make_client,
            db,
            role="admin",
            customer_id=str(customer.id),
            is_impersonating=True,
        )

        resp = client.post(f"/api/customers/{customer.id}/deactivate")

        assert resp.status_code == 200

    def test_companys_own_admin_cannot_deactivate_without_impersonating(self, make_client, db):
        customer = _make_customer(db)
        _, client = _admin_client(make_client, db, customer)

        resp = client.post(f"/api/customers/{customer.id}/deactivate")

        assert resp.status_code == 403

    def test_deactivated_companys_user_cannot_log_in(self, make_client, db):
        customer = _make_customer(db)
        client = _client_for(make_client, db, role="superuser")
        client.post(f"/api/customers/{customer.id}/deactivate")

        admin = _make_user(db, customer, role="admin", status="active")
        admin.hashed_password = "$2b$12$notarealhashjustatest"
        db.commit()

        # record_failed_attempt talks to a real Redis (login_rate_limiter is
        # not test-doubled anywhere in this suite) — patched out so this
        # expected-401 doesn't leave rate-limit counters behind for whatever
        # IP/email TestClient happens to use.
        with patch("app.api.auth_routes.record_failed_attempt"):
            resp = client.post(
                "/api/auth/login", json={"email": admin.email, "password": "whatever"}
            )

        assert resp.status_code == 401


class TestDonorGranteeSelfReferenceGuard:
    def test_rejects_same_customer_as_donor_and_grantee(self, db):
        customer = _make_customer(db, is_ngo=True, is_donor=True)

        with pytest.raises(DomainError) as exc_info:
            create_donor_grantee(db, donor_id=customer.id, grantee_id=customer.id)

        assert exc_info.value.status_code == 400
