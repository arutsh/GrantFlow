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
    login,
    refresh_token,
    register_endpoint,
    resend_verification,
    verify_email,
)
from app.schemas.auth_schema import (
    LoginRequest,
    RegisterRequest,
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
        user = UserModelFactory.build(customer_id=str(uuid4()))
        user.customer = CustomerFactory.build(is_donor=True)
        claims = _claims(self._login(user))
        assert claims["is_donor"] is True
        assert claims["is_ngo"] is False

    def test_ngo_customer(self):
        user = UserModelFactory.build(customer_id=str(uuid4()))
        user.customer = CustomerFactory.build(is_ngo=True)
        claims = _claims(self._login(user))
        assert claims["is_ngo"] is True
        assert claims["is_donor"] is False

    def test_customer_both_ngo_and_donor(self):
        user = UserModelFactory.build(customer_id=str(uuid4()))
        user.customer = CustomerFactory.build(is_ngo=True, is_donor=True)
        claims = _claims(self._login(user))
        assert claims["is_ngo"] is True
        assert claims["is_donor"] is True

    def test_user_with_no_customer_id(self):
        user = UserModelFactory.build(customer_id=None)
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


class TestRegisterRoleClaims:
    """register_endpoint has no already-loaded customer to reuse (a
    just-inserted UserModel isn't eager-loaded), so this is the one call
    site that still queries get_customer via _customer_role_claims."""

    def _register(self, created_user, db, get_customer_mock):
        with (
            patch("app.api.auth_routes.create_user", AsyncMock(return_value=created_user)),
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
            patch("app.api.auth_routes.get_customer", get_customer_mock) as mock_get_customer,
            patch("app.api.auth_routes.set_email_verification_token", return_value="raw-token"),
            patch("app.api.auth_routes.enqueue_verification_email"),
        ):
            resp = asyncio.run(
                register_endpoint(
                    RegisterRequest(
                        email="new@example.com",
                        password="pw",
                        customer_id=created_user.customer_id,
                    ),
                    db=db,
                )
            )
        return resp, mock_get_customer

    def test_donor_customer(self):
        customer_id = str(uuid4())
        created_user = UserModelFactory.build(customer_id=customer_id)
        db = object()
        resp, mock_get_customer = self._register(
            created_user, db, MagicMock(return_value=CustomerFactory.build(is_donor=True))
        )
        claims = _claims(resp)
        assert claims["is_donor"] is True
        assert claims["is_ngo"] is False
        mock_get_customer.assert_called_once_with(db, customer_id)

    def test_user_with_no_customer_id(self):
        created_user = UserModelFactory.build(customer_id=None)
        resp, mock_get_customer = self._register(created_user, object(), MagicMock())
        claims = _claims(resp)
        assert claims["is_ngo"] is False
        assert claims["is_donor"] is False
        mock_get_customer.assert_not_called()

    def test_customer_not_found(self):
        """customer_id is set but get_customer finds no row (deleted
        customer, orphaned FK) — degrades to false/false, same as no
        customer_id at all."""
        customer_id = str(uuid4())
        created_user = UserModelFactory.build(customer_id=customer_id)
        resp, mock_get_customer = self._register(
            created_user, object(), MagicMock(return_value=None)
        )
        claims = _claims(resp)
        assert claims["is_ngo"] is False
        assert claims["is_donor"] is False
        mock_get_customer.assert_called_once()

    def test_customer_lookup_failure_still_issues_token(self):
        """A transient get_customer failure must not turn an
        already-committed user+session into an unhandled 500 — see
        _customer_role_claims's docstring."""
        customer_id = str(uuid4())
        created_user = UserModelFactory.build(customer_id=customer_id)
        resp, _ = self._register(
            created_user, object(), MagicMock(side_effect=RuntimeError("db blip"))
        )
        claims = _claims(resp)
        assert claims["is_ngo"] is False
        assert claims["is_donor"] is False


class TestEmailVerifiedClaim:
    """email_verified is merged into the JWT at register/login/refresh,
    alongside is_ngo/is_donor — reflects the user row's current value, not
    a hardcoded default."""

    def test_register_reflects_false(self):
        created_user = UserModelFactory.build(customer_id=None, email_verified=False)
        with (
            patch("app.api.auth_routes.create_user", AsyncMock(return_value=created_user)),
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
            patch("app.api.auth_routes.get_customer", MagicMock()),
            patch("app.api.auth_routes.set_email_verification_token", return_value="raw-token"),
            patch("app.api.auth_routes.enqueue_verification_email"),
        ):
            resp = asyncio.run(
                register_endpoint(
                    RegisterRequest(email="new@example.com", password="pw"), db=object()
                )
            )
        assert _claims(resp)["email_verified"] is False

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
        )
        with (
            patch("app.api.auth_routes._cache_get", return_value=str(session.id)),
            patch("app.api.auth_routes._delete_key"),
            patch("app.api.auth_routes.get_session_by_id", return_value=session),
            patch("app.api.auth_routes.verify_token_hash", return_value=True),
        ):
            resp = refresh_token(refresh_token="incoming-refresh-token", db=MagicMock())
        assert _claims(resp)["email_verified"] is True


