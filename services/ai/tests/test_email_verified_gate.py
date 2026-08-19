"""session-security: an unverified token is rejected with 403 end-to-end,
via a real TestClient/JWT (no `get_validated_user` override)."""

from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from shared.security.jwt_utils import create_access_token


def _token(email_verified: bool) -> str:
    return create_access_token(
        {
            "user_id": str(uuid4()),
            "session_id": str(uuid4()),
            "role": "superuser",
            "customer_id": str(uuid4()),
            "email_verified": email_verified,
        }
    )


class TestAiSettingsEndpointRequiresVerifiedEmail:
    def test_unverified_token_rejected_with_403(self):
        client = TestClient(app)
        resp = client.get(
            "/api/v1/ai/settings",
            headers={"Authorization": f"Bearer {_token(email_verified=False)}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "email_not_verified"

    def test_verified_token_is_not_blocked_by_the_verification_gate(self):
        client = TestClient(app)
        resp = client.get(
            "/api/v1/ai/settings",
            headers={"Authorization": f"Bearer {_token(email_verified=True)}"},
        )
        assert resp.status_code != 403
