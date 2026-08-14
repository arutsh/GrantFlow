"""
Tests for ticket #147: attachment upload/download/delete, upload validation
(size/content-type), and the draft-only lock shared with report lines.
Also covers ticket #157: presigned download-URL generation and its
redirect route.

Same real-sqlite-session convention as test_report_line_routes.py. The
storage layer (ticket #145) is mocked at the `attachment_services` module
boundary — these tests exercise validation/authorization/lock logic, not
the S3-compatible backend itself (that's `test_storage_service.py`'s job).
"""

import io
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import DomainError, PermissionDenied
from app.models.base import Base
from app.models.budget import BudgetModel, BudgetLineModel, BudgetCategoryModel
from app.models.report import ReportModel, ReportLineModel, AttachmentModel
from app.schemas.budget_schema import BudgetStatus
from app.schemas.report_schema import ReportStatus
from app.services.attachment_services import (
    upload_attachment_service,
    list_attachments_service,
    download_attachment_service,
    get_attachment_download_url_service,
    delete_attachment_service,
    MAX_ATTACHMENT_SIZE,
)
from tests.factories.user import make_valid_user

OWNER_ID = str(uuid4())
FUNDER_ID = str(uuid4())
STRANGER_ID = str(uuid4())
# Real PDF magic bytes — the content-type sniff check (ticket #157 review
# fix) rejects uploads whose bytes don't match their declared Content-Type,
# so any test expecting a successful upload needs genuine-looking content.
PDF_BYTES = b"%PDF-1.4\nfake receipt content for tests"


def _valid_user(customer_id):
    return make_valid_user(customer_id=customer_id)


def _make_upload_file(content: bytes, filename="receipt.pdf", content_type="application/pdf"):
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            BudgetModel.__table__,
            BudgetLineModel.__table__,
            BudgetCategoryModel.__table__,
            ReportModel.__table__,
            ReportLineModel.__table__,
            AttachmentModel.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


@pytest.fixture
def storage():
    with patch("app.services.attachment_services.storage_client") as mock_storage:
        yield mock_storage


