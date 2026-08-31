"""Tests for POST /api/bug-reports/ (ticket #258): submission with/without a
screenshot, upload validation (size/content-type), auth, and the
notification-failure-does-not-fail-submission requirement.

Same real-sqlite-session convention as test_attachment_routes.py in budget —
the storage layer and the celery producer are mocked at the
`bug_report_services` module boundary.
"""

import io
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import DomainError
from app.models.base import Base
from app.models.bug_report import BugReportModel
from app.services.bug_report_services import MAX_SCREENSHOT_SIZE, submit_bug_report_service
from tests.factories.user import make_valid_user

# Real PNG magic bytes — the content-type sniff check rejects uploads whose
# bytes don't match their declared Content-Type, so a successful-upload test
# needs genuine-looking content.
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake png content for tests"


def _valid_user(user_id=None):
    return make_valid_user(user_id=user_id or str(uuid4()))


def _make_upload_file(content: bytes, filename="screenshot.png", content_type="image/png"):
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def _client_timestamp():
    return datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[BugReportModel.__table__])
    return sessionmaker(bind=engine)()


@pytest.fixture
def storage():
    with patch("app.services.bug_report_services.storage_client") as mock_storage:
        yield mock_storage


@pytest.fixture
def enqueue():
    with patch("app.services.bug_report_services.enqueue_bug_report_notification") as mock_fn:
        yield mock_fn


class TestSubmitBugReportService:
    def test_submission_without_screenshot(self, db, storage, enqueue):
        result = submit_bug_report_service(
            db,
            _valid_user(),
            description="Something broke",
            page_path="/budgets/123",
            user_agent="Mozilla/5.0",
            client_timestamp=_client_timestamp(),
        )

        assert result.description == "Something broke"
        assert result.screenshot_storage_key is None
        storage.save.assert_not_called()
        enqueue.assert_called_once()

    def test_submission_with_screenshot(self, db, storage, enqueue):
        upload = _make_upload_file(PNG_BYTES)

        result = submit_bug_report_service(
            db,
            _valid_user(),
            description="Something broke",
            page_path="/budgets/123",
            user_agent="Mozilla/5.0",
            client_timestamp=_client_timestamp(),
            screenshot=upload,
        )

        assert result.screenshot_storage_key is not None
        assert result.screenshot_storage_key.startswith(f"bug-reports/{result.id}/")
        storage.save.assert_called_once()
        enqueue.assert_called_once()

    def test_oversized_screenshot_rejected(self, db, storage, enqueue):
        upload = _make_upload_file(b"x" * (MAX_SCREENSHOT_SIZE + 1))

        with pytest.raises(DomainError):
            submit_bug_report_service(
                db,
                _valid_user(),
                description="Something broke",
                page_path="/budgets/123",
                user_agent="Mozilla/5.0",
                client_timestamp=_client_timestamp(),
                screenshot=upload,
            )
        storage.save.assert_not_called()
        enqueue.assert_not_called()

    def test_disallowed_content_type_rejected(self, db, storage, enqueue):
        upload = _make_upload_file(b"not an image", filename="notes.txt", content_type="text/plain")

        with pytest.raises(DomainError):
            submit_bug_report_service(
                db,
                _valid_user(),
                description="Something broke",
                page_path="/budgets/123",
                user_agent="Mozilla/5.0",
                client_timestamp=_client_timestamp(),
                screenshot=upload,
            )
        storage.save.assert_not_called()
        enqueue.assert_not_called()

    def test_spoofed_content_type_rejected(self, db, storage, enqueue):
        # Declares image/png but the bytes are plain text — the allowlist
        # check alone would let this through; the magic-byte sniff must not.
        upload = _make_upload_file(b"not actually a png", filename="fake.png")

        with pytest.raises(DomainError):
            submit_bug_report_service(
                db,
                _valid_user(),
                description="Something broke",
                page_path="/budgets/123",
                user_agent="Mozilla/5.0",
                client_timestamp=_client_timestamp(),
                screenshot=upload,
            )
        storage.save.assert_not_called()
        enqueue.assert_not_called()

    def test_enqueues_with_reporter_and_last_api_call(self, db, storage, enqueue):
        user = _valid_user(user_id="11111111-1111-1111-1111-111111111111")

        submit_bug_report_service(
            db,
            user,
            description="Something broke",
            page_path="/budgets/123",
            user_agent="Mozilla/5.0",
            client_timestamp=_client_timestamp(),
            last_api_call="GET /api/v1/budgets/123 (500)",
        )

        kwargs = enqueue.call_args.kwargs
        assert kwargs["user_id"] == "11111111-1111-1111-1111-111111111111"
        assert kwargs["last_api_call"] == "GET /api/v1/budgets/123 (500)"
        # No active OTEL span in this test process — graceful None, not a crash.
        assert kwargs["trace_id"] is None

    def test_notification_failure_does_not_fail_submission(self, db, storage, enqueue):
        enqueue.side_effect = Exception("broker unreachable")

        result = submit_bug_report_service(
            db,
            _valid_user(),
            description="Something broke",
            page_path="/budgets/123",
            user_agent="Mozilla/5.0",
            client_timestamp=_client_timestamp(),
        )

        assert result.id is not None


class TestBugReportRoutesWiring:
    def test_submit_route_delegates_to_service(self, make_client):
        client = make_client()
        with patch(
            "app.api.bug_report_routes.submit_bug_report_service",
        ) as mock_service:
            mock_service.return_value = BugReportModel(
                id=uuid4(),
                user_id=uuid4(),
                description="Something broke",
                page_path="/budgets/123",
                user_agent="Mozilla/5.0",
                client_timestamp=_client_timestamp(),
                screenshot_storage_key=None,
            )
            response = client.post(
                "/api/bug-reports/",
                data={
                    "description": "Something broke",
                    "page_path": "/budgets/123",
                    "user_agent": "Mozilla/5.0",
                    "client_timestamp": _client_timestamp().isoformat(),
                },
            )
        assert response.status_code == 200
        mock_service.assert_called_once()

    def test_requires_auth(self, make_client):
        client = make_client()
        app = client.app
        from app.utils.security import get_current_user
        from shared.security.dependencies import get_validated_user

        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_validated_user]

        response = client.post(
            "/api/bug-reports/",
            data={
                "description": "Something broke",
                "page_path": "/budgets/123",
                "user_agent": "Mozilla/5.0",
                "client_timestamp": _client_timestamp().isoformat(),
            },
        )

        assert response.status_code == 401
