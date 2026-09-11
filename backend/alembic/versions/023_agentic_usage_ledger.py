"""agentic usage ledger table

Revision ID: 023_agentic_usage_ledger
Revises: 022_model_skill_stats_project_scope
Create Date: 2026-07-20
"""

import sqlalchemy as sa

from alembic import op

revision = "023_agentic_usage_ledger"
down_revision = "022_model_skill_stats_project_scope"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _table_exists("agentic_usage_rows"):
        return
    op.create_table(
        "agentic_usage_rows",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("engine", sa.String(length=16), nullable=False),
        sa.Column("purpose", sa.String(length=120), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("agent_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("spine_phase", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("endpoint_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("node_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("model", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_write", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tool_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("turns", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("stop_reason", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("outcome", sa.String(length=20), nullable=False, server_default="success"),
        sa.Column("estimate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_type", sa.String(length=80), nullable=False, server_default=""),
    )
    op.create_index(op.f("ix_agentic_usage_rows_created_at"), "agentic_usage_rows", ["created_at"])
    op.create_index(op.f("ix_agentic_usage_rows_engine"), "agentic_usage_rows", ["engine"])
    op.create_index(op.f("ix_agentic_usage_rows_purpose"), "agentic_usage_rows", ["purpose"])
    op.create_index(op.f("ix_agentic_usage_rows_project_id"), "agentic_usage_rows", ["project_id"])
    op.create_index(op.f("ix_agentic_usage_rows_task_id"), "agentic_usage_rows", ["task_id"])
    op.create_index(op.f("ix_agentic_usage_rows_model"), "agentic_usage_rows", ["model"])
    op.create_index(op.f("ix_agentic_usage_rows_outcome"), "agentic_usage_rows", ["outcome"])


def downgrade() -> None:
    if not _table_exists("agentic_usage_rows"):
        return
    for index_name in (
        "ix_agentic_usage_rows_outcome",
        "ix_agentic_usage_rows_model",
        "ix_agentic_usage_rows_task_id",
        "ix_agentic_usage_rows_project_id",
        "ix_agentic_usage_rows_purpose",
        "ix_agentic_usage_rows_engine",
        "ix_agentic_usage_rows_created_at",
    ):
        op.drop_index(index_name, table_name="agentic_usage_rows")
    op.drop_table("agentic_usage_rows")
