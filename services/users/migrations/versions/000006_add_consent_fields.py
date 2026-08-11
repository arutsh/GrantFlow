"""add consent fields to users

Revision ID: 000006
Revises: 000005
Create Date: 2026-08-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "000006"
down_revision: Union[str, Sequence[str], None] = "000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("consent_data_processing_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("consent_marketing_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "consent_marketing_at")
    op.drop_column("users", "consent_data_processing_at")
