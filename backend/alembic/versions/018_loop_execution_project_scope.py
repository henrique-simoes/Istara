"""add project scope to loop executions

Revision ID: 018_loop_execution_project_scope
Revises: 017_mcp_audit_project_scope
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa


revision = "018_loop_execution_project_scope"
down_revision = "017_mcp_audit_project_scope"
branch_labels = None
depends_on = None


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
    table_name = "loop_executions"
    if not _table_exists(table_name):
        return

    if not _column_exists(table_name, "project_id"):
        op.add_column(
            table_name,
            sa.Column(
                "project_id",
                sa.String(length=36),
                nullable=False,
                server_default="",
            ),
        )
    index_name = op.f("ix_loop_executions_project_id")
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, ["project_id"], unique=False)


def downgrade() -> None:
    table_name = "loop_executions"
    if not _table_exists(table_name):
        return

    index_name = op.f("ix_loop_executions_project_id")
    if _index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)
    if _column_exists(table_name, "project_id"):
        op.drop_column(table_name, "project_id")
