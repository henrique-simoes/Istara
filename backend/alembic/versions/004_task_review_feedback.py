"""Add task review feedback state and events."""

from alembic import op
import sqlalchemy as sa


revision = "004_task_review_feedback"
down_revision = "003_add_mfa_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("labels", sa.Text(), nullable=False, server_default="[]"))
    op.add_column("tasks", sa.Column("review_state", sa.String(length=30), nullable=False, server_default="none"))
    op.add_column("tasks", sa.Column("what_to_review", sa.Text(), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("review_cycle_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("tasks", sa.Column("failure_streak", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("tasks", sa.Column("approval_streak", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("tasks", sa.Column("last_review_outcome", sa.String(length=50), nullable=True))
    op.add_column("tasks", sa.Column("last_reviewed_by", sa.String(length=36), nullable=True))
    op.add_column("tasks", sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("last_review_feedback", sa.Text(), nullable=False, server_default=""))
    op.add_column("tasks", sa.Column("next_agent_action", sa.String(length=30), nullable=True))
    op.add_column("tasks", sa.Column("human_feedback_score", sa.Float(), nullable=True))
    op.add_column("tasks", sa.Column("review_severity", sa.String(length=20), nullable=True))
    op.add_column("tasks", sa.Column("review_failure_category", sa.String(length=60), nullable=True))

    op.create_table(
        "task_review_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("skill_name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("model_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("previous_status", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("next_status", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("previous_review_state", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("next_review_state", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("outcome", sa.String(length=50), nullable=False),
        sa.Column("what_to_review", sa.Text(), nullable=False, server_default=""),
        sa.Column("feedback_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("context_snapshot", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("atomic_snapshot", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("validation_method", sa.String(length=50), nullable=True),
        sa.Column("consensus_score", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("failure_category", sa.String(length=60), nullable=True),
        sa.Column("failure_subcategory", sa.String(length=80), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("human_feedback_score", sa.Float(), nullable=True),
        sa.Column("failure_streak_after", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_cycle_after", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trace_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(length=36), nullable=False, server_default="local"),
        sa.Column("diagnosis_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("diagnosis_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_review_events_task_id", "task_review_events", ["task_id"])
    op.create_index("ix_task_review_events_project_id", "task_review_events", ["project_id"])
    op.create_index("ix_task_review_events_outcome", "task_review_events", ["outcome"])


def downgrade() -> None:
    op.drop_index("ix_task_review_events_outcome", table_name="task_review_events")
    op.drop_index("ix_task_review_events_project_id", table_name="task_review_events")
    op.drop_index("ix_task_review_events_task_id", table_name="task_review_events")
    op.drop_table("task_review_events")
    for column in (
        "review_failure_category",
        "review_severity",
        "human_feedback_score",
        "next_agent_action",
        "last_review_feedback",
        "last_reviewed_at",
        "last_reviewed_by",
        "last_review_outcome",
        "approval_streak",
        "failure_streak",
        "review_cycle_count",
        "what_to_review",
        "review_state",
        "labels",
    ):
        op.drop_column("tasks", column)
