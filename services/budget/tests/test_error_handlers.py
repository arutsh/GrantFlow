from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.budget_routes import get_validated_user
from main import app
from tests.factories.user import make_valid_user

# Handler unit tests (span recording, DomainError/unhandled-exception shapes)
# live in shared/tests/test_error_handlers.py since the handlers themselves
# are shared. This file only smoke-tests that this service's main.py wires
# them up correctly and that HTTPException still flows through unaffected.


class TestHTTPExceptionUnaffected:
    def test_http_exception_still_returns_normal_response(self):
        app.dependency_overrides[get_validated_user] = lambda: make_valid_user()
        client = TestClient(app)
        try:
            with patch(
                "app.api.budget_routes.update_budget_service",
                new_callable=AsyncMock,
                return_value=None,
            ):
                response = client.patch(
                    f"/api/v1/budgets/{'00000000-0000-0000-0000-000000000000'}",
                    json={"name": "Renamed"},
                )
        finally:
            app.dependency_overrides = {}

        assert response.status_code == 404
        assert response.json() == {"detail": "Not Found"}
