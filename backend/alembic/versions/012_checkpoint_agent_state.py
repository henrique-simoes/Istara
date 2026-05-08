"""Add agent state to task checkpoints."""

import sqlalchemy as sa

from alembic import op

revision = "012_checkpoint_agent_state"
down_revision = "011_auth_factor_hardening"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if not _table_exists("task_checkpoints"):
        op.create_table(
            "task_checkpoints",
            sa.Column("task_id", sa.String(length=100), nullable=False),
            sa.Column("agent_id", sa.String(length=100), nullable=False),
            sa.Column("phase", sa.String(length=50), nullable=False),
            sa.Column("checkpoint_data", sa.Text(), nullable=True, server_default="{}"),
            sa.Column("agent_state", sa.String(length=20), nullable=False, server_default="idle"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("task_id"),
        )
        return

    if "agent_state" not in _column_names("task_checkpoints"):
        op.add_column(
            "task_checkpoints",
            sa.Column("agent_state", sa.String(length=20), nullable=False, server_default="idle"),
        )


def downgrade() -> None:
    if "agent_state" in _column_names("task_checkpoints"):
        op.drop_column("task_checkpoints", "agent_state")
