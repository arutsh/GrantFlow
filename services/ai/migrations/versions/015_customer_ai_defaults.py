"""Create customer_ai_defaults table

Revision ID: 015_customer_ai_defaults
Revises: 014_multi_key_defaults
Create Date: 2026-08-31 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import shared

revision: str = "015_customer_ai_defaults"
down_revision: Union[str, Sequence[str], None] = "014_multi_key_defaults"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_ai_defaults",
        sa.Column("customer_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column(
            "platform_fallback_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("customer_id"),
    )


def downgrade() -> None:
    op.drop_table("customer_ai_defaults")
