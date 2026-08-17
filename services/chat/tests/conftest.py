import os
from contextlib import ExitStack

os.environ.setdefault("CHAT_DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.api.chat_routes import get_validated_user  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.privileged_access_log import PrivilegedAccessLog  # noqa: E402
from main import app  # noqa: E402,F401
from tests.factories.user import ValidUserFactory  # noqa: E402


@pytest.fixture
def db():
    """Real in-memory sqlite session covering PrivilegedAccessLog — sync,
    matching this sink's deliberately sync design (see
    app/services/privileged_access_audit.py). Add tables here as more tests
    need a real DB session for this service."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[PrivilegedAccessLog.__table__])
    return sessionmaker(bind=engine)()


@pytest.fixture
def anyio_backend():
    """Run @pytest.mark.anyio tests on asyncio only (trio isn't installed)."""
    return "asyncio"


@pytest.fixture
def make_client():
    stack = ExitStack()

    def _make(**user_kwargs):
        user = ValidUserFactory(**user_kwargs)
        app.dependency_overrides[get_validated_user] = lambda: user
        client = stack.enter_context(TestClient(app))
        client.user = user
        return client

    yield _make
    stack.close()
    app.dependency_overrides = {}
