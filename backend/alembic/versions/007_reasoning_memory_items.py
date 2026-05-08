"""Add ReasoningBank memory items."""

from alembic import op
import sqlalchemy as sa


revision = "007_reasoning_memory_items"
down_revision = "006_hash_connection_strings"
branch_labels = None
depends_on = None


INDEXED_COLUMNS = (
    "project_id",
    "agent_id",
    "source_kind",
    "source_id",
    "outcome",
    "domain",
    "status",
)


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    return index_name in {
        item.get("name")
        for item in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def upgrade() -> None:
    table_name = "reasoning_memory_items"
    if not _table_exists(table_name):
        op.create_table(
            table_name,
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False, server_default=""),
            sa.Column("agent_id", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("source_kind", sa.String(length=50), nullable=False, server_default="manual"),
            sa.Column("source_id", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("outcome", sa.String(length=30), nullable=False, server_default="unknown"),
            sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("content", sa.Text(), nullable=False, server_default=""),
            sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("domain", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("evidence_refs_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("judge_score", sa.Float(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    for column in INDEXED_COLUMNS:
        index_name = f"ix_reasoning_memory_items_{column}"
        if not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, [column])


def downgrade() -> None:
    if _table_exists("reasoning_memory_items"):
        op.drop_table("reasoning_memory_items")
