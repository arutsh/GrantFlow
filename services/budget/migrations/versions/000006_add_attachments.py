"""Add attachments

Revision ID: 000006
Revises: 000005
Create Date: 2026-07-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import shared.db.type_decorators

revision: str = "000006"
down_revision: Union[str, Sequence[str], None] = "000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("report_line_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.Column("updated_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.ForeignKeyConstraint(["report_line_id"], ["report_lines.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attachments_id"), "attachments", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_attachments_id"), table_name="attachments")
    op.drop_table("attachments")
