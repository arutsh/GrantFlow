import os

# Must be set before any test module imports `main` — importing it initializes
# OpenTelemetry, and without this guard test runs try to export telemetry to a
# collector on localhost:4317 (slow runs + "Logging error" noise at shutdown).
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from main import app  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.budget import BudgetModel, BudgetLineModel, BudgetCategoryModel  # noqa: E402
from app.models.report import ReportModel, ReportLineModel, AttachmentModel  # noqa: E402
from app.models.currency_ledger import (  # noqa: E402
    ReportLineConversionAllocationModel,
)
from app.models.privileged_access_log import PrivilegedAccessLog  # noqa: E402
from shared.security.dependencies import get_validated_user  # noqa: E402
from tests.factories.user import ValidUserFactory  # noqa: E402


@pytest.fixture
def make_client():
    """Build a TestClient authenticated as a fresh fake user.

    Usage:
        client = make_client()                    # regular user
        client = make_client(role="superuser")    # override any JWT field
        client.user                               # the fake JWT payload dict

    Older test files carry their own autouse auth override; new tests should
    use this instead.
    """

    def _make(**user_kwargs):
        user = ValidUserFactory(**user_kwargs)
        app.dependency_overrides[get_validated_user] = lambda: user
        client = TestClient(app)
        client.user = user
        return client

    yield _make
    app.dependency_overrides = {}


@pytest.fixture
def db():
    """Real in-memory sqlite session covering Budget/BudgetLine/BudgetCategory/
    Report/ReportLine/Attachment/ReportLineConversionAllocation/
    PrivilegedAccessLog — shared by any
    test that exercises budget<->report behavior against real SQLAlchemy
    relationships rather than mocking every crud call (see test_report_routes.py
    and test_budget_confirmation_lifecycle.py). Attachment/allocation tables are
    needed even for tests that never create either, since ReportLineModel's
    delete-orphan cascade touches them when a report line is deleted.
    """
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
            ReportLineConversionAllocationModel.__table__,
            PrivilegedAccessLog.__table__,
        ],
    )
    return sessionmaker(bind=engine)()
