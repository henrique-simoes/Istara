"""Add agent state to task checkpoints."""

import sqlalchemy as sa

from alembic import op

revision = "012_checkpoint_agent_state"
down_revision = "011_auth_factor_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "task_checkpoints",
        sa.Column("agent_state", sa.String(length=20), nullable=False, server_default="idle"),
    )


def downgrade() -> None:
    op.drop_column("task_checkpoints", "agent_state")
