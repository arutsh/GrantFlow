"""
Tests for is_ngo/is_donor role-flag claims on issued JWTs.

`/register`, `/auth/login`, and `/auth/refresh` each build the access-token
claims dict independently, so each is exercised separately. Mocks the crud
layer (matching this codebase's existing test convention — see
services/budget/tests/test_budget_line_services.py — no real DB session).
"""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.auth_routes import (
    forgot_password,
    login,
    refresh_token,
    register_endpoint,
    resend_verification,
    verify_email,
)
from app.schemas.auth_schema import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    VerifyEmailRequest,
)
from app.utils.security import decode_access_token
from tests.factories.user import CustomerFactory, UserModelFactory


def _claims(token_response):
    return decode_access_token(token_response.access_token)


class TestLoginRoleClaims:
    """login reads role flags off the already-loaded user.customer
    relationship (UserModel.customer is lazy="joined") rather than querying
    get_customer again — set .customer directly, don't mock get_customer."""

    def _login(self, user):
        with (
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch("app.api.auth_routes.verify_password", return_value=True),
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
        ):
            resp = login(LoginRequest(email=user.email, password="pw"), db=object())
        return resp

    def test_donor_customer(self):
        user = UserModelFactory.build(customer_id=str(uuid4()), email_verified=True)
        user.customer = CustomerFactory.build(is_donor=True)
        claims = _claims(self._login(user))
        assert claims["is_donor"] is True
        assert claims["is_ngo"] is False

    def test_ngo_customer(self):
        user = UserModelFactory.build(customer_id=str(uuid4()), email_verified=True)
        user.customer = CustomerFactory.build(is_ngo=True)
        claims = _claims(self._login(user))
        assert claims["is_ngo"] is True
        assert claims["is_donor"] is False

    def test_customer_both_ngo_and_donor(self):
        user = UserModelFactory.build(customer_id=str(uuid4()), email_verified=True)
        user.customer = CustomerFactory.build(is_ngo=True, is_donor=True)
        claims = _claims(self._login(user))
        assert claims["is_ngo"] is True
        assert claims["is_donor"] is True

    def test_user_with_no_customer_id(self):
        user = UserModelFactory.build(customer_id=None, email_verified=True)
        user.customer = None
        claims = _claims(self._login(user))
        assert claims["is_ngo"] is False
        assert claims["is_donor"] is False


class TestRefreshRoleClaims:
    """refresh_token reads role flags off the already-loaded s.user.customer
    relationship (UserModel.customer is lazy="joined") rather than querying
    get_customer again — set .customer directly, don't mock get_customer."""

    def _refresh(self, user):
        session = SimpleNamespace(
            id=str(uuid4()),
            user_id=user.id,
            user=user,
            refresh_token_hash="irrelevant",
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1),
            revoked=False,
        )
        with (
            patch("app.api.auth_routes._cache_get", return_value=str(session.id)),
            patch("app.api.auth_routes._delete_key"),
            patch("app.api.auth_routes.get_session_by_id", return_value=session),
            patch("app.api.auth_routes.verify_token_hash", return_value=True),
        ):
            resp = refresh_token(refresh_token="incoming-refresh-token", db=MagicMock())
        return resp

    def test_donor_customer(self):
        user = UserModelFactory.build(customer_id=str(uuid4()))
        user.customer = CustomerFactory.build(is_donor=True)
        claims = _claims(self._refresh(user))
        assert claims["is_donor"] is True
        assert claims["is_ngo"] is False

    def test_customer_both_ngo_and_donor(self):
        user = UserModelFactory.build(customer_id=str(uuid4()))
        user.customer = CustomerFactory.build(is_ngo=True, is_donor=True)
        claims = _claims(self._refresh(user))
        assert claims["is_ngo"] is True
        assert claims["is_donor"] is True

    def test_user_with_no_customer_id(self):
        user = UserModelFactory.build(customer_id=None)
        user.customer = None
        claims = _claims(self._refresh(user))
        assert claims["is_ngo"] is False
        assert claims["is_donor"] is False


