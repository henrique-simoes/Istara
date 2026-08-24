"""task_checkpoints timestamps -> timestamptz (F-P1).

The checkpoint model writes UTC-aware datetimes; the columns were created
TIMESTAMP WITHOUT TIME ZONE, so asyncpg rejected every insert on Postgres
("can't subtract offset-naive and offset-aware datetimes"), breaking all
background agent workers on deployed stacks.

Revision ID: 027_task_checkpoints_tz
Revises: 026_chat_usage_session_scope
"""

from alembic import op

revision = "027_task_checkpoints_tz"
down_revision = "026_chat_usage_session_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TABLE task_checkpoints "
            "ALTER COLUMN created_at TYPE TIMESTAMPTZ, "
            "ALTER COLUMN updated_at TYPE TIMESTAMPTZ"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TABLE task_checkpoints "
            "ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE, "
            "ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE"
        )
