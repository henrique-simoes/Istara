"""Harden auth factors and WebAuthn challenge storage."""

import sqlalchemy as sa

from alembic import op

revision = "011_auth_factor_hardening"
down_revision = "010_auth_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "totp_secret", type_=sa.Text(), existing_nullable=True)
    op.add_column("users", sa.Column("totp_last_accepted_counter", sa.Integer(), nullable=True))
    op.add_column(
        "users",
        sa.Column("totp_pending_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "webauthn_credentials",
        sa.Column("device_type", sa.String(length=50), nullable=False, server_default=""),
    )
    op.add_column(
        "webauthn_credentials",
        sa.Column("backed_up", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "webauthn_credentials",
        sa.Column("user_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "webauthn_credentials",
        sa.Column("last_used_ip", sa.String(length=128), nullable=False, server_default=""),
    )
    op.add_column(
        "webauthn_credentials",
        sa.Column("last_used_user_agent", sa.String(length=512), nullable=False, server_default=""),
    )

    op.create_table(
        "webauthn_challenges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("challenge", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webauthn_challenges_user_id", "webauthn_challenges", ["user_id"])
    op.create_index("ix_webauthn_challenges_purpose", "webauthn_challenges", ["purpose"])


def downgrade() -> None:
    op.drop_index("ix_webauthn_challenges_purpose", table_name="webauthn_challenges")
    op.drop_index("ix_webauthn_challenges_user_id", table_name="webauthn_challenges")
    op.drop_table("webauthn_challenges")

    op.drop_column("webauthn_credentials", "last_used_user_agent")
    op.drop_column("webauthn_credentials", "last_used_ip")
    op.drop_column("webauthn_credentials", "user_verified")
    op.drop_column("webauthn_credentials", "backed_up")
    op.drop_column("webauthn_credentials", "device_type")

    op.drop_column("users", "totp_pending_expires_at")
    op.drop_column("users", "totp_last_accepted_counter")
    op.alter_column("users", "totp_secret", type_=sa.String(length=64), existing_nullable=True)
