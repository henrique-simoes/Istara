"""Add ReasoningBank memory items."""

from alembic import op
import sqlalchemy as sa


revision = "007_reasoning_memory_items"
down_revision = "006_hash_connection_strings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reasoning_memory_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("agent_id", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("source_kind", sa.String(length=50), nullable=False, server_default="manual"),
        sa.Column("source_id", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("outcome", sa.String(length=30), nullable=False, server_default="unknown"),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("domain", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("evidence_refs_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("judge_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "project_id",
        "agent_id",
        "source_kind",
        "source_id",
        "outcome",
        "domain",
        "status",
    ):
        op.create_index(
            f"ix_reasoning_memory_items_{column}",
            "reasoning_memory_items",
            [column],
        )


def downgrade() -> None:
    op.drop_table("reasoning_memory_items")
