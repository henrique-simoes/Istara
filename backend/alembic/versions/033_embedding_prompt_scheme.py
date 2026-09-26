"""embedding profiles record their query/document prompt scheme

Revision ID: 033_embedding_prompt_scheme
Revises: 032_pi_tool_executions
Create Date: 2026-09-26
"""

import sqlalchemy as sa

from alembic import op

revision = "033_embedding_prompt_scheme"
down_revision = "032_pi_tool_executions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing profiles were built from raw text; "raw" keeps their vector space unchanged.
    op.add_column(
        "embedding_profiles",
        sa.Column("prompt_scheme", sa.String(length=40), nullable=False, server_default="raw"),
    )


def downgrade() -> None:
    op.drop_column("embedding_profiles", "prompt_scheme")