class TestVerifyEmailRoleClaims:
    """verify-email now issues the account's first session, not register."""

    def _verify(self, user, db, get_customer_mock):
        user.email_verification_expires_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + timedelta(hours=1)
        with (
            patch("app.api.auth_routes.get_user_by_verification_token", return_value=user),
            patch("app.api.auth_routes.mark_email_verified", return_value=user),
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
            patch("app.api.auth_routes.get_customer", get_customer_mock) as mock_get_customer,
        ):
            resp = verify_email(
                VerifyEmailRequest(email=user.email, token="raw-token"), db=db
            )
        return resp, mock_get_customer

    def test_donor_customer(self):
        customer_id = str(uuid4())
        user = UserModelFactory.build(customer_id=customer_id)
        db = object()
        resp, mock_get_customer = self._verify(
            user, db, MagicMock(return_value=CustomerFactory.build(is_donor=True))
        )
        claims = _claims(resp)
        assert claims["is_donor"] is True
        assert claims["is_ngo"] is False
        mock_get_customer.assert_called_once_with(db, customer_id)

    def test_user_with_no_customer_id(self):
        user = UserModelFactory.build(customer_id=None)
        resp, mock_get_customer = self._verify(user, object(), MagicMock())
        claims = _claims(resp)
        assert claims["is_ngo"] is False
        assert claims["is_donor"] is False
        mock_get_customer.assert_not_called()

    def test_customer_not_found(self):
        """customer_id is set but get_customer finds no row (deleted
        customer, orphaned FK) — degrades to false/false, same as no
        customer_id at all."""
        customer_id = str(uuid4())
        user = UserModelFactory.build(customer_id=customer_id)
        resp, mock_get_customer = self._verify(
            user, object(), MagicMock(return_value=None)
        )
        claims = _claims(resp)
        assert claims["is_ngo"] is False
        assert claims["is_donor"] is False
        mock_get_customer.assert_called_once()

    def test_customer_lookup_failure_still_issues_token(self):
        """A transient get_customer failure must not turn an
        already-committed verification+session into an unhandled 500 — see
        _customer_role_claims's docstring."""
        customer_id = str(uuid4())
        user = UserModelFactory.build(customer_id=customer_id)
        resp, _ = self._verify(
            user, object(), MagicMock(side_effect=RuntimeError("db blip"))
        )
        claims = _claims(resp)
        assert claims["is_ngo"] is False
        assert claims["is_donor"] is False


class TestEmailVerifiedClaim:
    """email_verified is merged into the JWT at login/refresh/verify-email."""

    def test_verify_email_reflects_true(self):
        user = UserModelFactory.build(
            customer_id=None,
            email_verified=False,
            email_verification_expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(hours=1),
        )
        with (
            patch("app.api.auth_routes.get_user_by_verification_token", return_value=user),
            patch("app.api.auth_routes.mark_email_verified") as mock_mark,
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
            patch("app.api.auth_routes.get_customer", MagicMock()),
        ):
            user.email_verified = True
            mock_mark.return_value = user
            resp = verify_email(
                VerifyEmailRequest(email=user.email, token="raw-token"), db=object()
            )
        assert _claims(resp)["email_verified"] is True

    def test_login_reflects_true(self):
        user = UserModelFactory.build(customer_id=None, email_verified=True)
        user.customer = None
        with (
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch("app.api.auth_routes.verify_password", return_value=True),
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
        ):
            resp = login(LoginRequest(email=user.email, password="pw"), db=object())
        assert _claims(resp)["email_verified"] is True

    def test_refresh_reflects_true(self):
        user = UserModelFactory.build(customer_id=None, email_verified=True)
        user.customer = None
        session = SimpleNamespace(
            id=str(uuid4()),
            user_id=user.id,
            user=user,
            refresh_token_hash="irrelevant",
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1),
            revoked=False,
        )
        with (
            patch("app.api.auth_routes._cache_get", return_value=str(session.id)),
            patch("app.api.auth_routes._delete_key"),
            patch("app.api.auth_routes.get_session_by_id", return_value=session),
            patch("app.api.auth_routes.verify_token_hash", return_value=True),
        ):
            resp = refresh_token(refresh_token="incoming-refresh-token", db=MagicMock())
        assert _claims(resp)["email_verified"] is True


