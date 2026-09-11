"""scope agentic usage rows to the active chat session

Revision ID: 026_chat_usage_session_scope
Revises: 025_autoresearch_experiment_engine
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa


revision = "026_chat_usage_session_scope"
down_revision = "025_autoresearch_experiment_engine"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(column["name"] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def upgrade() -> None:
    if _table_exists("chat_sessions") and not _column_exists("chat_sessions", "endpoint_override"):
        op.add_column(
            "chat_sessions",
            sa.Column("endpoint_override", sa.String(length=120), nullable=True),
        )
    if not _table_exists("agentic_usage_rows"):
        return
    if not _column_exists("agentic_usage_rows", "session_id"):
        op.add_column(
            "agentic_usage_rows",
            sa.Column("session_id", sa.String(length=36), nullable=True),
        )
        op.create_index(
            "ix_agentic_usage_rows_session_id",
            "agentic_usage_rows",
            ["session_id"],
        )


def downgrade() -> None:
    if _column_exists("agentic_usage_rows", "session_id"):
        op.drop_index("ix_agentic_usage_rows_session_id", table_name="agentic_usage_rows")
        op.drop_column("agentic_usage_rows", "session_id")
    if _column_exists("chat_sessions", "endpoint_override"):
        op.drop_column("chat_sessions", "endpoint_override")
