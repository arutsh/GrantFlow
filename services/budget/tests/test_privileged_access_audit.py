"""Tests for the privileged-access audit sink (superuser-cross-tenant-access,
Group 4). The read-vs-write fail-open/fail-closed behavior and the generic
sink-building logic live in shared/tests/test_privileged_access.py — this
file only proves this service's real PrivilegedAccessLog model round-trips
correctly through the shared sink builder."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.privileged_access_log import PrivilegedAccessLog
from shared.security.privileged_access import make_privileged_access_sink

ACTOR_ID = str(uuid4())
CUSTOMER_ID = str(uuid4())


@pytest.fixture
def db():
    """Dedicated sync in-memory session — privileged_access_audit.py's sink
    deliberately runs on its own sync engine, independent of the app's
    (async) primary session, so it needs its own sync db fixture here too."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[PrivilegedAccessLog.__table__])
    return sessionmaker(bind=engine)()


def _request(method="GET", path="/api/v1/budgets"):
    return SimpleNamespace(method=method, url=SimpleNamespace(path=path))


class TestWritePrivilegedAccessLog:
    def test_writes_a_row_with_actor_target_and_request_fields(self, db):
        sink = make_privileged_access_sink(lambda: db, PrivilegedAccessLog)
        payload = {"user_id": ACTOR_ID, "customer_id": CUSTOMER_ID}

        sink(payload, _request("POST", "/api/v1/budgets"))

        [row] = db.query(PrivilegedAccessLog).all()
        assert str(row.actor_user_id) == ACTOR_ID
        assert str(row.customer_id) == CUSTOMER_ID
        assert row.method == "POST"
        assert row.path == "/api/v1/budgets"
        assert row.created_at is not None
