"""Scope user_provider_keys by customer_id instead of user_id

Fixes a pre-existing bug: AI provider settings were looked up by the
individual caller's user_id, so two admins of the same org could each save
a separate row and silently shadow one another (see the
superuser-cross-tenant-access OpenSpec change). Lookups now key on
(customer_id, provider_id) instead of (user_id, provider_id).

Data-migration note: this is dev/demo data only at this stage — no
production backfill concern. Any rows sharing the same (customer_id,
provider_id) (the exact bug this migration fixes) are deduped, keeping only
the most recently updated row, so the new unique constraint can be added
without failing on existing local/dev data. Rows with a NULL customer_id
predate customer_id's introduction (migration 005) and are left in place —
they're simply unreachable via the customer_id-keyed lookup going forward.

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
