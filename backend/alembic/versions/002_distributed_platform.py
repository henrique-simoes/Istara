"""Distributed platform — multi-user, task locking, LLM servers, validation.

Revision ID: 002
Revises: 001
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Task locking + validation columns ──
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("locked_by", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("lock_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("validation_method", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("validation_result", sa.Text, nullable=True))
        batch_op.add_column(sa.Column("consensus_score", sa.Float, nullable=True))

    # ── Users table ──
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), server_default="researcher"),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("preferences", sa.Text, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # ── LLM Servers table ──
    op.create_table(
        "llm_servers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider_type", sa.String(50), server_default="openai_compat"),
        sa.Column("host", sa.String(500), nullable=False),
        sa.Column("api_key", sa.String(500), nullable=True),
        sa.Column("is_local", sa.Boolean, server_default="0"),
        sa.Column("is_healthy", sa.Boolean, server_default="1"),
        sa.Column("is_relay", sa.Boolean, server_default="0"),
        sa.Column("priority", sa.Integer, server_default="100"),
        sa.Column("last_health_check", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_latency_ms", sa.Float, nullable=True),
        sa.Column("capabilities", sa.Text, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Method Metrics table ──
    op.create_table(
        "method_metrics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("skill_name", sa.String(100), server_default=""),
        sa.Column("agent_id", sa.String(100), server_default=""),
        sa.Column("method", sa.String(50), nullable=False),
        sa.Column("success_count", sa.Integer, server_default="0"),
        sa.Column("fail_count", sa.Integer, server_default="0"),
        sa.Column("avg_consensus_score", sa.Float, server_default="0.0"),
        sa.Column("total_runs", sa.Integer, server_default="0"),
        sa.Column("weight", sa.Float, server_default="1.0"),
        sa.Column("last_used", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_method_metrics_project_id", "method_metrics", ["project_id"])
    op.create_index("ix_method_metrics_method", "method_metrics", ["method"])


def downgrade() -> None:
    op.drop_table("method_metrics")
    op.drop_table("llm_servers")
    op.drop_table("users")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("consensus_score")
        batch_op.drop_column("validation_result")
        batch_op.drop_column("validation_method")
        batch_op.drop_column("lock_expires_at")
        batch_op.drop_column("locked_at")
        batch_op.drop_column("locked_by")
