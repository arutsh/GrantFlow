"""Create conversations and messages tables

Revision ID: 001_conversations
Revises:
Create Date: 2026-07-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import shared

revision: str = "001_conversations"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("customer_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("user_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversations_customer_id"), "conversations", ["customer_id"], unique=False
    )
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False)
    op.create_index(
        "ix_conversations_last_activity_at", "conversations", ["last_activity_at"], unique=False
    )

    op.create_table(
        "messages",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("conversation_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=True),
        sa.Column("tool_params", sa.JSON(), nullable=True),
        sa.Column("tool_result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False
    )
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_messages_created_at"), "messages", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_conversations_last_activity_at", table_name="conversations")
    op.drop_index(op.f("ix_conversations_user_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_customer_id"), table_name="conversations")
    op.drop_table("conversations")
