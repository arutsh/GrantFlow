"""Users-service test bootstrap.

Everything here must run before any test module imports `main`:
importing it initializes OpenTelemetry and calls init_db() (a real
Postgres connection) at module level.
"""

import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import app.db.init_db as _init_db_module  # noqa: E402

# main.py calls init_db() at import time; tests have no database.
_init_db_module.init_db = lambda: None

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from main import app  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.customer import CustomerModel, DonorGranteeModel  # noqa: E402
from app.models.privileged_access_log import PrivilegedAccessLog  # noqa: E402
from app.utils.security import get_current_user  # noqa: E402
from shared.security.dependencies import get_validated_user  # noqa: E402
from tests.factories.user import ValidUserFactory  # noqa: E402


@pytest.fixture
def db():
    """Real in-memory sqlite session covering Customer/DonorGrantee/
    PrivilegedAccessLog — shared by any test that needs the model's real
    FKs/@validates/unique constraint rather than mocking the crud layer (see
    services/budget/tests/conftest.py for the sibling pattern).
    """
    # TestClient runs route handlers in a worker thread, so the sqlite
    # connection needs check_same_thread=False; StaticPool keeps every
    # connection pointing at the same in-memory DB rather than each getting
    # its own empty one.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            CustomerModel.__table__,
            DonorGranteeModel.__table__,
            PrivilegedAccessLog.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


@pytest.fixture
def make_client():
    """Build a TestClient with a fake authenticated user and (optionally) a
    mocked outbound AI service.

    Usage:
        client = make_client()                  # no outbound HTTP expected
        client = make_client(handler=handler)   # httpx.MockTransport handler
        client = make_client(is_donor=True)      # override any JWT field
        client = make_client(db=db)              # route the get_db dependency to
                                                  # a real session (see the `db`
                                                  # fixture above)
        client.user                             # the fake JWT payload dict

    Overrides both get_current_user and get_validated_user with the same fake
    payload, since routes depend on either one depending on how much of the
    JWT claims they need (donor-grantee routes need get_validated_user's full
    payload for customer_id/is_donor/is_ngo).

    The users lifespan connects to RabbitMQ (init_publisher) — patched out —
    and creates app.state.http_client, which is replaced by a MockTransport
    client when a handler is given.
    """
    stack = ExitStack()

    def _make(handler=None, db=None, **user_kwargs):
        user = ValidUserFactory(**user_kwargs)
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_validated_user] = lambda: user
        if db is not None:
            app.dependency_overrides[get_db] = lambda: db
        stack.enter_context(patch("main.init_publisher", AsyncMock()))
        stack.enter_context(patch("main.close_publisher", AsyncMock()))
        client = stack.enter_context(TestClient(app))
        if handler is not None:
            app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client.user = user
        return client

    yield _make
    stack.close()
    app.dependency_overrides = {}
