"""Scope user_provider_keys by customer_id instead of user_id

Dedupes any existing (customer_id, provider_id) duplicates (keeping the
newest) before adding the new unique constraint; dev/demo data only, no
production backfill concern.

Revision ID: 007_customer_scope_user_provider_keys
Revises: 006_drop_ai_chat_tables
Create Date: 2026-08-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_customer_scope_user_provider_keys"
down_revision: Union[str, Sequence[str], None] = "006_drop_ai_chat_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM user_provider_keys upk
            USING (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY customer_id, provider_id
                    ORDER BY updated_at DESC, id
                ) AS rn
                FROM user_provider_keys
                WHERE customer_id IS NOT NULL
            ) ranked
            WHERE upk.id = ranked.id AND ranked.rn > 1
            """
        )
    )
    op.drop_constraint(
        "uq_user_provider_keys_user_provider", "user_provider_keys", type_="unique"
    )
    op.create_unique_constraint(
        "uq_user_provider_keys_customer_provider",
        "user_provider_keys",
        ["customer_id", "provider_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_user_provider_keys_customer_provider", "user_provider_keys", type_="unique"
    )
    op.create_unique_constraint(
        "uq_user_provider_keys_user_provider",
        "user_provider_keys",
        ["user_id", "provider_id"],
    )
