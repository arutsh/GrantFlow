"""Tests for shared/security/jwt_utils.py's decode_access_token — in
particular both of its error branches. A prior version of this module
caught `jwt.PyJWTError` (a PyJWT name that doesn't exist in python-jose,
the library actually in use here) instead of `jwt.JWTError`, so the
generic-invalid-token branch silently raised an unhandled AttributeError
instead of the intended ValueError. No test caught it because none of
this module's error paths were exercised at all.
"""

from datetime import timedelta

import pytest

from shared.security.jwt_utils import create_access_token, decode_access_token


class TestDecodeAccessToken:
    def test_round_trips_a_freshly_issued_token(self):
        token = create_access_token({"user_id": "u1"})
        payload = decode_access_token(token)
        assert payload["user_id"] == "u1"

    def test_expired_token_raises_value_error(self):
        token = create_access_token({"user_id": "u1"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(ValueError, match="expired"):
            decode_access_token(token)

    def test_malformed_token_raises_value_error(self):
        # Not a JWT at all — this is the generic jwt.JWTError branch that
        # `jwt.PyJWTError` (a typo for a different library's exception
        # class) previously failed to catch.
        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token("not-a-valid-token")
