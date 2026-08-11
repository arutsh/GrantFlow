"""Route-level tests for the gdpr-iso27001-priority-1 data-subject-rights
and consent-management endpoints in user_routes.py — consent get/update,
account deletion, data export, and email-change rectification.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.user_routes import (
    delete_my_account,
    export_my_data,
    get_my_consent,
    request_email_change,
    update_my_consent,
)
from app.schemas.consent_schema import ConsentUpdateRequest, EmailChangeRequest
from tests.factories.user import UserModelFactory


class TestGetMyConsent:
    def test_returns_current_state(self):
        user = UserModelFactory.build(consent_data_processing_at=None, consent_marketing_at=None)
        with patch("app.api.user_routes.get_user", return_value=user):
            resp = get_my_consent(current_user={"user_id": user.id}, db=MagicMock())
        assert resp.data_processing_granted is False
        assert resp.marketing_granted is False

    def test_missing_user_is_404(self):
        with patch("app.api.user_routes.get_user", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                get_my_consent(current_user={"user_id": uuid4()}, db=MagicMock())
        assert exc_info.value.status_code == 404


class TestUpdateMyConsent:
    def test_can_toggle_marketing_independently_of_data_processing(self):
        user = UserModelFactory.build(consent_data_processing_at=None, consent_marketing_at=None)
        with patch("app.api.user_routes.get_user", return_value=user):
            resp = update_my_consent(
                ConsentUpdateRequest(marketing=True),
                current_user={"user_id": user.id},
                db=MagicMock(),
            )
        assert resp.marketing_granted is True
        # Mandatory data-processing consent is untouched by this endpoint.
        assert resp.data_processing_granted is False


class TestExportMyData:
    def test_bundles_profile_consent_and_financial_records(self):
        user = UserModelFactory.build(consent_data_processing_at=None)
        with (
            patch("app.api.user_routes.get_user", return_value=user),
            patch(
                "app.api.user_routes.get_financial_record_refs",
                AsyncMock(return_value=[{"id": "b1", "name": "Budget 1", "type": "budget"}]),
            ),
        ):
            resp = asyncio.run(
                export_my_data(
                    current_user={"user_id": user.id, "token": "fake-token"}, db=MagicMock()
                )
            )
        assert resp["profile"]["email"] == user.email
        assert resp["consent"]["data_processing_granted"] is False
        assert resp["financial_records_created"] == [
            {"id": "b1", "name": "Budget 1", "type": "budget"}
        ]

    def test_budget_service_failure_does_not_fail_the_export(self):
        """get_financial_record_refs already swallows its own failures and
        returns [] — this just confirms the export endpoint doesn't add a
        second point of failure on top of that."""
        user = UserModelFactory.build()
        with (
            patch("app.api.user_routes.get_user", return_value=user),
            patch("app.api.user_routes.get_financial_record_refs", AsyncMock(return_value=[])),
        ):
            resp = asyncio.run(
                export_my_data(
                    current_user={"user_id": user.id, "token": "fake-token"}, db=MagicMock()
                )
            )
        assert resp["financial_records_created"] == []


class TestRequestEmailChange:
    def test_success_enqueues_verification_email(self):
        user = UserModelFactory.build(email="old@example.com", email_verified=True)
        with (
            patch("app.api.user_routes.get_user", return_value=user),
            patch(
                "app.api.user_routes.set_pending_email_verification_token",
                return_value="raw-token",
            ),
            patch("app.api.user_routes.enqueue_verification_email") as mock_enqueue,
            patch("app.api.user_routes.settings.EXPOSE_VERIFICATION_TOKEN_FOR_TESTS", False),
        ):
            resp = asyncio.run(
                request_email_change(
                    EmailChangeRequest(new_email="new@example.com"),
                    current_user={"user_id": user.id},
                    db=MagicMock(),
                )
            )
        assert resp == {"pending_email": "new@example.com", "debug_token": None}
        mock_enqueue.assert_called_once_with("new@example.com", "raw-token", user.first_name)

    def test_debug_token_exposed_when_flag_enabled(self):
        user = UserModelFactory.build(email="old@example.com", email_verified=True)
        with (
            patch("app.api.user_routes.get_user", return_value=user),
            patch(
                "app.api.user_routes.set_pending_email_verification_token",
                return_value="raw-token",
            ),
            patch("app.api.user_routes.enqueue_verification_email"),
            patch("app.api.user_routes.settings.EXPOSE_VERIFICATION_TOKEN_FOR_TESTS", True),
        ):
            resp = asyncio.run(
                request_email_change(
                    EmailChangeRequest(new_email="new@example.com"),
                    current_user={"user_id": user.id},
                    db=MagicMock(),
                )
            )
        assert resp["debug_token"] == "raw-token"

    def test_conflicting_email_returns_400(self):
        user = UserModelFactory.build(email="old@example.com", email_verified=True)
        with (
            patch("app.api.user_routes.get_user", return_value=user),
            patch(
                "app.api.user_routes.set_pending_email_verification_token",
                side_effect=ValueError("Email already registered"),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    request_email_change(
                        EmailChangeRequest(new_email="taken@example.com"),
                        current_user={"user_id": user.id},
                        db=MagicMock(),
                    )
                )
        assert exc_info.value.status_code == 400

    def test_unverified_email_rejected(self):
        """Would otherwise overwrite the pending signup verification token."""
        user = UserModelFactory.build(email="old@example.com", email_verified=False)
        with (
            patch("app.api.user_routes.get_user", return_value=user),
            patch(
                "app.api.user_routes.set_pending_email_verification_token"
            ) as mock_set_token,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    request_email_change(
                        EmailChangeRequest(new_email="new@example.com"),
                        current_user={"user_id": user.id},
                        db=MagicMock(),
                    )
                )
        assert exc_info.value.status_code == 400
        mock_set_token.assert_not_called()


class TestDeleteMyAccount:
    def test_self_service_deletion_revokes_sessions_and_scrubs_user(self):
        user = UserModelFactory.build()
        sessions = [SimpleNamespace(id=str(uuid4())), SimpleNamespace(id=str(uuid4()))]
        with (
            patch("app.api.user_routes.get_user", return_value=user),
            patch(
                "app.api.user_routes.revoke_all_sessions_for_user", return_value=sessions
            ) as mock_revoke_all,
            patch("app.api.user_routes.mark_session_revoked") as mock_mark,
            patch("app.api.user_routes.soft_delete_user") as mock_soft_delete,
        ):
            # current_user["user_id"] is a *string* here, matching what
            # get_validated_user actually returns (decoded straight from the
            # JWT payload) — user_id is the UUID FastAPI parses from the path.
            # A prior version of this comparison used `!=` directly on these
            # mismatched types, which Python never considers equal, so this
            # request always 403'd in production despite this test passing
            # with same-type UUIDs on both sides.
            resp = delete_my_account(
                user_id=user.id, current_user={"user_id": str(user.id)}, db=MagicMock()
            )
        assert resp == {"deleted": True}
        mock_revoke_all.assert_called_once()
        assert mock_mark.call_count == len(sessions)
        mock_soft_delete.assert_called_once()

    def test_cannot_delete_another_users_account(self):
        with pytest.raises(HTTPException) as exc_info:
            delete_my_account(
                user_id=uuid4(), current_user={"user_id": str(uuid4())}, db=MagicMock()
            )
        assert exc_info.value.status_code == 403
