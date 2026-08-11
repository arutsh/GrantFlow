"""add index on users.pending_email

Revision ID: 000008
Revises: 000007
Create Date: 2026-08-11 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "000008"
down_revision: Union[str, Sequence[str], None] = "000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Backs the email==X OR pending_email==X lookup on /auth/verify-email.
    op.create_index(
        "ix_users_pending_email",
        "users",
        ["pending_email"],
        postgresql_where=sa.text("pending_email IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_users_pending_email", table_name="users")
