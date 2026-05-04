"""Add improvement governance proposals."""

from alembic import op
import sqlalchemy as sa


revision = "008_improvement_governance"
down_revision = "007_reasoning_memory_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "improvement_proposals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_system", sa.String(length=60), nullable=False, server_default="manual"),
        sa.Column("source_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("project_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("agent_id", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("affected_surfaces_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("approval_policy", sa.String(length=30), nullable=False, server_default="approval_required"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="proposed"),
        sa.Column("before_state_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("proposed_change_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("rollback_plan_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metrics_before_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("metrics_after_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("evaluation_runs_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("reasoning_memory_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("improvement_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("requires_human_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("auto_apply_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("approved_by", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("applied_by", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("reverted_by", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "source_system",
        "source_id",
        "project_id",
        "agent_id",
        "risk_level",
        "approval_policy",
        "status",
    ):
        op.create_index(
            f"ix_improvement_proposals_{column}",
            "improvement_proposals",
            [column],
        )


def downgrade() -> None:
    op.drop_table("improvement_proposals")
