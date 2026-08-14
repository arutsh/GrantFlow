from unittest.mock import patch

import fakeredis
import pytest
from fastapi import HTTPException

from shared.security import session_revocation
from shared.security.dependencies import get_current_user, get_validated_user
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


class TestGetValidatedUserSpanAttribute:
    def test_sets_user_id_on_the_active_span(self):
        user_id = "44444444-4444-4444-4444-444444444444"
        token = _token_for(user_id, "session-e")
        current_user = get_current_user(token=token)

        with patch("shared.security.dependencies.set_span_attributes") as mock_set_span_attrs:
            payload = get_validated_user(user=current_user)

        mock_set_span_attrs.assert_called_once_with(user_id=user_id)
        assert payload["user_id"] == user_id

    def test_reuses_the_already_decoded_payload_without_re_decoding(self):
        """get_validated_user must not re-verify the JWT signature — the
        token has already been decoded and validated by get_current_user."""
        user_id = "55555555-5555-5555-5555-555555555555"
        token = _token_for(user_id, "session-f")
        current_user = get_current_user(token=token)

        with patch("shared.security.dependencies.decode_access_token") as mock_decode:
            payload = get_validated_user(user=current_user)

        mock_decode.assert_not_called()
        assert payload["user_id"] == user_id
        assert payload["token"] == token
