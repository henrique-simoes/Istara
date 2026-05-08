"""Add task review feedback state and events."""

from alembic import op
import sqlalchemy as sa


revision = "004_task_review_feedback"
down_revision = "003"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    task_columns = _column_names("tasks")
    for column_name, column in (
        ("labels", sa.Column("labels", sa.Text(), nullable=False, server_default="[]")),
        (
            "review_state",
            sa.Column(
                "review_state",
                sa.String(length=30),
                nullable=False,
                server_default="none",
            ),
        ),
        ("what_to_review", sa.Column("what_to_review", sa.Text(), nullable=False, server_default="")),
        (
            "review_cycle_count",
            sa.Column("review_cycle_count", sa.Integer(), nullable=False, server_default="0"),
        ),
        ("failure_streak", sa.Column("failure_streak", sa.Integer(), nullable=False, server_default="0")),
        ("approval_streak", sa.Column("approval_streak", sa.Integer(), nullable=False, server_default="0")),
        ("last_review_outcome", sa.Column("last_review_outcome", sa.String(length=50), nullable=True)),
        ("last_reviewed_by", sa.Column("last_reviewed_by", sa.String(length=36), nullable=True)),
        ("last_reviewed_at", sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True)),
        (
            "last_review_feedback",
            sa.Column("last_review_feedback", sa.Text(), nullable=False, server_default=""),
        ),
        ("next_agent_action", sa.Column("next_agent_action", sa.String(length=30), nullable=True)),
        ("human_feedback_score", sa.Column("human_feedback_score", sa.Float(), nullable=True)),
        ("review_severity", sa.Column("review_severity", sa.String(length=20), nullable=True)),
        (
            "review_failure_category",
            sa.Column("review_failure_category", sa.String(length=60), nullable=True),
        ),
    ):
        if column_name not in task_columns:
            op.add_column("tasks", column)

    if not _table_exists("task_review_events"):
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
    if _table_exists("task_review_events"):
        op.drop_index("ix_task_review_events_outcome", table_name="task_review_events")
        op.drop_index("ix_task_review_events_project_id", table_name="task_review_events")
        op.drop_index("ix_task_review_events_task_id", table_name="task_review_events")
        op.drop_table("task_review_events")
    task_columns = _column_names("tasks")
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
        if column in task_columns:
            op.drop_column("tasks", column)
