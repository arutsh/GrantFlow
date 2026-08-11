"""add deletion and pending-email rectification fields to users

Revision ID: 000007
Revises: 000006
Create Date: 2026-08-10 00:00:00.000001

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "000007"
down_revision: Union[str, Sequence[str], None] = "000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("deletion_requested_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("pending_email", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "pending_email")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "deletion_requested_at")
