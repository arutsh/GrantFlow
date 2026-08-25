"""Extend donor_templates with fingerprint, detected_structure, version

Revision ID: 000012
Revises: 000011
Create Date: 2026-08-17 00:00:01.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "000012"
down_revision: Union[str, Sequence[str], None] = "000011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("donor_templates", sa.Column("fingerprint", sa.String(), nullable=True))
    op.add_column(
        "donor_templates",
        sa.Column("detected_structure", sa.JSON(), nullable=True),
    )
    op.add_column(
        "donor_templates",
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.create_index(
        op.f("ix_donor_templates_fingerprint"), "donor_templates", ["fingerprint"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_donor_templates_fingerprint"), table_name="donor_templates")
    op.drop_column("donor_templates", "version")
    op.drop_column("donor_templates", "detected_structure")
    op.drop_column("donor_templates", "fingerprint")
