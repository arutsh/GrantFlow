"""Add ai_chat_messages table and customer_id to user_provider_keys

Revision ID: 005
Revises: 004_create_ai_chat_sessions
Create Date: 2026-06-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import shared

revision: str = "005"
down_revision: Union[str, Sequence[str], None] = "004_create_ai_chat_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_chat_messages",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("session_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=True),
        sa.Column("tool_call_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"], ["ai_chat_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_chat_messages_session_id"),
        "ai_chat_messages",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_chat_messages_session_created",
        "ai_chat_messages",
        ["session_id", "created_at"],
        unique=False,
    )

    op.add_column(
        "user_provider_keys",
        sa.Column("customer_id", shared.db.type_decorators.GUID(), nullable=True),
    )
    op.create_index(
        op.f("ix_user_provider_keys_customer_id"),
        "user_provider_keys",
        ["customer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_provider_keys_customer_id"), table_name="user_provider_keys"
    )
    op.drop_column("user_provider_keys", "customer_id")

    op.drop_index("ix_ai_chat_messages_session_created", table_name="ai_chat_messages")
    op.drop_index(
        op.f("ix_ai_chat_messages_session_id"), table_name="ai_chat_messages"
    )
    op.drop_table("ai_chat_messages")
