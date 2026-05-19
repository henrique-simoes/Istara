"""add project interface configs

Revision ID: 016_project_interface_configs
Revises: 015_permission_requests
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa


revision = "016_project_interface_configs"
down_revision = "015_permission_requests"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    table_name = "project_interface_configs"
    if not _table_exists(table_name):
        op.create_table(
            table_name,
            sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), primary_key=True),
            sa.Column("stitch_api_key_encrypted", sa.Text(), nullable=False, server_default=""),
            sa.Column("figma_api_token_encrypted", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    table_name = "project_interface_configs"
    if _table_exists(table_name):
        op.drop_table(table_name)
