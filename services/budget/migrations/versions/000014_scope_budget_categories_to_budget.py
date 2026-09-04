"""Scope budget categories to a single owning budget

Revision ID: 000014
Revises: 000013
Create Date: 2026-09-02 00:00:00.000000

"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import shared.db.type_decorators

revision: str = "000014"
down_revision: Union[str, Sequence[str], None] = "000013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column(
        "budget_categories",
        sa.Column("budget_id", shared.db.type_decorators.GUID(), nullable=True),
    )

    # Categories referenced by exactly one distinct budget get that budget_id directly.
    single_budget_rows = bind.execute(sa.text("""
            SELECT category_id, MIN(budget_id::text) AS budget_id
            FROM budget_lines
            WHERE category_id IS NOT NULL
            GROUP BY category_id
            HAVING COUNT(DISTINCT budget_id) = 1
            """)).fetchall()
    for row in single_budget_rows:
        bind.execute(
            sa.text("UPDATE budget_categories SET budget_id = :budget_id WHERE id = :category_id"),
            {"budget_id": str(row.budget_id), "category_id": str(row.category_id)},
        )

    # Multi-budget categories: keep the original on the lowest budget_id, fork the rest.
    multi_budget_rows = bind.execute(sa.text("""
            SELECT DISTINCT category_id, budget_id
            FROM budget_lines
            WHERE category_id IS NOT NULL
            AND category_id IN (
                SELECT category_id
                FROM budget_lines
                WHERE category_id IS NOT NULL
                GROUP BY category_id
                HAVING COUNT(DISTINCT budget_id) > 1
            )
            ORDER BY category_id, budget_id
            """)).fetchall()

    budgets_by_category: dict = {}
    for row in multi_budget_rows:
        budgets_by_category.setdefault(row.category_id, []).append(row.budget_id)

    forked_count = 0
    for category_id, budget_ids in budgets_by_category.items():
        primary_budget_id = min(budget_ids)
        bind.execute(
            sa.text("UPDATE budget_categories SET budget_id = :budget_id WHERE id = :category_id"),
            {"budget_id": str(primary_budget_id), "category_id": str(category_id)},
        )
        source = bind.execute(
            sa.text(
                "SELECT name, code, created_by, updated_by, created_at "
                "FROM budget_categories WHERE id = :category_id"
            ),
            {"category_id": str(category_id)},
        ).fetchone()
        assert source is not None

        for budget_id in budget_ids:
            if budget_id == primary_budget_id:
                continue
            fork_id = str(uuid.uuid4())
            bind.execute(
                sa.text("""
                    INSERT INTO budget_categories
                        (id, name, code, budget_id, created_by, updated_by, created_at)
                    VALUES
                        (:id, :name, :code, :budget_id, :created_by, :updated_by, :created_at)
                    """),
                {
                    "id": fork_id,
                    "name": source.name,
                    "code": source.code,
                    "budget_id": str(budget_id),
                    "created_by": str(source.created_by) if source.created_by else None,
                    "updated_by": str(source.updated_by) if source.updated_by else None,
                    "created_at": source.created_at,
                },
            )
            bind.execute(
                sa.text(
                    "UPDATE budget_lines SET category_id = :fork_id "
                    "WHERE category_id = :category_id AND budget_id = :budget_id"
                ),
                {
                    "fork_id": fork_id,
                    "category_id": str(category_id),
                    "budget_id": str(budget_id),
                },
            )
            forked_count += 1

    # True orphans (zero referencing lines) are dead rows — delete them.
    orphan_result = bind.execute(sa.text("""
            DELETE FROM budget_categories
            WHERE id NOT IN (
                SELECT DISTINCT category_id FROM budget_lines WHERE category_id IS NOT NULL
            )
            """))

    # Merge rows left with the same (budget_id, name) by the pre-migration global dedup race.
    dup_groups = bind.execute(sa.text("""
            SELECT budget_id, name, MIN(id::text) AS keep_id
            FROM budget_categories
            WHERE budget_id IS NOT NULL
            GROUP BY budget_id, name
            HAVING COUNT(*) > 1
            """)).fetchall()

    merged_count = 0
    for dup in dup_groups:
        duplicate_rows = bind.execute(
            sa.text(
                "SELECT id FROM budget_categories "
                "WHERE budget_id = :budget_id AND name = :name AND id != :keep_id"
            ),
            {"budget_id": str(dup.budget_id), "name": dup.name, "keep_id": str(dup.keep_id)},
        ).fetchall()
        for dup_row in duplicate_rows:
            bind.execute(
                sa.text(
                    "UPDATE budget_lines SET category_id = :keep_id WHERE category_id = :dup_id"
                ),
                {"keep_id": str(dup.keep_id), "dup_id": str(dup_row.id)},
            )
            bind.execute(
                sa.text("DELETE FROM budget_categories WHERE id = :dup_id"),
                {"dup_id": str(dup_row.id)},
            )
            merged_count += 1

    print(
        f"budget-category-scoping migration: {len(single_budget_rows)} single-budget rows "
        f"assigned directly, {forked_count} rows forked for multi-budget entanglement, "
        f"{orphan_result.rowcount} orphan rows deleted, {merged_count} duplicate rows merged"
    )

    op.alter_column("budget_categories", "budget_id", nullable=False)
    op.create_foreign_key(
        "budget_categories_budget_id_fkey",
        "budget_categories",
        "budgets",
        ["budget_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_budget_categories_budget_id"), "budget_categories", ["budget_id"])
    op.create_unique_constraint(
        "uq_budget_categories_budget_id_name", "budget_categories", ["budget_id", "name"]
    )

    op.drop_constraint(
        "budget_categories_donor_template_id_fkey", "budget_categories", type_="foreignkey"
    )
    op.drop_column("budget_categories", "donor_template_id")


def downgrade() -> None:
    op.add_column(
        "budget_categories",
        sa.Column("donor_template_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "budget_categories_donor_template_id_fkey",
        "budget_categories",
        "donor_templates",
        ["donor_template_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("uq_budget_categories_budget_id_name", "budget_categories", type_="unique")
    op.drop_index(op.f("ix_budget_categories_budget_id"), table_name="budget_categories")
    op.drop_constraint("budget_categories_budget_id_fkey", "budget_categories", type_="foreignkey")
    op.drop_column("budget_categories", "budget_id")
