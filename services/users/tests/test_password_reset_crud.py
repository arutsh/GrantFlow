"""Tests for the password-reset additions to user_crud.py (see test_gdpr_user_crud.py)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.crud.user_crud import (
    PASSWORD_RESET_TOKEN_TTL_HOURS,
    get_user_by_password_reset_token,
    reset_password,
    set_password_reset_token,
)
from tests.factories.user import UserModelFactory


@pytest.mark.anyio
class TestSetPasswordResetToken:
    async def test_issues_a_hashed_token_with_expiry(self):
        user = UserModelFactory.build(hashed_password="a-real-hash")
        raw_token = await set_password_reset_token(AsyncMock(), user)

        assert raw_token
        assert user.password_reset_token_hash is not None
        assert user.password_reset_token_hash != raw_token
        assert user.password_reset_expires_at is not None

    async def test_expiry_is_one_hour_out(self):
        user = UserModelFactory.build(hashed_password="a-real-hash")
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        await set_password_reset_token(AsyncMock(), user)
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        assert PASSWORD_RESET_TOKEN_TTL_HOURS == 1
        assert (
            before + timedelta(hours=1)
            <= user.password_reset_expires_at
            <= after + timedelta(hours=1)
        )

    async def test_no_password_set_is_a_no_op(self):
        user = UserModelFactory.build(hashed_password=None)
        raw_token = await set_password_reset_token(AsyncMock(), user)

        assert raw_token is None
        assert user.password_reset_token_hash is None
        assert user.password_reset_expires_at is None

    async def test_overwrites_any_prior_token(self):
        user = UserModelFactory.build(
            hashed_password="a-real-hash",
            password_reset_token_hash="stale-hash",
            password_reset_expires_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        await set_password_reset_token(AsyncMock(), user)

        assert user.password_reset_token_hash != "stale-hash"


@pytest.mark.anyio
class TestGetUserByPasswordResetToken:
    def _db_returning(self, user):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = user
        return db

    async def test_valid_unexpired_token_resolves(self):
        user = UserModelFactory.build(email="user@example.com")
        user.password_reset_token_hash = "hashed-token"
        user.password_reset_expires_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + timedelta(hours=1)

        with patch("app.crud.user_crud.get_user_by_email", return_value=user), patch(
            "app.crud.user_crud.verify_token_hash", return_value=True
        ):
            resolved = await get_user_by_password_reset_token(AsyncMock(), user.email, "raw-token")

        assert resolved is user

    async def test_expired_token_is_rejected(self):
        user = UserModelFactory.build(email="user@example.com")
        user.password_reset_token_hash = "hashed-token"
        user.password_reset_expires_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - timedelta(seconds=1)

        with patch("app.crud.user_crud.get_user_by_email", return_value=user):
            resolved = await get_user_by_password_reset_token(AsyncMock(), user.email, "raw-token")

        assert resolved is None

    async def test_mismatched_token_is_rejected(self):
        user = UserModelFactory.build(email="user@example.com")
        user.password_reset_token_hash = "hashed-token"
        user.password_reset_expires_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) + timedelta(hours=1)

        with patch("app.crud.user_crud.get_user_by_email", return_value=user), patch(
            "app.crud.user_crud.verify_token_hash", return_value=False
        ):
            resolved = await get_user_by_password_reset_token(
                AsyncMock(), user.email, "wrong-token"
            )

        assert resolved is None

    async def test_no_pending_token_is_rejected(self):
        user = UserModelFactory.build(
            email="user@example.com",
            password_reset_token_hash=None,
            password_reset_expires_at=None,
        )
        with patch("app.crud.user_crud.get_user_by_email", return_value=user):
            resolved = await get_user_by_password_reset_token(AsyncMock(), user.email, "raw-token")

        assert resolved is None


@pytest.mark.anyio
class TestResetPassword:
    async def test_sets_new_hash_and_clears_the_token(self):
        user = UserModelFactory.build(
            hashed_password="old-hash",
            password_reset_token_hash="hashed-token",
            password_reset_expires_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        await reset_password(AsyncMock(), user, "N3w-Str0ng-Pass!")

        assert user.hashed_password != "old-hash"
        assert user.password_reset_token_hash is None
        assert user.password_reset_expires_at is None


@pytest.mark.anyio
class TestPasswordResetTokenIsolation:
    """Dedicated column pair (design.md decision 1) — a reset request must
    not disturb a pending email-verification token, and vice versa."""

    async def test_issuing_a_reset_token_leaves_a_pending_verification_token_untouched(self):
        user = UserModelFactory.build(
            hashed_password="a-real-hash",
            email_verification_token_hash="verify-hash",
            email_verification_expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(hours=1),
        )
        await set_password_reset_token(AsyncMock(), user)

        assert user.email_verification_token_hash == "verify-hash"

    async def test_consuming_a_reset_token_leaves_a_pending_verification_token_untouched(self):
        user = UserModelFactory.build(
            hashed_password="old-hash",
            password_reset_token_hash="reset-hash",
            password_reset_expires_at=datetime.now(timezone.utc).replace(tzinfo=None),
            email_verification_token_hash="verify-hash",
            email_verification_expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(hours=1),
        )
        await reset_password(AsyncMock(), user, "N3w-Str0ng-Pass!")

        assert user.email_verification_token_hash == "verify-hash"
