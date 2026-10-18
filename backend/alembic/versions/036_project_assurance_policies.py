"""project assurance modes and human-verified validation outcomes

Revision ID: 036_project_assurance_policies
Revises: 035_decision_trajectories
Create Date: 2026-10-18
"""

import sqlalchemy as sa

from alembic import op

revision = "036_project_assurance_policies"
down_revision = "035_decision_trajectories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No row means "auto": validation behaves exactly as before assurance modes existed.
    op.create_table(
        "project_assurance_policies",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="auto"),
        sa.Column("llm_method", sa.String(length=30), nullable=False, server_default="auto"),
        sa.Column("llm_judges", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("decider_endpoint_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("updated_by", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("project_id"),
    )
    # Validation methods learn only from outcomes a researcher verified (AV-1).
    with op.batch_alter_table("method_metrics") as batch:
        batch.add_column(
            sa.Column("human_agree_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("human_disagree_count", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("method_metrics") as batch:
        batch.drop_column("human_disagree_count")
        batch.drop_column("human_agree_count")
    op.drop_table("project_assurance_policies")
