"""Add revocable auth sessions."""

import sqlalchemy as sa

from alembic import op

revision = "010_auth_sessions"
down_revision = "009_dgmh_archive"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    return index_name in {
        item.get("name")
        for item in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def upgrade() -> None:
    table_name = "auth_sessions"
    if not _table_exists(table_name):
        op.create_table(
            table_name,
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("token_jti", sa.String(length=64), nullable=False),
            sa.Column("auth_method", sa.String(length=40), nullable=False, server_default="password"),
            sa.Column("mfa_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("ip_address", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("user_agent", sa.String(length=512), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists(table_name, "ix_auth_sessions_user_id"):
        op.create_index("ix_auth_sessions_user_id", table_name, ["user_id"])
    if not _index_exists(table_name, "ix_auth_sessions_token_jti"):
        op.create_index("ix_auth_sessions_token_jti", table_name, ["token_jti"], unique=True)


def downgrade() -> None:
    if _table_exists("auth_sessions"):
        if _index_exists("auth_sessions", "ix_auth_sessions_token_jti"):
            op.drop_index("ix_auth_sessions_token_jti", table_name="auth_sessions")
        if _index_exists("auth_sessions", "ix_auth_sessions_user_id"):
            op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
        op.drop_table("auth_sessions")
