import fakeredis
import pytest
from fastapi import HTTPException

from shared.security import session_revocation
from shared.security.dependencies import get_current_user
from shared.security.jwt_utils import create_access_token


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = fakeredis.FakeStrictRedis()
    monkeypatch.setattr(session_revocation, "_redis_client", fake)
    return fake


def _token_for(user_id: str, session_id: str) -> str:
    return create_access_token({"user_id": user_id, "session_id": session_id, "role": "user"})


class TestGetCurrentUserRevocation:
    def test_active_session_is_accepted(self):
        user_id = "11111111-1111-1111-1111-111111111111"
        result = get_current_user(token=_token_for(user_id, "session-a"))
        assert str(result["user_id"]) == user_id
        assert result["session_id"] == "session-a"

    def test_revoked_session_rejected_even_with_a_still_valid_token(self):
        """The core session-security requirement: revocation is enforced on
        every request, not only at issuance — a session revoked mid-lifetime
        must stop working before its access token naturally expires."""
        user_id = "22222222-2222-2222-2222-222222222222"
        token = _token_for(user_id, "session-b")

        # Works before revocation.
        get_current_user(token=token)

        session_revocation.mark_session_revoked("session-b", ttl_seconds=3600)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token)
        assert exc_info.value.status_code == 401

    def test_revoking_one_session_does_not_affect_another(self):
        user_id = "33333333-3333-3333-3333-333333333333"
        token_a = _token_for(user_id, "session-c")
        token_b = _token_for(user_id, "session-d")

        session_revocation.mark_session_revoked("session-c", ttl_seconds=3600)

        with pytest.raises(HTTPException):
            get_current_user(token=token_a)

        # Session d is untouched.
        result = get_current_user(token=token_b)
        assert result["session_id"] == "session-d"
