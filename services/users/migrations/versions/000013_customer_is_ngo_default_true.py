"""Align customers.is_ngo server_default with true

Revision ID: 000013
Revises: 000012
Create Date: 2026-09-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "000013"
down_revision: Union[str, Sequence[str], None] = "000012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("customers", "is_ngo", server_default="true")


def downgrade() -> None:
    op.alter_column("customers", "is_ngo", server_default="false")
