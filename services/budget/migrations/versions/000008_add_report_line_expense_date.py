"""Add report_lines.expense_date

Revision ID: 000008
Revises: 000007
Create Date: 2026-07-29 00:00:00.000000

Adds the real-world date an expense happened, distinct from AuditMixin's
created_at (when the row was written) — a receipt entered today for a
purchase 10 days ago needs to record the 10-days-ago date. Any existing
rows (report-line creation has no shipped frontend yet, so this is expected
to be zero or a handful of manually-tested dev rows) are backfilled to
their created_at date as a one-time best-effort approximation, then the
column is locked to NOT NULL for everything going forward.

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "000008"
down_revision: Union[str, Sequence[str], None] = "000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("report_lines", sa.Column("expense_date", sa.Date(), nullable=True))
    op.execute(
        "UPDATE report_lines SET expense_date = CAST(created_at AS DATE) "
        "WHERE expense_date IS NULL"
    )
    op.alter_column("report_lines", "expense_date", nullable=False)


def downgrade() -> None:
    op.drop_column("report_lines", "expense_date")
