from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import Column, DateTime, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from shared.security import privileged_access as pa

_Base = declarative_base()


class _FakePrivilegedAccessLog(_Base):
    """Minimal stand-in for a service's real model, just to exercise
    make_privileged_access_sink against a real session without importing
    any one service's model into shared/tests."""

    __tablename__ = "fake_privileged_access_logs"

    actor_user_id = Column(String, primary_key=True)
    customer_id = Column(String)
    method = Column(String)
    path = Column(String)
    created_at = Column(DateTime(timezone=True))


def _request(method="GET", path="/api/v1/budgets"):
    return SimpleNamespace(method=method, url=SimpleNamespace(path=path))


def _raising_sink(payload, request):
    raise RuntimeError("db down")


@pytest.fixture(autouse=True)
def _reset_sink():
    yield
    pa.register_privileged_access_sink(None)


class TestBuildPrivilegedAccessKwargs:
    def test_maps_actor_target_and_request_fields(self):
        payload = {"user_id": "u1", "customer_id": "c1"}
        kwargs = pa.build_privileged_access_kwargs(payload, _request("POST", "/api/v1/budgets/1"))

        assert kwargs["actor_user_id"] == "u1"
        assert kwargs["customer_id"] == "c1"
        assert kwargs["method"] == "POST"
        assert kwargs["path"] == "/api/v1/budgets/1"
        assert kwargs["created_at"] is not None


class TestMakePrivilegedAccessSink:
    def test_sink_inserts_and_commits_a_row(self):
        engine = create_engine("sqlite:///:memory:")
        _Base.metadata.create_all(engine, tables=[_FakePrivilegedAccessLog.__table__])
        db = sessionmaker(bind=engine)()
        sink = pa.make_privileged_access_sink(lambda: db, _FakePrivilegedAccessLog)
        payload = {"user_id": "u1", "customer_id": "c1"}

        sink(payload, _request("POST", "/x"))

        [row] = db.query(_FakePrivilegedAccessLog).all()
        assert row.actor_user_id == "u1"
        assert row.customer_id == "c1"
        assert row.method == "POST"
        assert row.path == "/x"


class TestLogPrivilegedAccess:
    def test_calls_the_registered_sink(self):
        calls = []
        pa.register_privileged_access_sink(lambda payload, request: calls.append(payload))

        pa.log_privileged_access({"user_id": "u1"}, _request())

        assert calls == [{"user_id": "u1"}]

    def test_no_request_is_a_no_op(self):
        calls = []
        pa.register_privileged_access_sink(lambda payload, request: calls.append(payload))

        pa.log_privileged_access({"user_id": "u1"}, None)

        assert calls == []

    def test_read_fails_open_when_sink_raises(self):
        pa.register_privileged_access_sink(_raising_sink)

        pa.log_privileged_access({"user_id": "u1"}, _request("GET"))  # does not raise

    def test_write_fails_closed_when_sink_raises(self):
        pa.register_privileged_access_sink(_raising_sink)

        with pytest.raises(HTTPException) as exc:
            pa.log_privileged_access({"user_id": "u1"}, _request("POST"))
        assert exc.value.status_code == 503

    def test_write_fails_closed_when_no_sink_registered(self):
        with pytest.raises(HTTPException) as exc:
            pa.log_privileged_access({"user_id": "u1"}, _request("DELETE"))
        assert exc.value.status_code == 503

    def test_read_fails_open_when_no_sink_registered(self):
        pa.log_privileged_access({"user_id": "u1"}, _request("HEAD"))  # does not raise
