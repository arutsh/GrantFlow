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

from main import app  # noqa: E402
from app.utils.security import get_current_user  # noqa: E402
from tests.factories.user import ValidUserFactory  # noqa: E402


@pytest.fixture
def make_client():
    """Build a TestClient with a fake authenticated user and (optionally) a
    mocked outbound AI service.

    Usage:
        client = make_client()                  # no outbound HTTP expected
        client = make_client(handler=handler)   # httpx.MockTransport handler
        client.user                             # the fake JWT payload dict

    The users lifespan connects to RabbitMQ (init_publisher) — patched out —
    and creates app.state.http_client, which is replaced by a MockTransport
    client when a handler is given.
    """
    stack = ExitStack()

    def _make(handler=None, **user_kwargs):
        user = ValidUserFactory(**user_kwargs)
        app.dependency_overrides[get_current_user] = lambda: user
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
