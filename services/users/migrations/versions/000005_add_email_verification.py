"""add email verification fields to users

Revision ID: 000005
Revises: 000004
Create Date: 2026-08-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "000005"
down_revision: Union[str, Sequence[str], None] = "000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("email_verification_token_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("email_verification_expires_at", sa.DateTime(), nullable=True))

    # Pre-existing accounts had implicit trust before this capability
    # existed — only new signups going forward should be gated.
    op.execute("UPDATE users SET email_verified = true")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_token_hash")
    op.drop_column("users", "email_verified")
