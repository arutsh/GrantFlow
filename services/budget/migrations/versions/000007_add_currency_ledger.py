"""Add currency ledger

Revision ID: 000007
Revises: 000006
Create Date: 2026-07-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import shared.db.type_decorators

revision: str = "000007"
down_revision: Union[str, Sequence[str], None] = "000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "funding_receipts",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("budget_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("received_at", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.Column("updated_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_funding_receipts_id"), "funding_receipts", ["id"], unique=False)

    op.create_table(
        "currency_conversions",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("budget_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("donor_amount", sa.Float(), nullable=False),
        sa.Column("local_amount", sa.Float(), nullable=False),
        sa.Column("converted_at", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.Column("updated_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_currency_conversions_id"), "currency_conversions", ["id"], unique=False
    )

    op.create_table(
        "report_line_conversion_allocations",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("report_line_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("conversion_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("amount_allocated", sa.Float(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.Column("updated_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.ForeignKeyConstraint(["report_line_id"], ["report_lines.id"]),
        sa.ForeignKeyConstraint(["conversion_id"], ["currency_conversions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_report_line_conversion_allocations_id"),
        "report_line_conversion_allocations",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_report_line_conversion_allocations_id"),
        table_name="report_line_conversion_allocations",
    )
    op.drop_table("report_line_conversion_allocations")

    op.drop_index(op.f("ix_currency_conversions_id"), table_name="currency_conversions")
    op.drop_table("currency_conversions")

    op.drop_index(op.f("ix_funding_receipts_id"), table_name="funding_receipts")
    op.drop_table("funding_receipts")
