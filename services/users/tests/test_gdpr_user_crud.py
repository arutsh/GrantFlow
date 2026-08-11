"""Tests for the gdpr-iso27001-priority-1 additions to user_crud.py:
consent state, soft-delete/erasure, and email-change rectification.

Matches this module's existing convention (see test_auth_routes.py) of
building an unpersisted UserModel via the factory and passing a MagicMock
session — these functions only mutate attributes and call commit/refresh,
so a real DB isn't needed to verify their behavior.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.crud.user_crud import (
    get_consent_state,
    mark_email_verified,
    set_marketing_consent,
    set_pending_email_verification_token,
    soft_delete_user,
)
from tests.factories.user import UserModelFactory


class TestConsentState:
    def test_no_consent_reflects_ungranted(self):
        user = UserModelFactory.build(consent_data_processing_at=None, consent_marketing_at=None)
        state = get_consent_state(user)
        assert state["data_processing_granted"] is False
        assert state["marketing_granted"] is False

    def test_granted_consent_reflects_timestamp(self):
        now = datetime.now(timezone.utc)
        user = UserModelFactory.build(consent_data_processing_at=now, consent_marketing_at=None)
        state = get_consent_state(user)
        assert state["data_processing_granted"] is True
        assert state["data_processing_at"] == now
        assert state["marketing_granted"] is False


class TestSetMarketingConsent:
    def test_enabling_sets_a_timestamp(self):
        user = UserModelFactory.build(consent_marketing_at=None)
        set_marketing_consent(MagicMock(), user, True)
        assert user.consent_marketing_at is not None

    def test_disabling_clears_the_timestamp(self):
        user = UserModelFactory.build(consent_marketing_at=datetime.now(timezone.utc))
        set_marketing_consent(MagicMock(), user, False)
        assert user.consent_marketing_at is None


class TestSoftDeleteUser:
    def test_scrubs_pii_and_blocks_future_login(self):
        user = UserModelFactory.build(
            first_name="Real",
            last_name="Name",
            email="real@example.com",
            hashed_password="a-real-hash",
        )
        soft_delete_user(MagicMock(), user)

        assert user.first_name == "Deleted"
        assert user.last_name == "User"
        assert user.email != "real@example.com"
        # No hash to verify against — login() rejects on `not user.hashed_password`.
        assert user.hashed_password is None
        assert user.deleted_at is not None

    def test_tombstone_email_is_unique_per_user(self):
        user_a = UserModelFactory.build()
        user_b = UserModelFactory.build()
        soft_delete_user(MagicMock(), user_a)
        soft_delete_user(MagicMock(), user_b)
        assert user_a.email != user_b.email

    def test_clears_any_pending_email_change(self):
        user = UserModelFactory.build(pending_email="new@example.com")
        soft_delete_user(MagicMock(), user)
        assert user.pending_email is None


class TestEmailChangeRectification:
    def _no_conflict_db(self) -> MagicMock:
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db

    def test_new_email_stored_as_pending_old_stays_active(self):
        user = UserModelFactory.build(email="old@example.com", pending_email=None)
        raw_token = set_pending_email_verification_token(
            self._no_conflict_db(), user, "new@example.com"
        )
        assert user.pending_email == "new@example.com"
        assert user.email == "old@example.com"
        assert raw_token

    def test_conflicting_email_rejected(self):
        import pytest

        user = UserModelFactory.build(email="old@example.com")
        other_user = UserModelFactory.build(email="taken@example.com")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = other_user

        with pytest.raises(ValueError, match="already registered"):
            set_pending_email_verification_token(db, user, "taken@example.com")

    def test_confirming_promotes_pending_email(self):
        user = UserModelFactory.build(email="old@example.com")
        set_pending_email_verification_token(self._no_conflict_db(), user, "new@example.com")

        mark_email_verified(MagicMock(), user)

        assert user.email == "new@example.com"
        assert user.pending_email is None
        assert user.email_verification_token_hash is None


class TestEmailChangeRectificationPendingCollision:
    """Uses a real in-memory sqlite session, unlike this module's other
    tests: the behavior under test is the crud query's WHERE clause
    matching another user's *pending* email, not just their active one —
    a MagicMock can't distinguish which column the mocked query "matched
    on", so it can't actually exercise the or_() this test is for."""

    def _make_session(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models.base import Base
        from app.models.customer import CustomerModel
        from app.models.user import UserModel

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine, tables=[UserModel.__table__, CustomerModel.__table__])
        return sessionmaker(bind=engine)()

    def test_rejected_when_another_user_already_has_it_pending(self):
        import pytest
        from app.models.user import UserModel
        from shared.schemas.user_schema import UserRole, UserStatus

        db = self._make_session()
        other_user = UserModel(
            email="other@example.com",
            pending_email="new@example.com",
            role=UserRole.user,
            status=UserStatus.active,
            hashed_password="hash",
        )
        me = UserModel(
            email="me@example.com",
            role=UserRole.user,
            status=UserStatus.active,
            hashed_password="hash",
        )
        # Added and committed separately, not via add_all: UserModel.id's
        # default returns a str instead of a uuid.UUID (pre-existing bug,
        # see BudgetModel's identical issue in GitHub #140), which breaks
        # SQLAlchemy's batched-insert sentinel matching on a 2+ row flush.
        db.add(other_user)
        db.commit()
        db.add(me)
        db.commit()

        # other_user's *active* email doesn't collide — only their pending
        # one does. Without checking pending_email too, this would succeed
        # here and only blow up later, as an unhandled 500, when both users
        # try to confirm and hit the `email` unique constraint.
        with pytest.raises(ValueError, match="already registered"):
            set_pending_email_verification_token(db, me, "new@example.com")
