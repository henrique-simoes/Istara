"""Add recovery code records and structured audit event type."""

import sqlalchemy as sa

from alembic import op

revision = "013_recovery_code_audit_events"
down_revision = "012_checkpoint_agent_state"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return index_name in {
        item.get("name")
        for item in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def _create_audit_log_table() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=True, server_default=""),
        sa.Column("method", sa.String(length=10), nullable=True, server_default=""),
        sa.Column("path", sa.String(length=500), nullable=True, server_default=""),
        sa.Column("status_code", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("duration_ms", sa.Float(), nullable=True, server_default="0"),
        sa.Column("ip_address", sa.String(length=45), nullable=True, server_default=""),
        sa.Column("user_agent", sa.String(length=500), nullable=True, server_default=""),
        sa.Column("request_body_hash", sa.String(length=64), nullable=True, server_default=""),
        sa.Column("project_id", sa.String(length=36), nullable=True, server_default=""),
        sa.Column("event_type", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("details", sa.Text(), nullable=True, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_path", "audit_log", ["path"])
    op.create_index("ix_audit_log_project_id", "audit_log", ["project_id"])
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])


def upgrade() -> None:
    if not _table_exists("recovery_codes"):
        op.create_table(
            "recovery_codes",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("code_hash", sa.Text(), nullable=False),
            sa.Column("batch_id", sa.String(length=36), nullable=False),
            sa.Column("created_by_user_id", sa.String(length=36), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("replaced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("used_ip_hash", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("used_user_agent_hash", sa.String(length=64), nullable=False, server_default=""),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_recovery_codes_user_id", "recovery_codes", ["user_id"])
        op.create_index("ix_recovery_codes_batch_id", "recovery_codes", ["batch_id"])
    else:
        if not _index_exists("recovery_codes", "ix_recovery_codes_user_id"):
            op.create_index("ix_recovery_codes_user_id", "recovery_codes", ["user_id"])
        if not _index_exists("recovery_codes", "ix_recovery_codes_batch_id"):
            op.create_index("ix_recovery_codes_batch_id", "recovery_codes", ["batch_id"])

    if not _table_exists("audit_log"):
        _create_audit_log_table()
    elif "event_type" not in _column_names("audit_log"):
        op.add_column(
            "audit_log",
            sa.Column("event_type", sa.String(length=80), nullable=False, server_default=""),
        )
        if not _index_exists("audit_log", "ix_audit_log_event_type"):
            op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])
    elif not _index_exists("audit_log", "ix_audit_log_event_type"):
        op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])


def downgrade() -> None:
    if "event_type" in _column_names("audit_log"):
        if _index_exists("audit_log", "ix_audit_log_event_type"):
            op.drop_index("ix_audit_log_event_type", table_name="audit_log")
        op.drop_column("audit_log", "event_type")
    if _table_exists("recovery_codes"):
        if _index_exists("recovery_codes", "ix_recovery_codes_batch_id"):
            op.drop_index("ix_recovery_codes_batch_id", table_name="recovery_codes")
        if _index_exists("recovery_codes", "ix_recovery_codes_user_id"):
            op.drop_index("ix_recovery_codes_user_id", table_name="recovery_codes")
        op.drop_table("recovery_codes")
