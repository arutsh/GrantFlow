"""Add total_amount to budgets, backfilled from budget_lines

Revision ID: 000003
Revises: 000002
Create Date: 2026-07-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "000003"
down_revision: Union[str, Sequence[str], None] = "000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "budgets",
        sa.Column("total_amount", sa.Float(), nullable=True, server_default="0"),
    )
    op.execute("""
        UPDATE budgets
        SET total_amount = COALESCE(
            (SELECT SUM(bl.amount) FROM budget_lines bl WHERE bl.budget_id = budgets.id),
            0
        )
        """)


def downgrade() -> None:
    op.drop_column("budgets", "total_amount")
