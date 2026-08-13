# Handler unit tests (span recording, DomainError/unhandled-exception shapes)
# live in shared/tests/test_error_handlers.py since the handlers themselves
# are shared. This file only smoke-tests that this service's main.py wires
# them up correctly and that HTTPException still flows through unaffected.


class TestHTTPExceptionUnaffected:
    def test_http_exception_still_returns_normal_response(self, make_client, db):
        client = make_client(db=db)

        response = client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid credentials"}
