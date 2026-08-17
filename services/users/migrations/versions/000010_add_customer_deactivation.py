"""add deactivated_at to customers

Revision ID: 000010
Revises: 000009
Create Date: 2026-08-17 00:00:00.000001

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "000010"
down_revision: Union[str, Sequence[str], None] = "000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("customers", sa.Column("deactivated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("customers", "deactivated_at")
