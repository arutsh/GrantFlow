import os

# Must be set before any test module imports `main` — importing it initializes
# OpenTelemetry, and without this guard test runs try to export telemetry to a
# collector on localhost:4317 (slow runs + "Logging error" noise at shutdown).
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from shared.security.dependencies import get_validated_user  # noqa: E402
from tests.factories.user import ValidUserFactory  # noqa: E402


@pytest.fixture
def make_client():
    """Build a TestClient authenticated as a fresh fake user.

    Usage:
        client = make_client()                    # regular user
        client = make_client(role="superuser")    # override any JWT field
        client.user                               # the fake JWT payload dict

    Older test files carry their own autouse auth override; new tests should
    use this instead.
    """

    def _make(**user_kwargs):
        user = ValidUserFactory(**user_kwargs)
        app.dependency_overrides[get_validated_user] = lambda: user
        client = TestClient(app)
        client.user = user
        return client

    yield _make
    app.dependency_overrides = {}
