"""Store connection-string lookup hashes instead of listing bearer secrets."""

from alembic import op
import sqlalchemy as sa


revision = "006_hash_connection_strings"
down_revision = "005_connection_strings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "connection_strings",
        sa.Column("connection_string_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_connection_strings_connection_string_hash",
        "connection_strings",
        ["connection_string_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_connection_strings_connection_string_hash",
        table_name="connection_strings",
    )
    op.drop_column("connection_strings", "connection_string_hash")
