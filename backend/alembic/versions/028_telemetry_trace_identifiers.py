"""widen telemetry trace identifiers for namespaced provenance handles

Revision ID: 028_telemetry_trace_identifiers
Revises: 027_task_checkpoints_tz
Create Date: 2026-08-24
"""

import sqlalchemy as sa

from alembic import op

revision = "028_telemetry_trace_identifiers"
down_revision = "027_task_checkpoints_tz"
branch_labels = None
depends_on = None


def _create_telemetry_table_if_missing() -> bool:
    """Reconcile installs where telemetry was created only by ``create_all``."""
    if sa.inspect(op.get_bind()).has_table("telemetry_spans"):
        return False

    op.create_table(
        "telemetry_spans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("trace_id", sa.String(length=120), nullable=False),
        sa.Column("parent_id", sa.String(length=120), nullable=True),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("skill_name", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("consensus_score", sa.Float(), nullable=True),
        sa.Column("reliability_score", sa.Float(), nullable=True),
        sa.Column("error_type", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("event_kind", sa.String(length=80), nullable=False),
        sa.Column("route_id", sa.String(length=120), nullable=False),
        sa.Column("donor_id", sa.String(length=120), nullable=False),
        sa.Column("retrieval_mode", sa.String(length=40), nullable=False),
        sa.Column("coding_run_id", sa.String(length=36), nullable=False),
        sa.Column("evidence_unit_id", sa.String(length=36), nullable=False),
        sa.Column("codebook_version_id", sa.String(length=36), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=True),
        sa.Column("tool_success", sa.Integer(), nullable=True),
        sa.Column("tool_duration_ms", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column_name in (
        "trace_id",
        "operation",
        "skill_name",
        "model_name",
        "project_id",
        "event_kind",
        "route_id",
        "donor_id",
        "coding_run_id",
        "evidence_unit_id",
        "codebook_version_id",
    ):
        op.create_index(
            f"ix_telemetry_spans_{column_name}",
            "telemetry_spans",
            [column_name],
        )
    return True


def upgrade() -> None:
    if _create_telemetry_table_if_missing():
        return
    with op.batch_alter_table("telemetry_spans") as batch_op:
        batch_op.alter_column(
            "trace_id",
            existing_type=sa.String(length=36),
            type_=sa.String(length=120),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "parent_id",
            existing_type=sa.String(length=36),
            type_=sa.String(length=120),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("telemetry_spans") as batch_op:
        batch_op.alter_column(
            "trace_id",
            existing_type=sa.String(length=120),
            type_=sa.String(length=36),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "parent_id",
            existing_type=sa.String(length=120),
            type_=sa.String(length=36),
            existing_nullable=True,
        )
