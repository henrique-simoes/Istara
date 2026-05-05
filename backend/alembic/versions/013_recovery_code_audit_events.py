"""Add recovery code records and structured audit event type."""

import sqlalchemy as sa

from alembic import op

revision = "013_recovery_code_audit_events"
down_revision = "012_checkpoint_agent_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
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

    op.add_column(
        "audit_log",
        sa.Column("event_type", sa.String(length=80), nullable=False, server_default=""),
    )
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_event_type", table_name="audit_log")
    op.drop_column("audit_log", "event_type")
    op.drop_index("ix_recovery_codes_batch_id", table_name="recovery_codes")
    op.drop_index("ix_recovery_codes_user_id", table_name="recovery_codes")
    op.drop_table("recovery_codes")
