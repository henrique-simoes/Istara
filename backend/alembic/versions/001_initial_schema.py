"""Initial schema — all tables.

Revision ID: 001
Revises:
Create Date: 2026-03-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Projects
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("phase", sa.String(20), server_default="discover"),
        sa.Column("company_context", sa.Text, server_default=""),
        sa.Column("project_context", sa.Text, server_default=""),
        sa.Column("guardrails", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Tasks
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("status", sa.String(20), server_default="backlog"),
        sa.Column("skill_name", sa.String(100), server_default=""),
        sa.Column("agent_notes", sa.Text, server_default=""),
        sa.Column("user_context", sa.Text, server_default=""),
        sa.Column("progress", sa.Float, server_default="0"),
        sa.Column("position", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Messages
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Nuggets
    op.create_table(
        "nuggets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("source", sa.String(500), nullable=False),
        sa.Column("source_location", sa.String(255), server_default=""),
        sa.Column("tags", sa.Text, server_default=""),
        sa.Column("phase", sa.String(20), server_default="discover"),
        sa.Column("confidence", sa.Float, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Facts
    op.create_table(
        "facts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("nugget_ids", sa.Text, server_default=""),
        sa.Column("phase", sa.String(20), server_default="discover"),
        sa.Column("confidence", sa.Float, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Insights
    op.create_table(
        "insights",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("fact_ids", sa.Text, server_default=""),
        sa.Column("phase", sa.String(20), server_default="define"),
        sa.Column("confidence", sa.Float, server_default="0.5"),
        sa.Column("impact", sa.String(20), server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Recommendations
    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("insight_ids", sa.Text, server_default=""),
        sa.Column("phase", sa.String(20), server_default="deliver"),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("effort", sa.String(20), server_default="medium"),
        sa.Column("status", sa.String(20), server_default="proposed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Indexes for common queries
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_messages_project_id", "messages", ["project_id"])
    op.create_index("ix_nuggets_project_id", "nuggets", ["project_id"])
    op.create_index("ix_nuggets_phase", "nuggets", ["phase"])
    op.create_index("ix_facts_project_id", "facts", ["project_id"])
    op.create_index("ix_insights_project_id", "insights", ["project_id"])
    op.create_index("ix_recommendations_project_id", "recommendations", ["project_id"])


def downgrade() -> None:
    op.drop_table("recommendations")
    op.drop_table("insights")
    op.drop_table("facts")
    op.drop_table("nuggets")
    op.drop_table("messages")
    op.drop_table("tasks")
    op.drop_table("projects")
