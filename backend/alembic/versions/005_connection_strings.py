"""Add connection string audit table."""

from alembic import op
import sqlalchemy as sa


revision = "005_connection_strings"
down_revision = "004_task_review_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connection_strings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("connection_string", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("server_url", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("is_redeemed", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("redeemed_by_user_id", sa.String(), nullable=True),
        sa.Column("redeemed_username", sa.String(), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(), nullable=True),
        sa.Column("last_validated_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_connection_strings_connection_string", "connection_strings", ["connection_string"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_connection_strings_connection_string", table_name="connection_strings")
    op.drop_table("connection_strings")
