"""Tests for the gdpr-iso27001-priority-1 additions to auth_routes.py:
login lockout, change-password, logout, and session listing/revocation.

Follows this module's existing convention (see test_auth_routes.py) of
calling route functions directly with a mocked crud layer, no real DB.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.auth_routes import (
    change_password,
    list_sessions,
    login,
    logout,
    refresh_token,
    register_endpoint,
    revoke_one_session,
    verify_email,
)
from app.schemas.auth_schema import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    VerifyEmailRequest,
)
from tests.factories.user import UserModelFactory


class TestLoginLockout:
    def test_locked_out_returns_429_before_checking_credentials(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=True),
            patch("app.api.auth_routes.get_user_by_email") as mock_get_user,
        ):
            with pytest.raises(HTTPException) as exc_info:
                login(LoginRequest(email="a@b.com", password="x"), db=MagicMock())
        assert exc_info.value.status_code == 429
        mock_get_user.assert_not_called()

    def test_failed_login_records_the_attempt(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.get_user_by_email", return_value=None),
            patch("app.api.auth_routes.record_failed_attempt") as mock_record,
        ):
            with pytest.raises(HTTPException) as exc_info:
                login(LoginRequest(email="a@b.com", password="x"), db=MagicMock())
        assert exc_info.value.status_code == 401
        mock_record.assert_called_once()

    def test_successful_login_clears_failed_attempts(self):
        user = UserModelFactory.build(customer_id=None)
        user.customer = None
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch("app.api.auth_routes.verify_password", return_value=True),
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
            patch("app.api.auth_routes.clear_failed_attempts") as mock_clear,
        ):
            login(LoginRequest(email=user.email, password="pw"), db=MagicMock())
        mock_clear.assert_called_once()

    def test_deleted_account_cannot_log_in(self):
        user = UserModelFactory.build(
            customer_id=None, deleted_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        user.customer = None
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
        ):
            with pytest.raises(HTTPException) as exc_info:
                login(LoginRequest(email=user.email, password="whatever"), db=MagicMock())
        assert exc_info.value.status_code == 401


class TestVerifyEmailLockout:
    """verify-email takes the same class of attacker-guessable input
    (email + token) as login, so it reuses the same lockout mechanism
    under a separate `bucket` — see login_rate_limiter.py."""

    def test_locked_out_returns_429_before_checking_the_token(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=True),
            patch("app.api.auth_routes.get_user_by_verification_token") as mock_lookup,
        ):
            with pytest.raises(HTTPException) as exc_info:
                verify_email(VerifyEmailRequest(email="a@b.com", token="x"), db=MagicMock())
        assert exc_info.value.status_code == 429
        mock_lookup.assert_not_called()

    def test_invalid_token_records_the_attempt(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.get_user_by_verification_token", return_value=None),
            patch("app.api.auth_routes.record_failed_attempt") as mock_record,
        ):
            with pytest.raises(HTTPException) as exc_info:
                verify_email(VerifyEmailRequest(email="a@b.com", token="x"), db=MagicMock())
        assert exc_info.value.status_code == 400
        mock_record.assert_called_once()
        assert mock_record.call_args.kwargs.get("bucket") == "verify_email"

    def test_successful_verification_clears_failed_attempts(self):
        user = UserModelFactory.build(
            email_verification_expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(hours=1)
        )
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.get_user_by_verification_token", return_value=user),
            patch("app.api.auth_routes.mark_email_verified"),
            patch("app.api.auth_routes.clear_failed_attempts") as mock_clear,
        ):
            verify_email(VerifyEmailRequest(email=user.email, token="x"), db=MagicMock())
        mock_clear.assert_called_once()
        assert mock_clear.call_args.kwargs.get("bucket") == "verify_email"


class TestRegisterPassesConsentThrough:
    def test_consent_flags_forwarded_to_create_user(self):
        created_user = UserModelFactory.build(customer_id=None)
        with (
            patch(
                "app.api.auth_routes.create_user", AsyncMock(return_value=created_user)
            ) as mock_create_user,
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
            patch("app.api.auth_routes.get_customer", MagicMock()),
            patch("app.api.auth_routes.set_email_verification_token", return_value="raw-token"),
            patch("app.api.auth_routes.enqueue_verification_email"),
        ):
            asyncio.run(
                register_endpoint(
                    RegisterRequest(
                        email="new@example.com",
                        password="Correct-Horse-1",
                        consent_data_processing=True,
                        consent_marketing=True,
                    ),
                    db=object(),
                )
            )
        assert mock_create_user.call_args.kwargs["consent_data_processing"] is True
        assert mock_create_user.call_args.kwargs["consent_marketing"] is True


class TestChangePassword:
    def test_success_rehashes_and_stores_new_password(self):
        user = UserModelFactory.build(hashed_password="old-hash")
        with (
            patch("app.api.auth_routes.get_user", return_value=user),
            patch("app.api.auth_routes.verify_password", return_value=True),
            patch("app.api.auth_routes.hash_password", return_value="new-hash"),
            patch("app.api.auth_routes.get_non_revoked_sessions_for_user", return_value=[]),
        ):
            resp = change_password(
                ChangePasswordRequest(current_password="old", new_password="Correct-Horse-2"),
                current_user={"user_id": user.id},
                db=MagicMock(),
            )
        assert resp == {"changed": True}
        assert user.hashed_password == "new-hash"

    def test_wrong_current_password_rejected(self):
        user = UserModelFactory.build(hashed_password="old-hash")
        with (
            patch("app.api.auth_routes.get_user", return_value=user),
            patch("app.api.auth_routes.verify_password", return_value=False),
            patch("app.api.auth_routes.record_failed_attempt") as mock_record,
        ):
            with pytest.raises(HTTPException) as exc_info:
                change_password(
                    ChangePasswordRequest(current_password="wrong", new_password="Correct-Horse-2"),
                    current_user={"user_id": user.id},
                    db=MagicMock(),
                )
        assert exc_info.value.status_code == 401
        mock_record.assert_called_once()
        assert mock_record.call_args.kwargs.get("bucket") == "change_password"

    def test_weak_new_password_rejected(self):
        user = UserModelFactory.build(hashed_password="old-hash")
        with (
            patch("app.api.auth_routes.get_user", return_value=user),
            patch("app.api.auth_routes.verify_password", return_value=True),
        ):
            with pytest.raises(HTTPException) as exc_info:
                change_password(
                    ChangePasswordRequest(current_password="old", new_password="12345678"),
                    current_user={"user_id": user.id},
                    db=MagicMock(),
                )
        assert exc_info.value.status_code == 400

    def test_locked_out_returns_429_before_checking_credentials(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=True),
            patch("app.api.auth_routes.get_user") as mock_get_user,
        ):
            with pytest.raises(HTTPException) as exc_info:
                change_password(
                    ChangePasswordRequest(
                        current_password="whatever", new_password="Correct-Horse-2"
                    ),
                    current_user={"user_id": uuid4()},
                    db=MagicMock(),
                )
        assert exc_info.value.status_code == 429
        mock_get_user.assert_not_called()

    def test_revokes_other_sessions_but_not_the_callers_own(self):
        user = UserModelFactory.build(hashed_password="old-hash")
        own_session = SimpleNamespace(id=str(uuid4()), revoked=False)
        other_session = SimpleNamespace(id=str(uuid4()), revoked=False)
        with (
            patch("app.api.auth_routes.get_user", return_value=user),
            patch("app.api.auth_routes.verify_password", return_value=True),
            patch("app.api.auth_routes.hash_password", return_value="new-hash"),
            patch(
                "app.api.auth_routes.get_non_revoked_sessions_for_user",
                return_value=[own_session, other_session],
            ),
            patch(
                "app.api.auth_routes.revoke_session",
                side_effect=lambda db, s: (setattr(s, "revoked", True), s)[1],
            ),
            patch("app.api.auth_routes.mark_session_revoked") as mock_mark,
        ):
            change_password(
                ChangePasswordRequest(current_password="old", new_password="Correct-Horse-2"),
                current_user={"user_id": user.id, "session_id": own_session.id},
                db=MagicMock(),
            )
        assert own_session.revoked is False
        assert other_session.revoked is True
        mock_mark.assert_called_once()
        assert mock_mark.call_args.args[0] == str(other_session.id)


class TestLogout:
    def test_revokes_the_callers_session_everywhere(self):
        session = SimpleNamespace(id=str(uuid4()), revoked=False)
        with (
            patch("app.api.auth_routes.get_session_by_id", return_value=session),
            patch(
                "app.api.auth_routes.revoke_session",
                side_effect=lambda db, s: (setattr(s, "revoked", True), s)[1],
            ),
            patch("app.api.auth_routes.mark_session_revoked") as mock_mark,
        ):
            resp = logout(current_user={"session_id": session.id}, db=MagicMock())
        assert resp == {"logged_out": True}
        assert session.revoked is True
        mock_mark.assert_called_once()

    def test_already_revoked_session_is_a_noop(self):
        session = SimpleNamespace(id=str(uuid4()), revoked=True)
        with (
            patch("app.api.auth_routes.get_session_by_id", return_value=session),
            patch("app.api.auth_routes.revoke_session") as mock_revoke,
            patch("app.api.auth_routes.mark_session_revoked") as mock_mark,
        ):
            logout(current_user={"session_id": session.id}, db=MagicMock())
        mock_revoke.assert_not_called()
        mock_mark.assert_not_called()


class TestListSessions:
    def test_flags_the_current_session(self):
        current_id = str(uuid4())
        other_id = str(uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        sessions = [
            SimpleNamespace(id=current_id, issued_at=now, expires_at=now),
            SimpleNamespace(id=other_id, issued_at=now, expires_at=now),
        ]
        with patch("app.api.auth_routes.get_non_revoked_sessions_for_user", return_value=sessions):
            result = list_sessions(
                current_user={"user_id": str(uuid4()), "session_id": current_id}, db=MagicMock()
            )
        by_id = {str(s.id): s for s in result}
        assert by_id[current_id].current is True
        assert by_id[other_id].current is False


class TestRefreshRejectsRevokedSession:
    def test_revoked_session_cannot_refresh(self):
        session = SimpleNamespace(id=str(uuid4()), revoked=True)
        with (
            patch("app.api.auth_routes._cache_get", return_value=str(session.id)),
            patch("app.api.auth_routes._delete_key"),
            patch("app.api.auth_routes.get_session_by_id", return_value=session),
        ):
            with pytest.raises(HTTPException) as exc_info:
                refresh_token(refresh_token="some-refresh-token", db=MagicMock())
        assert exc_info.value.status_code == 401


class TestRevokeOneSession:
    def test_owner_can_revoke_without_affecting_others(self):
        user_id = str(uuid4())
        target = SimpleNamespace(id=str(uuid4()), user_id=user_id, revoked=False)
        with (
            patch("app.api.auth_routes.get_session_by_id", return_value=target),
            patch(
                "app.api.auth_routes.revoke_session",
                side_effect=lambda db, s: (setattr(s, "revoked", True), s)[1],
            ),
            patch("app.api.auth_routes.mark_session_revoked") as mock_mark,
        ):
            resp = revoke_one_session(
                session_id=target.id, current_user={"user_id": user_id}, db=MagicMock()
            )
        assert resp == {"revoked": True}
        assert target.revoked is True
        mock_mark.assert_called_once()

    def test_cannot_revoke_another_users_session(self):
        target = SimpleNamespace(id=str(uuid4()), user_id=str(uuid4()), revoked=False)
        with patch("app.api.auth_routes.get_session_by_id", return_value=target):
            with pytest.raises(HTTPException) as exc_info:
                revoke_one_session(
                    session_id=target.id, current_user={"user_id": str(uuid4())}, db=MagicMock()
                )
        assert exc_info.value.status_code == 404
