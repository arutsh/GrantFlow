from uuid import UUID

from shared.schemas.report_schema import ReportStatus  # noqa: F401
from shared.schemas.report_schema import ReportBase  # noqa: F401
from shared.schemas.report_schema import ReportCreate  # noqa: F401
from shared.schemas.report_schema import ReportUpdate  # noqa: F401
from shared.schemas.report_schema import Report  # noqa: F401
from shared.schemas.report_schema import ReportWithLines  # noqa: F401
from shared.schemas.report_schema import ReportReviewRequest  # noqa: F401
from app.schemas.budget_schema import BudgetStatus


class ReportWithBudgetInfo(Report):
    """Report plus its parent budget's name/status/funder/owner — used by
    both the owner's reports directory (GET /reports/) and the donor's
    funded-reports directory (GET /reports/funded/), where a flat list of
    reports needs enough budget context to be useful without a second
    per-row lookup. Populated by the service layer from an eager-loaded
    Report.budget, not by from_attributes on the Report row alone.
    `owner_id`/`owner_name` are only resolved (via a customer lookup) on the
    funded-reports directory, where the viewer needs to know which grantee
    each report belongs to — left `None` on the owner's own directory, where
    every row's owner is the viewer themselves."""

    budget_name: str | None = None
    budget_status: BudgetStatus | None = None
    funding_customer_id: UUID | None = None
    external_funder_name: str | None = None
    owner_id: UUID | None = None
    owner_name: str | None = None