class TestRegistrationIssuesNoSession:
    def test_response_carries_no_token_or_session_fields(self):
        created_user = UserModelFactory.build(customer_id=None)
        with (
            patch("app.api.auth_routes.create_user", AsyncMock(return_value=created_user)),
            patch("app.api.auth_routes.set_email_verification_token", return_value="raw-token"),
            patch("app.api.auth_routes.enqueue_verification_email"),
        ):
            resp = asyncio.run(
                register_endpoint(
                    RegisterRequest(
                        email="new@example.com",
                        password="Correct-Horse-1",
                        consent_data_processing=True,
                    ),
                    db=object(),
                )
            )
        assert not hasattr(resp, "access_token")
        assert not hasattr(resp, "refresh_token")
        assert resp.email == created_user.email


class TestRegisterEnqueuesVerificationEmail:
    def test_stores_token_and_enqueues_send(self):
        created_user = UserModelFactory.build(customer_id=None)
        with (
            patch("app.api.auth_routes.create_user", AsyncMock(return_value=created_user)),
            patch(
                "app.api.auth_routes.set_email_verification_token", return_value="raw-token"
            ) as mock_set_token,
            patch("app.api.auth_routes.enqueue_verification_email") as mock_enqueue,
        ):
            asyncio.run(
                register_endpoint(
                    RegisterRequest(
                        email="new@example.com",
                        password="Correct-Horse-1",
                        consent_data_processing=True,
                    ),
                    db=object(),
                )
            )
        assert mock_set_token.call_args[0][1] is created_user
        mock_enqueue.assert_called_once_with(
            created_user.email, "raw-token", created_user.first_name
        )

    def test_broker_failure_does_not_fail_registration(self):
        """Registration is already durably committed by the time the
        enqueue happens — a broker blip must not turn that into a 500."""
        created_user = UserModelFactory.build(customer_id=None)
        with (
            patch("app.api.auth_routes.create_user", AsyncMock(return_value=created_user)),
            patch("app.api.auth_routes.set_email_verification_token", return_value="raw-token"),
            patch(
                "app.api.auth_routes.enqueue_verification_email",
                side_effect=RuntimeError("broker down"),
            ),
        ):
            resp = asyncio.run(
                register_endpoint(
                    RegisterRequest(
                        email="new@example.com",
                        password="Correct-Horse-1",
                        consent_data_processing=True,
                    ),
                    db=object(),
                )
            )
        assert resp.email == created_user.email


