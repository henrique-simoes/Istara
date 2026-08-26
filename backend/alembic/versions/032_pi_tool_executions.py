"""add durable Pi authority tool execution ledger

Revision ID: 032_pi_tool_executions
Revises: 031_embedding_profiles
Create Date: 2026-08-26
"""

import sqlalchemy as sa

from alembic import op

revision = "032_pi_tool_executions"
down_revision = "031_embedding_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pi_tool_executions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("args_hash", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("worker_session_key", sa.String(length=255), nullable=False),
        sa.Column("run_id", sa.String(length=100), nullable=False),
        sa.Column("tool_call_id", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_pi_tool_execution_project_key",
        ),
    )
    op.create_index(
        op.f("ix_pi_tool_executions_project_id"),
        "pi_tool_executions",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pi_tool_executions_status"),
        "pi_tool_executions",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_pi_tool_executions_status"), table_name="pi_tool_executions")
    op.drop_index(op.f("ix_pi_tool_executions_project_id"), table_name="pi_tool_executions")
    op.drop_table("pi_tool_executions")
