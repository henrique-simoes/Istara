"""Add connection string audit table."""

from alembic import op
import sqlalchemy as sa


revision = "005_connection_strings"
down_revision = "004_task_review_feedback"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return index_name in {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    if not _table_exists("connection_strings"):
        op.create_table(
            "connection_strings",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("connection_string", sa.String(), nullable=False),
            sa.Column("connection_string_hash", sa.String(length=64), nullable=True),
            sa.Column("token_type", sa.String(), nullable=True, server_default="user_invite"),
            sa.Column("label", sa.String(), nullable=True),
            sa.Column("server_url", sa.String(), nullable=False),
            sa.Column("ws_url", sa.String(), nullable=True, server_default=""),
            sa.Column("intended_role", sa.String(), nullable=True, server_default="researcher"),
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
    else:
        columns = _column_names("connection_strings")
        for column_name, column in (
            ("token_type", sa.Column("token_type", sa.String(), nullable=True, server_default="user_invite")),
            ("ws_url", sa.Column("ws_url", sa.String(), nullable=True, server_default="")),
            (
                "intended_role",
                sa.Column("intended_role", sa.String(), nullable=True, server_default="researcher"),
            ),
        ):
            if column_name not in columns:
                op.add_column("connection_strings", column)
    if not _index_exists("connection_strings", "ix_connection_strings_connection_string"):
        op.create_index(
            "ix_connection_strings_connection_string",
            "connection_strings",
            ["connection_string"],
            unique=True,
        )


def downgrade() -> None:
    if _index_exists("connection_strings", "ix_connection_strings_connection_string"):
        op.drop_index("ix_connection_strings_connection_string", table_name="connection_strings")
    if _table_exists("connection_strings"):
        op.drop_table("connection_strings")
