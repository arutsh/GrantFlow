"""Create ai_provider_models — the per-provider model catalog, seeded here
directly (no admin UI/CRUD yet, see ai-provider-key-defaults design.md)

Revision ID: 016_ai_provider_models
Revises: 015_customer_ai_defaults
Create Date: 2026-08-31 00:00:00.000000

"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa

from shared.db.type_decorators import GUID

revision: str = "016_ai_provider_models"
down_revision: Union[str, Sequence[str], None] = "015_customer_ai_defaults"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MODELS_BY_PROVIDER = {
    "anthropic": [
        ("claude-sonnet-4-6", "Claude Sonnet 4.6"),
        ("claude-haiku-4-5", "Claude Haiku 4.5"),
        ("claude-opus-4-5", "Claude Opus 4.5"),
    ],
    "ollama": [
        ("llama3.2", "Llama 3.2"),
        ("gemma4:12b", "Gemma 4 12B"),
        ("qwen3.6:27b", "Qwen 3.6 27B"),
        ("deepseek-coder:6.7b", "DeepSeek Coder 6.7B"),
    ],
}


def upgrade() -> None:
    op.create_table(
        "ai_provider_models",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("provider_id", GUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["provider_id"], ["ai_providers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_id", "name", name="uq_ai_provider_models_provider_name"
        ),
    )

    bind = op.get_bind()
    provider_id_by_name = {
        row.name: row.id
        for row in bind.execute(sa.text("SELECT id, name FROM ai_providers")).fetchall()
    }

    for provider_name, models in _MODELS_BY_PROVIDER.items():
        provider_id = provider_id_by_name.get(provider_name)
        if provider_id is None:
            continue
        for name, display_name in models:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO ai_provider_models (id, provider_id, name, display_name, is_active)
                    VALUES (:id, :provider_id, :name, :display_name, TRUE)
                    """
                ).bindparams(
                    id=str(uuid.uuid4()),
                    provider_id=provider_id,
                    name=name,
                    display_name=display_name,
                )
            )


def downgrade() -> None:
    op.drop_table("ai_provider_models")
