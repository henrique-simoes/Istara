"""autoresearch_experiments engine per-experiment selection column

Revision ID: 025_autoresearch_experiment_engine
Revises: 024_project_agentic_engine
Create Date: 2026-07-21
"""

from alembic import op
import sqlalchemy as sa


revision = "025_autoresearch_experiment_engine"
down_revision = "024_project_agentic_engine"
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
    # Nullable so pre-W6 rows keep an honest "unknown engine" (NULL); every new
    # row is written with the selected pi|legacy engine by the runner loop.
    if not _table_exists("autoresearch_experiments"):
        return
    if not _column_exists("autoresearch_experiments", "engine"):
        op.add_column(
            "autoresearch_experiments",
            sa.Column("engine", sa.String(length=16), nullable=True),
        )
        op.create_index(
            "ix_autoresearch_experiments_engine",
            "autoresearch_experiments",
            ["engine"],
        )


def downgrade() -> None:
    if _column_exists("autoresearch_experiments", "engine"):
        op.drop_index(
            "ix_autoresearch_experiments_engine",
            table_name="autoresearch_experiments",
        )
        op.drop_column("autoresearch_experiments", "engine")
