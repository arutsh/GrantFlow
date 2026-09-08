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
    start_impersonation,
    verify_email,
)
from app.schemas.auth_schema import (
    ChangePasswordRequest,
    ImpersonateRequest,
    LoginRequest,
    RegisterRequest,
    VerifyEmailRequest,
)
from app.utils.security import decode_access_token
from tests.factories.user import UserModelFactory


@pytest.mark.anyio
class TestLoginLockout:
    async def test_locked_out_returns_429_before_checking_credentials(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=True),
            patch("app.api.auth_routes.get_user_by_email") as mock_get_user,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await login(LoginRequest(email="a@b.com", password="x"), db=MagicMock())
        assert exc_info.value.status_code == 429
        mock_get_user.assert_not_called()

    async def test_failed_login_records_the_attempt(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.get_user_by_email", return_value=None),
            patch("app.api.auth_routes.record_failed_attempt") as mock_record,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await login(LoginRequest(email="a@b.com", password="x"), db=MagicMock())
        assert exc_info.value.status_code == 401
        mock_record.assert_called_once()

    async def test_successful_login_clears_failed_attempts(self):
        user = UserModelFactory.build(customer_id=None, email_verified=True)
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
            await login(LoginRequest(email=user.email, password="pw"), db=MagicMock())
        mock_clear.assert_called_once()

    async def test_deleted_account_cannot_log_in(self):
        user = UserModelFactory.build(
            customer_id=None, deleted_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        user.customer = None
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await login(LoginRequest(email=user.email, password="whatever"), db=MagicMock())
        assert exc_info.value.status_code == 401


@pytest.mark.anyio
class TestLoginGatedOnVerification:
    """Correct credentials alone no longer issue a session for an unverified account."""

    async def test_unverified_account_gets_no_session(self):
        user = UserModelFactory.build(customer_id=None, email_verified=False)
        user.customer = None
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch("app.api.auth_routes.verify_password", return_value=True),
            patch("app.api.auth_routes.create_session") as mock_create_session,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await login(LoginRequest(email=user.email, password="pw"), db=MagicMock())
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "email_not_verified"
        mock_create_session.assert_not_called()

    async def test_verified_account_logs_in_as_before(self):
        user = UserModelFactory.build(customer_id=None, email_verified=True)
        user.customer = None
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch("app.api.auth_routes.verify_password", return_value=True),
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
        ):
            resp = await login(LoginRequest(email=user.email, password="pw"), db=MagicMock())
        assert resp.access_token
        assert decode_access_token(resp.access_token)["email_verified"] is True


@pytest.mark.anyio
class TestVerifyEmailLockout:
    """verify-email takes the same class of attacker-guessable input
    (email + token) as login, so it reuses the same lockout mechanism
    under a separate `bucket` — see login_rate_limiter.py."""

    async def test_locked_out_returns_429_before_checking_the_token(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=True),
            patch("app.api.auth_routes.get_user_by_verification_token") as mock_lookup,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_email(VerifyEmailRequest(email="a@b.com", token="x"), db=MagicMock())
        assert exc_info.value.status_code == 429
        mock_lookup.assert_not_called()

    async def test_invalid_token_records_the_attempt(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.get_user_by_verification_token", return_value=None),
            patch("app.api.auth_routes.record_failed_attempt") as mock_record,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_email(VerifyEmailRequest(email="a@b.com", token="x"), db=MagicMock())
        assert exc_info.value.status_code == 400
        mock_record.assert_called_once()
        assert mock_record.call_args.kwargs.get("bucket") == "verify_email"

    async def test_successful_verification_clears_failed_attempts(self):
        user = UserModelFactory.build(
            customer_id=None,
            email_verification_expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(hours=1),
        )
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.get_user_by_verification_token", return_value=user),
            patch("app.api.auth_routes.mark_email_verified", return_value=user),
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
            patch("app.api.auth_routes.get_customer", AsyncMock()),
            patch("app.api.auth_routes.clear_failed_attempts") as mock_clear,
        ):
            await verify_email(VerifyEmailRequest(email=user.email, token="x"), db=MagicMock())
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
            patch("app.api.auth_routes.get_customer", AsyncMock()),
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


def _register(role_in_payload=None, **overrides):
    kwargs = {
        "email": "attacker@example.com",
        "password": "Correct-Horse-1",
        "consent_data_processing": True,
        **overrides,
    }
    if role_in_payload is not None:
        kwargs["role"] = role_in_payload  # dropped by RegisterRequest, not a real field
    return RegisterRequest(**kwargs)


@pytest.mark.anyio
class TestRegisterCannotSetPrivilegedRole:
    """Register as superuser, then check the role verify-email's session issues."""

    async def _register_then_verify(self, role_in_payload):
        created_user = UserModelFactory.build(customer_id=None, role="user")
        with (
            patch(
                "app.api.auth_routes.create_user", AsyncMock(return_value=created_user)
            ) as mock_create_user,
            patch("app.api.auth_routes.set_email_verification_token", return_value="raw-token"),
            patch("app.api.auth_routes.enqueue_verification_email"),
        ):
            await register_endpoint(_register(role_in_payload=role_in_payload), db=object())

        created_user.email_verification_expires_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + timedelta(hours=1)
        with (
            patch("app.api.auth_routes.get_user_by_verification_token", return_value=created_user),
            patch("app.api.auth_routes.mark_email_verified", return_value=created_user),
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
            patch("app.api.auth_routes.get_customer", AsyncMock()),
        ):
            verify_resp = await verify_email(
                VerifyEmailRequest(email=created_user.email, token="raw-token"), db=object()
            )
        return created_user, verify_resp, mock_create_user

    async def test_superuser_in_payload_is_dropped_before_create_user(self):
        _, _, mock_create_user = await self._register_then_verify("superuser")
        assert "role" not in mock_create_user.call_args.kwargs

    async def test_admin_in_payload_still_persists_and_issues_a_user_role(self):
        created_user, verify_resp, _ = await self._register_then_verify("admin")
        assert created_user.role == "user"
        assert decode_access_token(verify_resp.access_token)["role"] == "user"

    async def test_registered_role_user_cannot_self_authorize_impersonation(self):
        _, verify_resp, _ = await self._register_then_verify("superuser")
        claims = decode_access_token(verify_resp.access_token)
        actor = {"user_id": claims["user_id"], "role": claims["role"]}

        with pytest.raises(HTTPException) as exc_info:
            await start_impersonation(ImpersonateRequest(customer_id=uuid4()), actor, db=object())
        assert exc_info.value.status_code == 403


class TestRegisterLockout:
    def test_locked_out_returns_429_before_creating_user(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=True),
            patch("app.api.auth_routes.create_user") as mock_create_user,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(register_endpoint(_register(), db=object()))
        assert exc_info.value.status_code == 429
        mock_create_user.assert_not_called()

    def test_duplicate_email_records_the_attempt(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch(
                "app.api.auth_routes.create_user",
                AsyncMock(side_effect=ValueError("Email already registered")),
            ),
            patch("app.api.auth_routes.record_failed_attempt") as mock_record,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(register_endpoint(_register(), db=object()))
        assert exc_info.value.status_code == 400
        mock_record.assert_called_once()
        assert mock_record.call_args.kwargs.get("bucket") == "register"

    def test_successful_registration_clears_failed_attempts(self):
        created_user = UserModelFactory.build(customer_id=None, role="user")
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.create_user", AsyncMock(return_value=created_user)),
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
            patch("app.api.auth_routes.get_customer", AsyncMock()),
            patch("app.api.auth_routes.set_email_verification_token", return_value="raw-token"),
            patch("app.api.auth_routes.enqueue_verification_email"),
            patch("app.api.auth_routes.clear_failed_attempts") as mock_clear,
        ):
            asyncio.run(register_endpoint(_register(), db=object()))
        mock_clear.assert_called_once()
        assert mock_clear.call_args.kwargs.get("bucket") == "register"


@pytest.mark.anyio
class TestChangePassword:
    async def test_success_rehashes_and_stores_new_password(self):
        user = UserModelFactory.build(hashed_password="old-hash")
        with (
            patch("app.api.auth_routes.get_user", return_value=user),
            patch("app.api.auth_routes.verify_password", return_value=True),
            patch("app.api.auth_routes.hash_password", return_value="new-hash"),
            patch("app.api.auth_routes.get_non_revoked_sessions_for_user", return_value=[]),
        ):
            resp = await change_password(
                ChangePasswordRequest(current_password="old", new_password="Correct-Horse-2"),
                current_user={"user_id": user.id},
                db=AsyncMock(),
            )
        assert resp == {"changed": True}
        assert user.hashed_password == "new-hash"

    async def test_wrong_current_password_rejected(self):
        user = UserModelFactory.build(hashed_password="old-hash")
        with (
            patch("app.api.auth_routes.get_user", return_value=user),
            patch("app.api.auth_routes.verify_password", return_value=False),
            patch("app.api.auth_routes.record_failed_attempt") as mock_record,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await change_password(
                    ChangePasswordRequest(current_password="wrong", new_password="Correct-Horse-2"),
                    current_user={"user_id": user.id},
                    db=MagicMock(),
                )
        assert exc_info.value.status_code == 401
        mock_record.assert_called_once()
        assert mock_record.call_args.kwargs.get("bucket") == "change_password"

    async def test_weak_new_password_rejected(self):
        user = UserModelFactory.build(hashed_password="old-hash")
        with (
            patch("app.api.auth_routes.get_user", return_value=user),
            patch("app.api.auth_routes.verify_password", return_value=True),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await change_password(
                    ChangePasswordRequest(current_password="old", new_password="12345678"),
                    current_user={"user_id": user.id},
                    db=MagicMock(),
                )
        assert exc_info.value.status_code == 400

    async def test_locked_out_returns_429_before_checking_credentials(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=True),
            patch("app.api.auth_routes.get_user") as mock_get_user,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await change_password(
                    ChangePasswordRequest(
                        current_password="whatever", new_password="Correct-Horse-2"
                    ),
                    current_user={"user_id": uuid4()},
                    db=MagicMock(),
                )
        assert exc_info.value.status_code == 429
        mock_get_user.assert_not_called()

    async def test_revokes_other_sessions_but_not_the_callers_own(self):
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
            await change_password(
                ChangePasswordRequest(current_password="old", new_password="Correct-Horse-2"),
                current_user={"user_id": user.id, "session_id": own_session.id},
                db=AsyncMock(),
            )
        assert own_session.revoked is False
        assert other_session.revoked is True
        mock_mark.assert_called_once()
        assert mock_mark.call_args.args[0] == str(other_session.id)


@pytest.mark.anyio
class TestLogout:
    async def test_revokes_the_callers_session_everywhere(self):
        session = SimpleNamespace(id=str(uuid4()), revoked=False)
        with (
            patch("app.api.auth_routes.get_session_by_id", return_value=session),
            patch(
                "app.api.auth_routes.revoke_session",
                side_effect=lambda db, s: (setattr(s, "revoked", True), s)[1],
            ),
            patch("app.api.auth_routes.mark_session_revoked") as mock_mark,
        ):
            resp = await logout(current_user={"session_id": session.id}, db=MagicMock())
        assert resp == {"logged_out": True}
        assert session.revoked is True
        mock_mark.assert_called_once()

    async def test_already_revoked_session_is_a_noop(self):
        session = SimpleNamespace(id=str(uuid4()), revoked=True)
        with (
            patch("app.api.auth_routes.get_session_by_id", return_value=session),
            patch("app.api.auth_routes.revoke_session") as mock_revoke,
            patch("app.api.auth_routes.mark_session_revoked") as mock_mark,
        ):
            await logout(current_user={"session_id": session.id}, db=MagicMock())
        mock_revoke.assert_not_called()
        mock_mark.assert_not_called()


@pytest.mark.anyio
class TestListSessions:
    async def test_flags_the_current_session(self):
        current_id = str(uuid4())
        other_id = str(uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        sessions = [
            SimpleNamespace(id=current_id, issued_at=now, expires_at=now),
            SimpleNamespace(id=other_id, issued_at=now, expires_at=now),
        ]
        with patch("app.api.auth_routes.get_non_revoked_sessions_for_user", return_value=sessions):
            result = await list_sessions(
                current_user={"user_id": str(uuid4()), "session_id": current_id}, db=MagicMock()
            )
        by_id = {str(s.id): s for s in result}
        assert by_id[current_id].current is True
        assert by_id[other_id].current is False


@pytest.mark.anyio
class TestRefreshRejectsRevokedSession:
    async def test_revoked_session_cannot_refresh(self):
        session = SimpleNamespace(id=str(uuid4()), revoked=True)
        with (
            patch("app.api.auth_routes._cache_get", return_value=str(session.id)),
            patch("app.api.auth_routes._delete_key"),
            patch("app.api.auth_routes.get_session_by_id", return_value=session),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await refresh_token(refresh_token="some-refresh-token", db=MagicMock())
        assert exc_info.value.status_code == 401


@pytest.mark.anyio
class TestRevokeOneSession:
    async def test_owner_can_revoke_without_affecting_others(self):
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
            resp = await revoke_one_session(
                session_id=target.id, current_user={"user_id": user_id}, db=MagicMock()
            )
        assert resp == {"revoked": True}
        assert target.revoked is True
        mock_mark.assert_called_once()

    async def test_cannot_revoke_another_users_session(self):
        target = SimpleNamespace(id=str(uuid4()), user_id=str(uuid4()), revoked=False)
        with patch("app.api.auth_routes.get_session_by_id", return_value=target):
            with pytest.raises(HTTPException) as exc_info:
                await revoke_one_session(
                    session_id=target.id, current_user={"user_id": str(uuid4())}, db=MagicMock()
                )
        assert exc_info.value.status_code == 404
