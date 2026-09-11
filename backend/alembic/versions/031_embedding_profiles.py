"""add Pi-owned versioned embedding profiles

Revision ID: 031_embedding_profiles
Revises: 030_telemetry_source_provenance
Create Date: 2026-08-25
"""

import sqlalchemy as sa

from alembic import op

revision = "031_embedding_profiles"
down_revision = "030_telemetry_source_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "embedding_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("endpoint_id", sa.String(length=255), nullable=False),
        sa.Column("transport", sa.String(length=50), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("dtype", sa.String(length=40), nullable=False),
        sa.Column("normalization", sa.String(length=60), nullable=False),
        sa.Column("cache_namespace", sa.String(length=320), nullable=False),
        sa.Column("health_status", sa.String(length=40), nullable=False),
        sa.Column("migration_source", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id", "version", name="uq_embedding_profile_version"
        ),
    )
    op.create_index(
        op.f("ix_embedding_profiles_is_active"),
        "embedding_profiles",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_embedding_profiles_profile_id"),
        "embedding_profiles",
        ["profile_id"],
        unique=False,
    )
    op.create_index(
        "uq_embedding_profiles_single_active",
        "embedding_profiles",
        ["is_active"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
    )


def downgrade() -> None:
    op.drop_index("uq_embedding_profiles_single_active", table_name="embedding_profiles")
    op.drop_index(op.f("ix_embedding_profiles_profile_id"), table_name="embedding_profiles")
    op.drop_index(op.f("ix_embedding_profiles_is_active"), table_name="embedding_profiles")
    op.drop_table("embedding_profiles")
