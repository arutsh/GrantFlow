import pytest
from main import app
from app.api.parse_routes import get_validated_user
from app.services.provider import get_resolved_model
from tests.factories.user import ValidUserFactory
from tests.factories.provider import ResolvedModelFactory
from fastapi.testclient import TestClient
from contextlib import ExitStack


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
