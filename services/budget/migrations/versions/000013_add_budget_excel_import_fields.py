"""Add excel-import save-as-template tracking fields to budgets

Revision ID: 000013
Revises: 000012
Create Date: 2026-08-18 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "000013"
down_revision: Union[str, Sequence[str], None] = "000012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("budgets", sa.Column("excel_import_fingerprint", sa.String(), nullable=True))
    op.add_column("budgets", sa.Column("excel_import_structure", sa.JSON(), nullable=True))
    op.add_column(
        "budgets", sa.Column("excel_import_lines_locked_count", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("budgets", "excel_import_lines_locked_count")
    op.drop_column("budgets", "excel_import_structure")
    op.drop_column("budgets", "excel_import_fingerprint")
