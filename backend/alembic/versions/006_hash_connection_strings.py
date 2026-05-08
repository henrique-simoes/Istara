"""Store connection-string lookup hashes instead of listing bearer secrets."""

from alembic import op
import sqlalchemy as sa


revision = "006_hash_connection_strings"
down_revision = "005_connection_strings"
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
    if "connection_string_hash" not in _column_names("connection_strings"):
        op.add_column(
            "connection_strings",
            sa.Column("connection_string_hash", sa.String(length=64), nullable=True),
        )
    if not _index_exists("connection_strings", "ix_connection_strings_connection_string_hash"):
        op.create_index(
            "ix_connection_strings_connection_string_hash",
            "connection_strings",
            ["connection_string_hash"],
            unique=True,
        )


def downgrade() -> None:
    if _index_exists("connection_strings", "ix_connection_strings_connection_string_hash"):
        op.drop_index(
            "ix_connection_strings_connection_string_hash",
            table_name="connection_strings",
        )
    if "connection_string_hash" in _column_names("connection_strings"):
        op.drop_column("connection_strings", "connection_string_hash")