class TestRegisterEnqueuesVerificationEmail:
    def test_stores_token_and_enqueues_send(self):
        created_user = UserModelFactory.build(customer_id=None)
        with (
            patch("app.api.auth_routes.create_user", AsyncMock(return_value=created_user)),
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
            patch("app.api.auth_routes.get_customer", MagicMock()),
            patch(
                "app.api.auth_routes.set_email_verification_token", return_value="raw-token"
            ) as mock_set_token,
            patch("app.api.auth_routes.enqueue_verification_email") as mock_enqueue,
        ):
            asyncio.run(
                register_endpoint(
                    RegisterRequest(email="new@example.com", password="pw"), db=object()
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
            patch(
                "app.api.auth_routes.create_session",
                return_value=SimpleNamespace(id=str(uuid4())),
            ),
            patch("app.api.auth_routes.get_customer", MagicMock()),
            patch("app.api.auth_routes.set_email_verification_token", return_value="raw-token"),
            patch(
                "app.api.auth_routes.enqueue_verification_email",
                side_effect=RuntimeError("broker down"),
            ),
        ):
            resp = asyncio.run(
                register_endpoint(
                    RegisterRequest(email="new@example.com", password="pw"), db=object()
                )
            )
        assert resp.access_token


class TestVerifyEmail:
    def test_valid_unexpired_token_verifies_account(self):
        user = UserModelFactory.build(
            email_verification_expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(hours=1)
        )
        db = object()
        with (
            patch(
                "app.api.auth_routes.get_user_by_verification_token", return_value=user
            ) as mock_lookup,
            patch("app.api.auth_routes.mark_email_verified") as mock_mark,
        ):
            resp = verify_email(VerifyEmailRequest(email=user.email, token="raw-token"), db=db)
        assert resp.email_verified is True
        mock_lookup.assert_called_once_with(db, user.email, "raw-token")
        mock_mark.assert_called_once()
        assert mock_mark.call_args[0][1] is user

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
    def test_unverified_account_gets_new_token_and_send(self):
        user = UserModelFactory.build(email_verified=False)
        with (
            patch("app.api.auth_routes.get_user", return_value=user),
            patch(
                "app.api.auth_routes.set_email_verification_token", return_value="raw-token"
            ) as mock_set_token,
            patch("app.api.auth_routes.enqueue_verification_email") as mock_enqueue,
        ):
            resp = resend_verification(current_user={"user_id": user.id}, db=object())
        assert resp.sent is True
        mock_set_token.assert_called_once()
        mock_enqueue.assert_called_once_with(user.email, "raw-token", user.first_name)

    def test_already_verified_account_is_a_noop(self):
        user = UserModelFactory.build(email_verified=True)
        with (
            patch("app.api.auth_routes.get_user", return_value=user),
            patch("app.api.auth_routes.set_email_verification_token") as mock_set_token,
            patch("app.api.auth_routes.enqueue_verification_email") as mock_enqueue,
        ):
            resp = resend_verification(current_user={"user_id": user.id}, db=object())
        assert resp.sent is False
        mock_set_token.assert_not_called()
        mock_enqueue.assert_not_called()
