import os
from contextlib import ExitStack

os.environ.setdefault("CHAT_DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.chat_routes import get_validated_user  # noqa: E402
from main import app  # noqa: E402,F401
from tests.factories.user import ValidUserFactory  # noqa: E402


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
