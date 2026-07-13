import pytest

from app.api.parse_routes import get_validated_user
from app.services.provider import get_resolved_model
from tests.factories.user import ValidUserFactory
from tests.factories.provider import ResolvedModelFactory
from fastapi.testclient import TestClient
from contextlib import ExitStack

import os

os.environ.setdefault("AI_DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from main import app  # noqa: E402


@pytest.fixture
def anyio_backend():
    """Run @pytest.mark.anyio tests on asyncio only.

    anyio's built-in fixture parametrizes every anyio test over both asyncio
    and trio, but this service is asyncio-only and trio isn't installed.
    """
    return "asyncio"


@pytest.fixture
def make_client():
    stack = ExitStack()

    def _make(resolved=None, **user_kwargs):
        user = ValidUserFactory(**user_kwargs)
        model = ResolvedModelFactory() if resolved else None
        app.dependency_overrides[get_validated_user] = lambda: user
        app.dependency_overrides[get_resolved_model] = lambda: model
        client = stack.enter_context(TestClient(app))
        client.user = user
        return client

    yield _make
    stack.close()
    app.dependency_overrides = {}
