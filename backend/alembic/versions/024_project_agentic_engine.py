"""project agentic_engine engine-selection column

Revision ID: 024_project_agentic_engine
Revises: 023_agentic_usage_ledger
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa


revision = "024_project_agentic_engine"
down_revision = "023_agentic_usage_ledger"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def upgrade() -> None:
    if not _table_exists("projects"):
        return
    if not _column_exists("projects", "agentic_engine"):
        op.add_column("projects", sa.Column("agentic_engine", sa.String(length=32), nullable=True))


def downgrade() -> None:
    if _column_exists("projects", "agentic_engine"):
        op.drop_column("projects", "agentic_engine")
