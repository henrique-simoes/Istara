"""add permission requests

Revision ID: 015_permission_requests
Revises: 014_chat_session_thinking_mode
Create Date: 2026-05-06
"""

from alembic import op
import sqlalchemy as sa


revision = "015_permission_requests"
down_revision = "014_chat_session_thinking_mode"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return index_name in {
        item.get("name")
        for item in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


INDEXES = (
    ("ix_permission_requests_project_id", ["project_id"]),
    ("ix_permission_requests_requester_user_id", ["requester_user_id"]),
    ("ix_permission_requests_action", ["action"]),
    ("ix_permission_requests_status", ["status"]),
)


def upgrade() -> None:
    table_name = "permission_requests"
    if not _table_exists(table_name):
        op.create_table(
            table_name,
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("requester_user_id", sa.String(length=36), nullable=False),
            sa.Column("requester_username", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("action", sa.String(length=120), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("details", sa.Text(), nullable=False, server_default=""),
            sa.Column("payload_summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("reviewer_user_id", sa.String(length=36), nullable=False, server_default=""),
            sa.Column("reviewer_username", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("review_note", sa.Text(), nullable=False, server_default=""),
            sa.Column("history_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        )

    for index_name, columns in INDEXES:
        if not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    table_name = "permission_requests"
    if _table_exists(table_name):
        for index_name, _columns in reversed(INDEXES):
            if _index_exists(table_name, index_name):
                op.drop_index(index_name, table_name=table_name)
        op.drop_table(table_name)
