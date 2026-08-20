"""session-security: an unverified token is rejected with 403 end-to-end,
via a real TestClient/JWT (no `get_validated_user` override)."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.api.auth_routes import get_db
from app.models.base import Base
from app.models.session import SessionModel
from shared.security.jwt_utils import create_access_token


def _token(email_verified: bool) -> str:
    return create_access_token(
        {
            "user_id": str(uuid4()),
            "session_id": str(uuid4()),
            "role": "user",
            "email_verified": email_verified,
        }
    )


@pytest.fixture
def sessions_db():
    # auth_routes.py declares its own module-local get_db (see
    # project_user_routes_duplicate_get_db in memory for the sibling case in
    # user_routes.py) — this fixture exists only so
    # test_verified_token_is_not_blocked_by_the_verification_gate doesn't
    # need a real Postgres reachable at settings.users_database_url, which
    # varies with $ENV and isn't resolvable outside docker-compose.local.yml.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[SessionModel.__table__])
    return sessionmaker(bind=engine)()


class TestSessionsEndpointRequiresVerifiedEmail:
    def test_unverified_token_rejected_with_403(self):
        client = TestClient(app)
        resp = client.get(
            "/api/auth/sessions",
            headers={"Authorization": f"Bearer {_token(email_verified=False)}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "email_not_verified"

    def test_verified_token_is_not_blocked_by_the_verification_gate(self, sessions_db):
        # get_current_user/get_validated_user are deliberately left
        # unmocked (see module docstring) so the gate itself runs for real;
        # only get_db is overridden, so this stays a real end-to-end check
        # of the verification gate without needing a live database.
        app.dependency_overrides[get_db] = lambda: sessions_db
        try:
            client = TestClient(app)
            resp = client.get(
                "/api/auth/sessions",
                headers={"Authorization": f"Bearer {_token(email_verified=True)}"},
            )
        finally:
            del app.dependency_overrides[get_db]
        assert resp.status_code != 403
