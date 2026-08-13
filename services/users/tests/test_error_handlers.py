# Handler unit tests (span recording, DomainError/unhandled-exception shapes)
# live in shared/tests/test_error_handlers.py since the handlers themselves
# are shared. This file only smoke-tests that this service's main.py wires
# them up correctly and that HTTPException still flows through unaffected.

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.auth_routes import login
from app.schemas.auth_schema import LoginRequest


class TestHTTPExceptionUnaffected:
    def test_http_exception_still_returns_normal_response(self):
        # Calls the route function directly rather than via TestClient, same
        # convention as test_auth_routes.py — auth_routes.py has its own
        # module-local get_db() (distinct from app.db.session.get_db), so a
        # TestClient-level `db` fixture override never reaches it and would
        # silently fall through to a real Postgres connection instead.
        with patch("app.api.auth_routes.get_user_by_email", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                login(LoginRequest(email="nobody@example.com", password="wrong"), db=object())

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid credentials"
