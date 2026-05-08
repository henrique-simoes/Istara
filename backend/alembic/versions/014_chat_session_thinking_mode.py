"""Add chat session thinking mode."""

import sqlalchemy as sa

from alembic import op

revision = "014_chat_session_thinking_mode"
down_revision = "013_recovery_code_audit_events"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if not _table_exists("chat_sessions"):
        op.create_table(
            "chat_sessions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True, server_default="New Chat"),
            sa.Column("agent_id", sa.String(length=36), nullable=True),
            sa.Column("model_override", sa.String(length=255), nullable=True),
            sa.Column("inference_preset", sa.String(length=20), nullable=True, server_default="medium"),
            sa.Column("custom_temperature", sa.Float(), nullable=True),
            sa.Column("custom_max_tokens", sa.Integer(), nullable=True),
            sa.Column("custom_context_window", sa.Integer(), nullable=True),
            sa.Column(
                "thinking_mode",
                sa.String(length=20),
                nullable=False,
                server_default="server_default",
            ),
            sa.Column("session_type", sa.String(length=20), nullable=True, server_default="chat"),
            sa.Column("starred", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.Column("archived", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.Column("message_count", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        return

    if "thinking_mode" not in _column_names("chat_sessions"):
        op.add_column(
            "chat_sessions",
            sa.Column(
                "thinking_mode",
                sa.String(length=20),
                nullable=False,
                server_default="server_default",
            ),
        )


def downgrade() -> None:
    if "thinking_mode" in _column_names("chat_sessions"):
        op.drop_column("chat_sessions", "thinking_mode")
