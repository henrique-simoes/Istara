"""add task provenance to atomic findings

Revision ID: 020_finding_task_provenance
Revises: 019_a2a_message_project_scope
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa


revision = "020_finding_task_provenance"
down_revision = "019_a2a_message_project_scope"
branch_labels = None
depends_on = None


FINDING_TABLES = ("nuggets", "facts", "insights", "recommendations")


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def _index_exists(table_name: str, index_name: str) -> bool:
    return any(
        index["name"] == index_name
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    )


def upgrade() -> None:
    for table_name in FINDING_TABLES:
        if not _table_exists(table_name):
            continue
        if not _column_exists(table_name, "task_id"):
            op.add_column(table_name, sa.Column("task_id", sa.String(length=36), nullable=True))
        index_name = op.f(f"ix_{table_name}_task_id")
        if not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, ["task_id"], unique=False)


def downgrade() -> None:
    for table_name in FINDING_TABLES:
        if not _table_exists(table_name):
            continue
        index_name = op.f(f"ix_{table_name}_task_id")
        if _index_exists(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
        if _column_exists(table_name, "task_id"):
            op.drop_column(table_name, "task_id")
