"""per-project opt-in for hosted decision-model egress

Revision ID: 034_decision_model_project_policies
Revises: 033_embedding_prompt_scheme
Create Date: 2026-10-17
"""

import sqlalchemy as sa

from alembic import op

revision = "034_decision_model_project_policies"
down_revision = "033_embedding_prompt_scheme"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No row means a project sends nothing to hosted decision models (owner decision DEC-1).
    op.create_table(
        "decision_model_project_policies",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column(
            "hosted_egress_endpoint_ids_json", sa.Text(), nullable=False, server_default="[]"
        ),
        sa.Column("updated_by", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("project_id"),
    )


def downgrade() -> None:
    op.drop_table("decision_model_project_policies")
