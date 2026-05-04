"""Add DGM-H archive variants."""

from alembic import op
import sqlalchemy as sa


revision = "009_dgmh_archive"
down_revision = "008_improvement_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dgmh_archive_variants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("parent_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("root_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_system", sa.String(length=60), nullable=False, server_default="manual"),
        sa.Column("source_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("project_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("agent_id", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("governance_proposal_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("target_system", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("mutation_kind", sa.String(length=80), nullable=False, server_default="proposal"),
        sa.Column("mutation_surface", sa.String(length=80), nullable=False, server_default="evaluation"),
        sa.Column("artifact_kind", sa.String(length=80), nullable=False, server_default="evidence_trace"),
        sa.Column("artifact_ref", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="candidate"),
        sa.Column("lineage_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("mutation_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("rollback_plan_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metrics_before_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("metrics_after_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("evaluation_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("reasoning_memory_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("ucb_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "parent_id",
        "root_id",
        "generation",
        "source_system",
        "source_id",
        "project_id",
        "agent_id",
        "governance_proposal_id",
        "target_system",
        "mutation_kind",
        "mutation_surface",
        "artifact_kind",
        "status",
    ):
        op.create_index(f"ix_dgmh_archive_variants_{column}", "dgmh_archive_variants", [column])


def downgrade() -> None:
    op.drop_table("dgmh_archive_variants")
