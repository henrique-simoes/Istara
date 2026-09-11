"""widen telemetry source provenance identifiers

Revision ID: 030_telemetry_source_provenance
Revises: 029_connection_string_timestamps_tz
Create Date: 2026-08-24
"""

import sqlalchemy as sa

from alembic import op

revision = "030_telemetry_source_provenance"
down_revision = "029_connection_string_timestamps_tz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("telemetry_spans") as batch_op:
        batch_op.alter_column(
            "source",
            existing_type=sa.String(length=20),
            type_=sa.String(length=40),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("telemetry_spans") as batch_op:
        batch_op.alter_column(
            "source",
            existing_type=sa.String(length=40),
            type_=sa.String(length=20),
            existing_nullable=False,
        )
