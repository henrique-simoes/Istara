"""make connection string lifecycle timestamps timezone-aware

Revision ID: 029_connection_string_timestamps_tz
Revises: 028_telemetry_trace_identifiers
Create Date: 2026-08-24
"""

import sqlalchemy as sa

from alembic import op

revision = "029_connection_string_timestamps_tz"
down_revision = "028_telemetry_trace_identifiers"
branch_labels = None
depends_on = None

_COLUMNS = ("redeemed_at", "last_validated_at", "expires_at", "created_at")


def upgrade() -> None:
    with op.batch_alter_table("connection_strings") as batch_op:
        for column_name in _COLUMNS:
            batch_op.alter_column(
                column_name,
                existing_type=sa.DateTime(timezone=False),
                type_=sa.DateTime(timezone=True),
                existing_nullable=column_name != "expires_at",
            )


def downgrade() -> None:
    with op.batch_alter_table("connection_strings") as batch_op:
        for column_name in _COLUMNS:
            batch_op.alter_column(
                column_name,
                existing_type=sa.DateTime(timezone=True),
                type_=sa.DateTime(timezone=False),
                existing_nullable=column_name != "expires_at",
            )
