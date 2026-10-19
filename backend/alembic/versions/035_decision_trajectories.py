"""decision trajectories and decider trust evaluations

Revision ID: 035_decision_trajectories
Revises: 034_decision_model_project_policies
Create Date: 2026-10-18
"""

import sqlalchemy as sa

from alembic import op

revision = "035_decision_trajectories"
down_revision = "034_decision_model_project_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Content-free: handles, model identities and numbers only (Research Spine telemetry contract).
    op.create_table(
        "decision_trajectories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("subject_kind", sa.String(length=40), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("coding_run_id", sa.String(length=36), nullable=True),
        sa.Column("evidence_unit_id", sa.String(length=36), nullable=True),
        sa.Column("endpoint_id", sa.String(length=100), nullable=False),
        sa.Column("requested_model", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("served_model", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("alias_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("question_set_id", sa.String(length=100), nullable=False),
        sa.Column("question_set_version", sa.String(length=40), nullable=False),
        sa.Column("question_id", sa.String(length=100), nullable=False),
        sa.Column("task_family", sa.String(length=60), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("scope_key", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("raw_distribution_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("calibrated_distribution_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("positive_outcomes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("tau", sa.Float(), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False, server_default="shadow"),
        sa.Column("routed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("order_flip_agree", sa.Boolean(), nullable=True),
        sa.Column("audit_sampled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("audit_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("audit_blind", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("label_mapping_version", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("human_label", sa.Integer(), nullable=True),
        sa.Column("label_decision_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("labelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("project_id", "subject_id", "scope_key"):
        op.create_index(
            op.f(f"ix_decision_trajectories_{column}"), "decision_trajectories", [column]
        )
    op.create_table(
        "decision_trust_evaluations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("scope_key", sa.String(length=32), nullable=False),
        sa.Column("trusted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metrics_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("policy_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("labelled_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_decision_trust_evaluations_scope_key"), "decision_trust_evaluations", ["scope_key"]
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_decision_trust_evaluations_scope_key"), table_name="decision_trust_evaluations"
    )
    op.drop_table("decision_trust_evaluations")
    for column in ("project_id", "subject_id", "scope_key"):
        op.drop_index(op.f(f"ix_decision_trajectories_{column}"), table_name="decision_trajectories")
    op.drop_table("decision_trajectories")
