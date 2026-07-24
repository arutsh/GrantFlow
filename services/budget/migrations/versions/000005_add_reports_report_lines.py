"""Add reports, report_lines

Revision ID: 000005
Revises: 000004
Create Date: 2026-07-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import shared.db.type_decorators

revision: str = "000005"
down_revision: Union[str, Sequence[str], None] = "000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("budget_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "submitted", "approved", "rejected", name="report_status"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.Column("review_notes", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.Column("updated_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_id"), "reports", ["id"], unique=False)

    op.create_table(
        "report_lines",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("report_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("budget_line_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("extra_fields", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.Column("updated_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
        sa.ForeignKeyConstraint(["budget_line_id"], ["budget_lines.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_report_lines_id"), "report_lines", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_report_lines_id"), table_name="report_lines")
    op.drop_table("report_lines")
    op.drop_index(op.f("ix_reports_id"), table_name="reports")
    op.drop_table("reports")
    sa.Enum(name="report_status").drop(op.get_bind(), checkfirst=True)
