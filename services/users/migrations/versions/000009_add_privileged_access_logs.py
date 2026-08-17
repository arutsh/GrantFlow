"""Add privileged_access_logs table

Revision ID: 000009
Revises: 000008
Create Date: 2026-08-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import shared.db.type_decorators

revision: str = "000009"
down_revision: Union[str, Sequence[str], None] = "000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "privileged_access_logs",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("actor_user_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("customer_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_privileged_access_logs_actor_user_id",
        "privileged_access_logs",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_privileged_access_logs_customer_id",
        "privileged_access_logs",
        ["customer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_privileged_access_logs_customer_id", table_name="privileged_access_logs")
    op.drop_index("ix_privileged_access_logs_actor_user_id", table_name="privileged_access_logs")
    op.drop_table("privileged_access_logs")
