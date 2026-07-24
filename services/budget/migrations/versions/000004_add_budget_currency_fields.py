"""Add actual_currency, start_date to budgets

Revision ID: 000004
Revises: 000003
Create Date: 2026-07-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "000004"
down_revision: Union[str, Sequence[str], None] = "000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("budgets", sa.Column("actual_currency", sa.String(length=3), nullable=True))
    op.add_column("budgets", sa.Column("start_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("budgets", "start_date")
    op.drop_column("budgets", "actual_currency")
