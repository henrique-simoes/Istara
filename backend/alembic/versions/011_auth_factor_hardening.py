"""Harden auth factors and WebAuthn challenge storage."""

import sqlalchemy as sa

from alembic import op

revision = "011_auth_factor_hardening"
down_revision = "010_auth_sessions"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    return index_name in {
        item.get("name")
        for item in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def _create_webauthn_credentials_table() -> None:
    op.create_table(
        "webauthn_credentials",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("credential_id", sa.String(length=255), nullable=False),
        sa.Column("credential_public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("aaguid", sa.String(length=64), nullable=True),
        sa.Column("transports", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("attestation_object", sa.Text(), nullable=True),
        sa.Column("client_data_json", sa.Text(), nullable=True),
        sa.Column("label", sa.String(length=100), nullable=False, server_default="Passkey"),
        sa.Column("authenticator_type", sa.String(length=50), nullable=True),
        sa.Column("device_type", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("backed_up", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("user_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_used_ip", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("last_used_user_agent", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_webauthn_credentials_credential_id",
        "webauthn_credentials",
        ["credential_id"],
        unique=True,
    )


def upgrade() -> None:
    user_columns = _column_names("users")
    if user_columns:
        with op.batch_alter_table("users") as batch_op:
            if "totp_secret" in user_columns:
                batch_op.alter_column("totp_secret", type_=sa.Text(), existing_nullable=True)
            if "totp_last_accepted_counter" not in user_columns:
                batch_op.add_column(sa.Column("totp_last_accepted_counter", sa.Integer(), nullable=True))
            if "totp_pending_expires_at" not in user_columns:
                batch_op.add_column(
                    sa.Column("totp_pending_expires_at", sa.DateTime(timezone=True), nullable=True),
                )

    if not _table_exists("webauthn_credentials"):
        _create_webauthn_credentials_table()
    else:
        credential_columns = _column_names("webauthn_credentials")
        if not _index_exists(
            "webauthn_credentials",
            "ix_webauthn_credentials_credential_id",
        ):
            op.create_index(
                "ix_webauthn_credentials_credential_id",
                "webauthn_credentials",
                ["credential_id"],
                unique=True,
            )
        if "device_type" not in credential_columns:
            op.add_column(
                "webauthn_credentials",
                sa.Column("device_type", sa.String(length=50), nullable=False, server_default=""),
            )
        if "backed_up" not in credential_columns:
            op.add_column(
                "webauthn_credentials",
                sa.Column("backed_up", sa.Boolean(), nullable=False, server_default=sa.false()),
            )
        if "user_verified" not in credential_columns:
            op.add_column(
                "webauthn_credentials",
                sa.Column("user_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
            )
        if "last_used_ip" not in credential_columns:
            op.add_column(
                "webauthn_credentials",
                sa.Column("last_used_ip", sa.String(length=128), nullable=False, server_default=""),
            )
        if "last_used_user_agent" not in credential_columns:
            op.add_column(
                "webauthn_credentials",
                sa.Column(
                    "last_used_user_agent",
                    sa.String(length=512),
                    nullable=False,
                    server_default="",
                ),
            )

    if not _table_exists("webauthn_challenges"):
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
    if not _index_exists("webauthn_challenges", "ix_webauthn_challenges_user_id"):
        op.create_index("ix_webauthn_challenges_user_id", "webauthn_challenges", ["user_id"])
    if not _index_exists("webauthn_challenges", "ix_webauthn_challenges_purpose"):
        op.create_index("ix_webauthn_challenges_purpose", "webauthn_challenges", ["purpose"])


def downgrade() -> None:
    if _table_exists("webauthn_challenges"):
        if _index_exists("webauthn_challenges", "ix_webauthn_challenges_purpose"):
            op.drop_index("ix_webauthn_challenges_purpose", table_name="webauthn_challenges")
        if _index_exists("webauthn_challenges", "ix_webauthn_challenges_user_id"):
            op.drop_index("ix_webauthn_challenges_user_id", table_name="webauthn_challenges")
        op.drop_table("webauthn_challenges")

    credential_columns = _column_names("webauthn_credentials")
    if credential_columns:
        with op.batch_alter_table("webauthn_credentials") as batch_op:
            for column in (
                "last_used_user_agent",
                "last_used_ip",
                "user_verified",
                "backed_up",
                "device_type",
            ):
                if column in credential_columns:
                    batch_op.drop_column(column)

    user_columns = _column_names("users")
    if user_columns:
        with op.batch_alter_table("users") as batch_op:
            if "totp_pending_expires_at" in user_columns:
                batch_op.drop_column("totp_pending_expires_at")
            if "totp_last_accepted_counter" in user_columns:
                batch_op.drop_column("totp_last_accepted_counter")
            if "totp_secret" in user_columns:
                batch_op.alter_column("totp_secret", type_=sa.String(length=64), existing_nullable=True)
