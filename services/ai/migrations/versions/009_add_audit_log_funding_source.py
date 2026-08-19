"""Add funding_source to ai_audit_logs (BYOK vs GrantFlow-funded)

Revision ID: 009_add_audit_log_funding_source
Revises: 008_add_privileged_access_logs
Create Date: 2026-08-17 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009_add_audit_log_funding_source"
down_revision: Union[str, Sequence[str], None] = "008_add_privileged_access_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_audit_logs",
        sa.Column("funding_source", sa.String(), nullable=False, server_default="byok"),
    )


def downgrade() -> None:
    op.drop_column("ai_audit_logs", "funding_source")
