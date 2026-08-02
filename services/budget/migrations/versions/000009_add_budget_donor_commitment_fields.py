"""Add budgets.donor_total_amount/estimated_exchange_rate/confirmed_at

Revision ID: 000009
Revises: 000008
Create Date: 2026-08-01 00:00:00.000000

Additive-only, no backfill: existing budgets simply have none of these set,
identical to their current state. `confirmed_at` stays null for already-
confirmed budgets rather than being backfilled from `updated_at` (not a
reliable proxy — see budget-report-iteration-2/design.md's Context).

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "000009"
down_revision: Union[str, Sequence[str], None] = "000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("budgets", sa.Column("donor_total_amount", sa.Float(), nullable=True))
    op.add_column("budgets", sa.Column("estimated_exchange_rate", sa.Float(), nullable=True))
    op.add_column("budgets", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("budgets", "confirmed_at")
    op.drop_column("budgets", "estimated_exchange_rate")
    op.drop_column("budgets", "donor_total_amount")