class TestVerifyEmail:
    def test_valid_unexpired_token_verifies_account_and_issues_a_session(self):
        user = UserModelFactory.build(
            customer_id=None,
            email_verification_expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(hours=1),
        )
        db = object()
        with (
            patch(
                "app.api.auth_routes.get_user_by_verification_token", return_value=user
            ) as mock_lookup,
            patch("app.api.auth_routes.mark_email_verified", return_value=user) as mock_mark,
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ) as mock_create_session,
            patch("app.api.auth_routes.get_customer", MagicMock()),
        ):
            resp = verify_email(VerifyEmailRequest(email=user.email, token="raw-token"), db=db)
        assert resp.email_verified is True
        assert resp.access_token
        assert resp.refresh_token
        mock_lookup.assert_called_once_with(db, user.email, "raw-token")
        mock_mark.assert_called_once()
        assert mock_mark.call_args[0][1] is user
        mock_create_session.assert_called_once_with(
            session=db, user_id=user.id, refresh_token_hash=resp.refresh_token
        )

    def test_expired_token_is_rejected(self):
        user = UserModelFactory.build(
            email_verification_expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            - timedelta(hours=1)
        )
        with (
            patch("app.api.auth_routes.get_user_by_verification_token", return_value=user),
            patch("app.api.auth_routes.mark_email_verified") as mock_mark,
        ):
            with pytest.raises(HTTPException) as exc_info:
                verify_email(VerifyEmailRequest(email=user.email, token="raw-token"), db=object())
        assert exc_info.value.status_code == 400
        mock_mark.assert_not_called()

    def test_invalid_or_already_used_token_is_rejected(self):
        """No matching pending token — covers both a bogus token and one
        that already succeeded once (its hash was cleared on success)."""
        with patch("app.api.auth_routes.get_user_by_verification_token", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                verify_email(
                    VerifyEmailRequest(email="test@example.com", token="raw-token"),
                    db=object(),
                )
        assert exc_info.value.status_code == 400


class TestResendVerification:
    """Anonymous and enumeration-safe: every branch returns `sent=True`."""

    def test_unverified_account_gets_new_token_and_send(self):
        user = UserModelFactory.build(email_verified=False)
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.record_failed_attempt"),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch(
                "app.api.auth_routes.set_email_verification_token", return_value="raw-token"
            ) as mock_set_token,
            patch("app.api.auth_routes.enqueue_verification_email") as mock_enqueue,
        ):
            resp = resend_verification(ResendVerificationRequest(email=user.email), db=object())
        assert resp.sent is True
        mock_set_token.assert_called_once()
        mock_enqueue.assert_called_once_with(user.email, "raw-token", user.first_name)

    def test_already_verified_account_returns_the_same_generic_response(self):
        user = UserModelFactory.build(email_verified=True)
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.record_failed_attempt"),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch("app.api.auth_routes.set_email_verification_token") as mock_set_token,
            patch("app.api.auth_routes.enqueue_verification_email") as mock_enqueue,
        ):
            resp = resend_verification(ResendVerificationRequest(email=user.email), db=object())
        assert resp.sent is True
        mock_set_token.assert_not_called()
        mock_enqueue.assert_not_called()

    def test_nonexistent_email_returns_the_same_generic_response(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.record_failed_attempt"),
            patch("app.api.auth_routes.get_user_by_email", return_value=None),
            patch("app.api.auth_routes.set_email_verification_token") as mock_set_token,
            patch("app.api.auth_routes.enqueue_verification_email") as mock_enqueue,
        ):
            resp = resend_verification(
                ResendVerificationRequest(email="nobody@example.com"), db=object()
            )
        assert resp.sent is True
        assert resp.debug_token is None
        mock_set_token.assert_not_called()
        mock_enqueue.assert_not_called()

    def test_repeated_requests_past_the_threshold_are_rate_limited(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=True),
            patch("app.api.auth_routes.get_user_by_email") as mock_get_user,
        ):
            with pytest.raises(HTTPException) as exc_info:
                resend_verification(
                    ResendVerificationRequest(email="a@b.com"), db=object()
                )
        assert exc_info.value.status_code == 429
        mock_get_user.assert_not_called()

    def test_debug_token_included_when_flag_enabled(self):
        """EXPOSE_VERIFICATION_TOKEN_FOR_TESTS lets e2e drive the real
        verify-email flow without a real inbox — only ever true in
        services/users/.env.users.local, never in prod."""
        user = UserModelFactory.build(email_verified=False)
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.record_failed_attempt"),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch(
                "app.api.auth_routes.set_email_verification_token", return_value="raw-token"
            ),
            patch("app.api.auth_routes.enqueue_verification_email"),
            patch("app.api.auth_routes.settings.EXPOSE_VERIFICATION_TOKEN_FOR_TESTS", True),
        ):
            resp = resend_verification(ResendVerificationRequest(email=user.email), db=object())
        assert resp.debug_token == "raw-token"

    def test_debug_token_absent_when_flag_disabled(self):
        user = UserModelFactory.build(email_verified=False)
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.record_failed_attempt"),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch(
                "app.api.auth_routes.set_email_verification_token", return_value="raw-token"
            ),
            patch("app.api.auth_routes.enqueue_verification_email"),
            patch("app.api.auth_routes.settings.EXPOSE_VERIFICATION_TOKEN_FOR_TESTS", False),
        ):
            resp = resend_verification(ResendVerificationRequest(email=user.email), db=object())
        assert resp.debug_token is None


