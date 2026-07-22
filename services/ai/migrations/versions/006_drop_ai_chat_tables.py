"""Drop ai_chat_sessions and ai_chat_messages

Fresh-start decision: chat history now lives in services/chat's own
conversations/messages tables (see the ai-chat-agent-host-migration
OpenSpec change). The old PydanticAI-serialized history in these tables
is not migrated.

Revision ID: 006_drop_ai_chat_tables
Revises: 005
Create Date: 2026-07-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import shared

revision: str = "006_drop_ai_chat_tables"
down_revision: Union[str, Sequence[str], None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_ai_chat_messages_session_created", table_name="ai_chat_messages")
    op.drop_index(op.f("ix_ai_chat_messages_session_id"), table_name="ai_chat_messages")
    op.drop_table("ai_chat_messages")

    op.drop_index("ix_ai_chat_sessions_last_activity_at", table_name="ai_chat_sessions")
    op.drop_index(op.f("ix_ai_chat_sessions_user_id"), table_name="ai_chat_sessions")
    op.drop_index(op.f("ix_ai_chat_sessions_customer_id"), table_name="ai_chat_sessions")
    op.drop_table("ai_chat_sessions")


def downgrade() -> None:
    op.create_table(
        "ai_chat_sessions",
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
        op.f("ix_ai_chat_sessions_customer_id"),
        "ai_chat_sessions",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_chat_sessions_user_id"),
        "ai_chat_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_chat_sessions_last_activity_at",
        "ai_chat_sessions",
        ["last_activity_at"],
        unique=False,
    )

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
