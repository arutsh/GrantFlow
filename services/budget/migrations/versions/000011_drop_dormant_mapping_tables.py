"""Drop dormant donor-mapping tables, superseded by AI-first Excel extraction

Revision ID: 000011
Revises: 000010
Create Date: 2026-08-17 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import shared

revision: str = "000011"
down_revision: Union[str, Sequence[str], None] = "000010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DROPPED_TABLES = (
    "ngo_mappings",
    "template_budget_mappings",
    "donor_fields",
    "uploaded_templates",
    "semantic_field_mappings",
)


def upgrade() -> None:
    bind = op.get_bind()
    for table in _DROPPED_TABLES:
        count = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar()
        if count:
            raise RuntimeError(
                f"Refusing to drop '{table}': {count} row(s) present. "
                "This migration only runs against confirmed-empty tables."
            )

    op.drop_index(op.f("ix_ngo_mappings_owner_id"), table_name="ngo_mappings")
    op.drop_index(op.f("ix_ngo_mappings_id"), table_name="ngo_mappings")
    op.drop_index(op.f("ix_ngo_mappings_donor_field_id"), table_name="ngo_mappings")
    op.drop_table("ngo_mappings")

    op.drop_index(op.f("ix_template_budget_mappings_id"), table_name="template_budget_mappings")
    op.drop_table("template_budget_mappings")

    op.drop_index(op.f("ix_donor_fields_id"), table_name="donor_fields")
    op.drop_index(op.f("ix_donor_fields_donor_template_id"), table_name="donor_fields")
    op.drop_table("donor_fields")

    op.drop_index(op.f("ix_uploaded_templates_id"), table_name="uploaded_templates")
    op.drop_table("uploaded_templates")
    sa.Enum(name="uploaded_template_status").drop(bind, checkfirst=True)

    op.drop_index(
        op.f("ix_semantic_field_mappings_raw_value"), table_name="semantic_field_mappings"
    )
    op.drop_index(
        op.f("ix_semantic_field_mappings_normalized_value"), table_name="semantic_field_mappings"
    )
    op.drop_table("semantic_field_mappings")
    sa.Enum(name="mappingsource").drop(bind, checkfirst=True)


def downgrade() -> None:
    op.create_table(
        "semantic_field_mappings",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column(
            "raw_value",
            sa.String(),
            nullable=False,
            comment="Original cell text e.g. 'Office costs'",
        ),
        sa.Column(
            "normalized_value",
            sa.String(),
            nullable=False,
            comment="Normalized form for lookup (lowercase, trimmed)",
        ),
        sa.Column(
            "mapped_to",
            sa.String(),
            nullable=False,
            comment="budget_category | budget_field | extra_field",
        ),
        sa.Column("mapped_key", sa.String(), nullable=False, comment="e.g. 'office_costs'"),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("AI", "HUMAN", "RULE", "IMPORTED", name="mappingsource"),
            nullable=False,
        ),
        sa.Column("times_used", sa.Integer(), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False, comment="Human-confirmed mapping"),
        sa.Column(
            "meta_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="AI reasoning, alternatives, examples",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.Column("updated_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_semantic_field_mappings_normalized_value"),
        "semantic_field_mappings",
        ["normalized_value"],
        unique=False,
    )
    op.create_index(
        op.f("ix_semantic_field_mappings_raw_value"),
        "semantic_field_mappings",
        ["raw_value"],
        unique=False,
    )

    op.create_table(
        "uploaded_templates",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("owner_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("funding_customer_id", shared.db.type_decorators.GUID(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("detected_structure", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.Enum("UPLOADED", "DETECTED", "MAPPED", "CONSUMED", name="uploaded_template_status"),
            server_default=sa.text("'UPLOADED'::uploaded_template_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.Column("updated_by", shared.db.type_decorators.GUID(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_uploaded_templates_id"), "uploaded_templates", ["id"], unique=False)

    op.create_table(
        "donor_fields",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("donor_template_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["donor_template_id"], ["donor_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_donor_fields_donor_template_id"),
        "donor_fields",
        ["donor_template_id"],
        unique=False,
    )
    op.create_index(op.f("ix_donor_fields_id"), "donor_fields", ["id"], unique=False)

    op.create_table(
        "template_budget_mappings",
        sa.Column("id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("uploaded_template_id", shared.db.type_decorators.GUID(), nullable=False),
        sa.Column("mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["uploaded_template_id"],
            ["uploaded_templates.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_template_budget_mappings_id"), "template_budget_mappings", ["id"], unique=False
    )

    op.create_table(
        "ngo_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("owner_field", sa.String(length=255), nullable=False),
        sa.Column("donor_field_id", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["donor_field_id"], ["donor_fields.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ngo_mappings_donor_field_id"), "ngo_mappings", ["donor_field_id"], unique=False
    )
    op.create_index(op.f("ix_ngo_mappings_id"), "ngo_mappings", ["id"], unique=False)
    op.create_index(op.f("ix_ngo_mappings_owner_id"), "ngo_mappings", ["owner_id"], unique=False)