class TestForgotPassword:
    """Anonymous and enumeration-safe: every branch returns `sent=True`."""

    def test_account_with_password_gets_a_new_token_and_send(self):
        user = UserModelFactory.build(hashed_password="a-real-hash")
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.record_failed_attempt"),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch(
                "app.api.auth_routes.set_password_reset_token", return_value="raw-token"
            ) as mock_set_token,
            patch("app.api.auth_routes.enqueue_password_reset_email") as mock_enqueue,
        ):
            resp = forgot_password(ForgotPasswordRequest(email=user.email), db=object())
        assert resp.sent is True
        mock_set_token.assert_called_once()
        mock_enqueue.assert_called_once_with(user.email, "raw-token", user.first_name)

    def test_account_with_no_password_set_returns_the_same_generic_response(self):
        user = UserModelFactory.build(hashed_password=None)
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.record_failed_attempt"),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch("app.api.auth_routes.set_password_reset_token", return_value=None),
            patch("app.api.auth_routes.enqueue_password_reset_email") as mock_enqueue,
        ):
            resp = forgot_password(ForgotPasswordRequest(email=user.email), db=object())
        assert resp.sent is True
        mock_enqueue.assert_not_called()

    def test_nonexistent_email_returns_the_same_generic_response(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.record_failed_attempt"),
            patch("app.api.auth_routes.get_user_by_email", return_value=None),
            patch("app.api.auth_routes.set_password_reset_token") as mock_set_token,
            patch("app.api.auth_routes.enqueue_password_reset_email") as mock_enqueue,
        ):
            resp = forgot_password(
                ForgotPasswordRequest(email="nobody@example.com"), db=object()
            )
        assert resp.sent is True
        assert resp.debug_token is None
        mock_set_token.assert_not_called()
        mock_enqueue.assert_not_called()

    def test_repeated_requests_past_the_threshold_are_rate_limited(self):
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=True),
            patch("app.api.auth_routes.get_user_by_email") as mock_get_user,
        ):
            with pytest.raises(HTTPException) as exc_info:
                forgot_password(ForgotPasswordRequest(email="a@b.com"), db=object())
        assert exc_info.value.status_code == 429
        mock_get_user.assert_not_called()

    def test_resend_verification_lockout_does_not_block_forgot_password(self):
        """The two buckets must not share a key space (design.md risk #2)."""
        with (
            patch(
                "app.api.auth_routes.is_locked_out",
                side_effect=lambda email, ip, bucket: bucket == "resend_verification",
            ),
            patch("app.api.auth_routes.record_failed_attempt"),
            patch("app.api.auth_routes.get_user_by_email", return_value=None),
        ):
            resp = forgot_password(ForgotPasswordRequest(email="a@b.com"), db=object())
        assert resp.sent is True

    def test_debug_token_included_when_flag_enabled(self):
        user = UserModelFactory.build(hashed_password="a-real-hash")
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.record_failed_attempt"),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch(
                "app.api.auth_routes.set_password_reset_token", return_value="raw-token"
            ),
            patch("app.api.auth_routes.enqueue_password_reset_email"),
            patch("app.api.auth_routes.settings.EXPOSE_VERIFICATION_TOKEN_FOR_TESTS", True),
        ):
            resp = forgot_password(ForgotPasswordRequest(email=user.email), db=object())
        assert resp.debug_token == "raw-token"

    def test_debug_token_absent_when_flag_disabled(self):
        user = UserModelFactory.build(hashed_password="a-real-hash")
        with (
            patch("app.api.auth_routes.is_locked_out", return_value=False),
            patch("app.api.auth_routes.record_failed_attempt"),
            patch("app.api.auth_routes.get_user_by_email", return_value=user),
            patch(
                "app.api.auth_routes.set_password_reset_token", return_value="raw-token"
            ),
            patch("app.api.auth_routes.enqueue_password_reset_email"),
            patch("app.api.auth_routes.settings.EXPOSE_VERIFICATION_TOKEN_FOR_TESTS", False),
        ):
            resp = forgot_password(ForgotPasswordRequest(email=user.email), db=object())
        assert resp.debug_token is None
