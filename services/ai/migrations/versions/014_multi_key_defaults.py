"""Allow multiple user_provider_keys rows per (customer_id, provider); add
explicit default

Drops the one-row-per-provider unique constraint, adds `label` and
`is_default`, and backfills `is_default = true` on the oldest row per
customer_id (every customer keeps a working default, including orgs with
keys for more than one provider).

Revision ID: 014_multi_key_defaults
Revises: 013_excel_extract_v4_localtgt
Create Date: 2026-08-31 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "014_multi_key_defaults"
down_revision: Union[str, Sequence[str], None] = "013_excel_extract_v4_localtgt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_user_provider_keys_customer_provider", "user_provider_keys", type_="unique"
    )
    op.add_column("user_provider_keys", sa.Column("label", sa.String(), nullable=True))
    op.add_column(
        "user_provider_keys",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.execute(
        sa.text(
            """
            UPDATE user_provider_keys
            SET is_default = TRUE
            WHERE id IN (
                SELECT id FROM (
                    SELECT id, customer_id,
                           ROW_NUMBER() OVER (
                               PARTITION BY customer_id ORDER BY created_at, id
                           ) AS rn
                    FROM user_provider_keys
                    WHERE customer_id IS NOT NULL
                ) ranked
                WHERE rn = 1
            )
            """
        )
    )

    op.create_index(
        "uq_user_provider_keys_customer_default",
        "user_provider_keys",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
        sqlite_where=sa.text("is_default"),
    )


def downgrade() -> None:
    op.drop_index("uq_user_provider_keys_customer_default", table_name="user_provider_keys")
    op.drop_column("user_provider_keys", "is_default")
    op.drop_column("user_provider_keys", "label")
    op.create_unique_constraint(
        "uq_user_provider_keys_customer_provider",
        "user_provider_keys",
        ["customer_id", "provider_id"],
    )
