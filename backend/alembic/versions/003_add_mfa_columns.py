"""
Add MFA columns to users table (TOTP, recovery codes, passkey support).

Revision ID: 003
Revises: 002
Create Date: 2026-04-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("totp_secret", sa.String(64), nullable=True, default=None))
        batch_op.add_column(sa.Column("totp_enabled", sa.Boolean, server_default="0", nullable=False))
        batch_op.add_column(sa.Column("recovery_codes_hashed", sa.Text, nullable=True, default=None))
        batch_op.add_column(sa.Column("passkey_enabled", sa.Boolean, server_default="0", nullable=False))
        # Widen password_hash from 255 to 512 for Argon2id hashes
        batch_op.alter_column(
            "password_hash",
            type_=sa.String(512),
            existing_type=sa.String(255),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("passkey_enabled")
        batch_op.drop_column("recovery_codes_hashed")
        batch_op.drop_column("totp_enabled")
        batch_op.drop_column("totp_secret")
        batch_op.alter_column(
            "password_hash",
            type_=sa.String(255),
            existing_type=sa.String(512),
            existing_nullable=False,
        )