def _make_budget(db, owner_id=OWNER_ID, funding_customer_id=None):
    budget = BudgetModel(
        name="Test Budget",
        owner_id=owner_id,
        funding_customer_id=funding_customer_id,
        status=BudgetStatus.confirmed,
        start_date=date(2026, 1, 1),
        duration_months=12,
        local_currency="GBP",
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def _make_budget_line(db, budget_id, amount=1000.0):
    line = BudgetLineModel(budget_id=budget_id, description="Admin costs", amount=amount)
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def _make_report(db, budget_id, status=ReportStatus.draft):
    report = ReportModel(
        budget_id=budget_id,
        name="Report",
        status=status,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _make_report_line(db, report_id, budget_line_id):
    line = ReportLineModel(
        report_id=report_id,
        budget_line_id=budget_line_id,
        description="Receipt",
        amount=50.0,
        expense_date=date(2026, 6, 15),
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


class TestUploadAttachment:
    def test_upload_happy_path(self, db, storage):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        report_line = _make_report_line(db, report.id, budget_line.id)
        upload = _make_upload_file(PDF_BYTES)

        result = upload_attachment_service(db, _valid_user(OWNER_ID), report_line.id, upload)

        assert result.report_line_id == report_line.id
        assert result.filename == "receipt.pdf"
        assert result.content_type == "application/pdf"
        assert result.size == len(PDF_BYTES)
        storage.save.assert_called_once()
        saved_key = storage.save.call_args.args[0]
        assert saved_key == result.storage_key

    def test_oversized_file_rejected(self, db, storage):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        report_line = _make_report_line(db, report.id, budget_line.id)
        upload = _make_upload_file(b"x" * (MAX_ATTACHMENT_SIZE + 1))

        with pytest.raises(DomainError):
            upload_attachment_service(db, _valid_user(OWNER_ID), report_line.id, upload)
        storage.save.assert_not_called()

    def test_disallowed_content_type_rejected(self, db, storage):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        report_line = _make_report_line(db, report.id, budget_line.id)
        upload = _make_upload_file(b"text", filename="notes.txt", content_type="text/plain")

        with pytest.raises(DomainError):
            upload_attachment_service(db, _valid_user(OWNER_ID), report_line.id, upload)
        storage.save.assert_not_called()

    def test_spoofed_content_type_rejected(self, db, storage):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        report_line = _make_report_line(db, report.id, budget_line.id)
        # Declares application/pdf but the bytes are plain text — allowlist
        # check alone would let this through; the magic-byte sniff must not.
        upload = _make_upload_file(b"not actually a pdf", filename="fake.pdf")

        with pytest.raises(DomainError):
            upload_attachment_service(db, _valid_user(OWNER_ID), report_line.id, upload)
        storage.save.assert_not_called()

    def test_rejected_on_non_draft_report(self, db, storage):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id, status=ReportStatus.submitted)
        report_line = _make_report_line(db, report.id, budget_line.id)
        upload = _make_upload_file(PDF_BYTES)

        with pytest.raises(DomainError):
            upload_attachment_service(db, _valid_user(OWNER_ID), report_line.id, upload)
        storage.save.assert_not_called()

    def test_funder_cannot_upload(self, db, storage):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        report_line = _make_report_line(db, report.id, budget_line.id)
        upload = _make_upload_file(PDF_BYTES)

        with pytest.raises(PermissionDenied):
            upload_attachment_service(db, _valid_user(FUNDER_ID), report_line.id, upload)

    def test_multiple_attachments_per_line(self, db, storage):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        report_line = _make_report_line(db, report.id, budget_line.id)

        upload_attachment_service(
            db, _valid_user(OWNER_ID), report_line.id, _make_upload_file(PDF_BYTES)
        )
        upload_attachment_service(
            db,
            _valid_user(OWNER_ID),
            report_line.id,
            _make_upload_file(PDF_BYTES, filename="proof.pdf"),
        )

        attachments = list_attachments_service(db, _valid_user(OWNER_ID), report_line.id)
        assert len(attachments) == 2


class TestDownloadAttachment:
    def test_owner_and_funder_can_download(self, db, storage):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        report_line = _make_report_line(db, report.id, budget_line.id)
        attachment = upload_attachment_service(
            db, _valid_user(OWNER_ID), report_line.id, _make_upload_file(PDF_BYTES)
        )
        storage.open_stream.return_value = io.BytesIO(b"pdf-bytes")

        owner_result, _ = download_attachment_service(db, _valid_user(OWNER_ID), attachment.id)
        funder_result, _ = download_attachment_service(db, _valid_user(FUNDER_ID), attachment.id)

        assert owner_result.id == attachment.id
        assert funder_result.id == attachment.id
        storage.open_stream.assert_called_with(attachment.storage_key)

    def test_stranger_cannot_download(self, db, storage):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        report_line = _make_report_line(db, report.id, budget_line.id)
        attachment = upload_attachment_service(
            db, _valid_user(OWNER_ID), report_line.id, _make_upload_file(PDF_BYTES)
        )

        with pytest.raises(DomainError):
            download_attachment_service(db, _valid_user(STRANGER_ID), attachment.id)


class TestDownloadUrl:
    def test_owner_and_funder_can_get_url(self, db, storage):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        report_line = _make_report_line(db, report.id, budget_line.id)
        attachment = upload_attachment_service(
            db, _valid_user(OWNER_ID), report_line.id, _make_upload_file(PDF_BYTES)
        )
        storage.presigned_download_url.return_value = "https://minio.local/signed-url"

        owner_url = get_attachment_download_url_service(db, _valid_user(OWNER_ID), attachment.id)
        funder_url = get_attachment_download_url_service(db, _valid_user(FUNDER_ID), attachment.id)

        assert owner_url == "https://minio.local/signed-url"
        assert funder_url == "https://minio.local/signed-url"
        storage.presigned_download_url.assert_called_with(
            attachment.storage_key,
            content_type=attachment.content_type,
            filename=attachment.filename,
        )

    def test_stranger_cannot_get_url(self, db, storage):
        budget = _make_budget(db, funding_customer_id=FUNDER_ID)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        report_line = _make_report_line(db, report.id, budget_line.id)
        attachment = upload_attachment_service(
            db, _valid_user(OWNER_ID), report_line.id, _make_upload_file(PDF_BYTES)
        )

        with pytest.raises(DomainError):
            get_attachment_download_url_service(db, _valid_user(STRANGER_ID), attachment.id)
        storage.presigned_download_url.assert_not_called()


class TestDeleteAttachment:
    def test_delete_removes_blob_and_row(self, db, storage):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        report_line = _make_report_line(db, report.id, budget_line.id)
        attachment = upload_attachment_service(
            db, _valid_user(OWNER_ID), report_line.id, _make_upload_file(PDF_BYTES)
        )

        delete_attachment_service(db, _valid_user(OWNER_ID), attachment.id)

        storage.delete.assert_called_once_with(attachment.storage_key)
        remaining = list_attachments_service(db, _valid_user(OWNER_ID), report_line.id)
        assert remaining == []

    def test_delete_rejected_on_non_draft_report(self, db, storage):
        budget = _make_budget(db)
        budget_line = _make_budget_line(db, budget.id)
        report = _make_report(db, budget.id)
        report_line = _make_report_line(db, report.id, budget_line.id)
        attachment = upload_attachment_service(
            db, _valid_user(OWNER_ID), report_line.id, _make_upload_file(PDF_BYTES)
        )
        report.status = ReportStatus.submitted
        db.commit()
        storage.reset_mock()

        with pytest.raises(DomainError):
            delete_attachment_service(db, _valid_user(OWNER_ID), attachment.id)
        storage.delete.assert_not_called()


class TestAttachmentRoutesWiring:
    """Thin route-level checks with the service layer mocked, matching
    test_report_routes.py's convention."""

    def test_upload_route_delegates_to_service(self, make_client):
        client = make_client()
        with patch(
            "app.api.attachment_routes.upload_attachment_service",
            return_value=SimpleNamespace(id=uuid4()),
        ) as mock_service:
            response = client.post(
                "/api/v1/attachments/",
                data={"report_line_id": str(uuid4())},
                files={"file": ("receipt.pdf", b"pdf-bytes", "application/pdf")},
            )
        assert response.status_code == 200
        mock_service.assert_called_once()

    def test_upload_route_sets_span_attributes(self, make_client):
        client = make_client()
        report_line_id = uuid4()
        attachment_id = uuid4()
        with (
            patch(
                "app.api.attachment_routes.upload_attachment_service",
                return_value=SimpleNamespace(id=attachment_id),
            ),
            patch("app.api.attachment_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.post(
                "/api/v1/attachments/",
                data={"report_line_id": str(report_line_id)},
                files={"file": ("receipt.pdf", b"pdf-bytes", "application/pdf")},
            )
        mock_set_span_attrs.assert_any_call(report_line_id=report_line_id)
        mock_set_span_attrs.assert_any_call(attachment_id=attachment_id)

    def test_download_route_streams_content(self, make_client):
        client = make_client()
        attachment_stub = SimpleNamespace(content_type="application/pdf", filename="receipt.pdf")
        with patch(
            "app.api.attachment_routes.download_attachment_service",
            return_value=(attachment_stub, io.BytesIO(b"pdf-bytes")),
        ) as mock_service:
            response = client.get(f"/api/v1/attachments/{uuid4()}/content")
        assert response.status_code == 200
        assert response.content == b"pdf-bytes"
        assert response.headers["content-type"] == "application/pdf"
        mock_service.assert_called_once()

    def test_download_url_route_redirects(self, make_client):
        client = make_client()
        with patch(
            "app.api.attachment_routes.get_attachment_download_url_service",
            return_value="https://minio.local/signed-url",
        ) as mock_service:
            response = client.get(
                f"/api/v1/attachments/{uuid4()}/download-url", follow_redirects=False
            )
        assert response.status_code == 307
        assert response.headers["location"] == "https://minio.local/signed-url"
        mock_service.assert_called_once()

    def test_delete_route_delegates_to_service(self, make_client):
        client = make_client()
        with patch(
            "app.api.attachment_routes.delete_attachment_service", return_value=True
        ) as mock_service:
            response = client.delete(f"/api/v1/attachments/{uuid4()}")
        assert response.status_code == 200
        assert response.json() == {"success": True}
        mock_service.assert_called_once()

    def test_delete_route_sets_attachment_id_span_attribute(self, make_client):
        client = make_client()
        attachment_id = uuid4()
        with (
            patch("app.api.attachment_routes.delete_attachment_service", return_value=True),
            patch("app.api.attachment_routes.set_span_attributes") as mock_set_span_attrs,
        ):
            client.delete(f"/api/v1/attachments/{attachment_id}")
        mock_set_span_attrs.assert_any_call(attachment_id=attachment_id)
