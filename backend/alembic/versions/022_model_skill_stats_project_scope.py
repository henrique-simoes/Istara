"""scope model skill statistics by project

Revision ID: 022_model_skill_stats_project_scope
Revises: 021_research_validity_contract
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa


revision = "022_model_skill_stats_project_scope"
down_revision = "021_research_validity_contract"
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


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        index["name"] == index_name
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    )


def upgrade() -> None:
    if not _table_exists("model_skill_stats"):
        return
    if not _column_exists("model_skill_stats", "project_id"):
        op.add_column(
            "model_skill_stats",
            sa.Column("project_id", sa.String(length=36), nullable=False, server_default=""),
        )
    index_name = op.f("ix_model_skill_stats_project_id")
    if not _index_exists("model_skill_stats", index_name):
        op.create_index(index_name, "model_skill_stats", ["project_id"], unique=False)


def downgrade() -> None:
    if not _table_exists("model_skill_stats"):
        return
    index_name = op.f("ix_model_skill_stats_project_id")
    if _index_exists("model_skill_stats", index_name):
        op.drop_index(index_name, table_name="model_skill_stats")
    if _column_exists("model_skill_stats", "project_id"):
        op.drop_column("model_skill_stats", "project_id")
