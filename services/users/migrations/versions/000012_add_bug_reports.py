"""add bug_reports table

Revision ID: 000012
Revises: 000011
Create Date: 2026-08-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import shared.db.type_decorators

# revision identifiers, used by Alembic.
revision: str = "000012"
down_revision: Union[str, Sequence[str], None] = "000011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "bug_reports",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("user_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("page_path", sa.String(), nullable=False),
        sa.Column("user_agent", sa.String(), nullable=False),
        sa.Column("client_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("screenshot_storage_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.Column("updated_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bug_reports_id", "bug_reports", ["id"], unique=False)
    op.create_index("ix_bug_reports_user_id", "bug_reports", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_bug_reports_user_id", table_name="bug_reports")
    op.drop_index("ix_bug_reports_id", table_name="bug_reports")
    op.drop_table("bug_reports")
