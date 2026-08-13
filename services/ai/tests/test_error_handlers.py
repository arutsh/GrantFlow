# Handler unit tests (span recording, DomainError/unhandled-exception shapes)
# live in shared/tests/test_error_handlers.py since the handlers themselves
# are shared. This file only smoke-tests that this service's main.py wires
# them up correctly and that HTTPException still flows through unaffected.


class TestHTTPExceptionUnaffected:
    def test_http_exception_still_returns_normal_response(self, make_client):
        client = make_client(role="user")

        response = client.get("/api/v1/ai/settings")

        assert response.status_code == 403
        assert response.json() == {"detail": "Admin or superuser role required"}
