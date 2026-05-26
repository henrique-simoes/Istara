"""add research validity contract tables and audit handles

Revision ID: 021_research_validity_contract
Revises: 020_finding_task_provenance
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa


revision = "021_research_validity_contract"
down_revision = "020_finding_task_provenance"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(
        index["name"] == index_name
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    )


def _add_column(table_name: str, column: sa.Column) -> None:
    if _table_exists(table_name) and not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def _create_index(table_name: str, column_name: str) -> None:
    index_name = op.f(f"ix_{table_name}_{column_name}")
    if _table_exists(table_name) and not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, [column_name], unique=False)


def upgrade() -> None:
    if not _table_exists("evidence_units"):
        op.create_table(
            "evidence_units",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("task_id", sa.String(length=36), nullable=True),
            sa.Column("source_document_id", sa.String(length=36), nullable=True),
            sa.Column("source_id", sa.String(length=200), nullable=False, server_default=""),
            sa.Column("stable_id", sa.String(length=120), nullable=False),
            sa.Column("unit_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("unit_type", sa.String(length=40), nullable=False, server_default="segment"),
            sa.Column("source_type", sa.String(length=60), nullable=False, server_default="document"),
            sa.Column("method", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("phase", sa.String(length=40), nullable=False, server_default=""),
            sa.Column("participant_id", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("speaker", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("source_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("source_location", sa.String(length=250), nullable=False, server_default=""),
            sa.Column("start_offset", sa.Integer(), nullable=True),
            sa.Column("end_offset", sa.Integer(), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
    for column_name in (
        "project_id",
        "source_document_id",
        "source_id",
        "stable_id",
    ):
        _create_index("evidence_units", column_name)
    _add_column("evidence_units", sa.Column("task_id", sa.String(length=36), nullable=True))
    _create_index("evidence_units", "task_id")

    if not _table_exists("coding_runs"):
        op.create_table(
            "coding_runs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("task_id", sa.String(length=36), nullable=True),
            sa.Column("codebook_version_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
            sa.Column("method", sa.String(length=80), nullable=False, server_default="inductive_multi_model"),
            sa.Column("reliability_method", sa.String(length=60), nullable=False, server_default=""),
            sa.Column("rater_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("distinct_model_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("kappa", sa.Float(), nullable=True),
            sa.Column("alpha", sa.Float(), nullable=True),
            sa.Column("threshold", sa.Float(), nullable=False, server_default="0.60"),
            sa.Column("promotion_status", sa.String(length=40), nullable=False, server_default="blocked"),
            sa.Column("fallback_reason", sa.Text(), nullable=False, server_default=""),
            sa.Column("route_evidence_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("matrix_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("disagreement_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_by", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
    _add_column("coding_runs", sa.Column("task_id", sa.String(length=36), nullable=True))
    for column_name in ("project_id", "task_id", "codebook_version_id"):
        _create_index("coding_runs", column_name)

    if not _table_exists("coding_run_coders"):
        op.create_table(
            "coding_run_coders",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("coding_run_id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("coder_id", sa.String(length=100), nullable=False),
            sa.Column("coder_type", sa.String(length=30), nullable=False, server_default="llm"),
            sa.Column("model_name", sa.String(length=200), nullable=False, server_default=""),
            sa.Column("donor_id", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("route_id", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("route_evidence_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
    for column_name in ("coding_run_id", "project_id"):
        _create_index("coding_run_coders", column_name)

    if not _table_exists("research_evidence_edges"):
        op.create_table(
            "research_evidence_edges",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("source_type", sa.String(length=80), nullable=False),
            sa.Column("source_id", sa.String(length=120), nullable=False),
            sa.Column("relation", sa.String(length=80), nullable=False),
            sa.Column("target_type", sa.String(length=80), nullable=False),
            sa.Column("target_id", sa.String(length=120), nullable=False),
            sa.Column("evidence_unit_id", sa.String(length=36), nullable=True),
            sa.Column("coding_run_id", sa.String(length=36), nullable=True),
            sa.Column("task_id", sa.String(length=36), nullable=True),
            sa.Column("codebook_version_id", sa.String(length=36), nullable=True),
            sa.Column("reliability_status", sa.String(length=40), nullable=False, server_default=""),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
    for column_name in (
        "project_id",
        "source_id",
        "relation",
        "target_id",
        "evidence_unit_id",
        "coding_run_id",
    ):
        _create_index("research_evidence_edges", column_name)
    _add_column("research_evidence_edges", sa.Column("task_id", sa.String(length=36), nullable=True))
    _create_index("research_evidence_edges", "task_id")

    if not _table_exists("reconciliation_decisions"):
        op.create_table(
            "reconciliation_decisions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("task_id", sa.String(length=36), nullable=True),
            sa.Column("coding_run_id", sa.String(length=36), nullable=True),
            sa.Column("evidence_unit_id", sa.String(length=36), nullable=True),
            sa.Column("code_application_id", sa.String(length=36), nullable=True),
            sa.Column("decision_type", sa.String(length=40), nullable=False, server_default="human_review"),
            sa.Column("source", sa.String(length=40), nullable=False, server_default="human_review"),
            sa.Column("accepted_code_id", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
            sa.Column("decided_by", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("previous_state_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("resolved_state_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("route_evidence_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
    for column_name in (
        "project_id",
        "task_id",
        "coding_run_id",
        "evidence_unit_id",
        "code_application_id",
        "decision_type",
    ):
        _create_index("reconciliation_decisions", column_name)

    for column in (
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("evidence_unit_id", sa.String(length=36), nullable=True),
        sa.Column("coding_run_id", sa.String(length=36), nullable=True),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.Column("model_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("donor_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("route_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("route_evidence_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("reliability_status", sa.String(length=40), nullable=False, server_default="unknown"),
        sa.Column("reconciliation_status", sa.String(length=40), nullable=False, server_default="unreconciled"),
        sa.Column("promotion_status", sa.String(length=40), nullable=False, server_default="blocked"),
    ):
        _add_column("code_applications", column)
    for column_name in ("task_id", "evidence_unit_id", "coding_run_id"):
        _create_index("code_applications", column_name)

    for column in (
        sa.Column("event_kind", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("route_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("donor_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("retrieval_mode", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("coding_run_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("evidence_unit_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("codebook_version_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("reliability_score", sa.Float(), nullable=True),
    ):
        _add_column("telemetry_spans", column)
    for column_name in (
        "event_kind",
        "route_id",
        "donor_id",
        "coding_run_id",
        "evidence_unit_id",
        "codebook_version_id",
    ):
        _create_index("telemetry_spans", column_name)


def downgrade() -> None:
    for table_name in (
        "reconciliation_decisions",
        "research_evidence_edges",
        "coding_run_coders",
        "coding_runs",
        "evidence_units",
    ):
        if _table_exists(table_name):
            op.drop_table(table_name)

    for table_name, columns in {
        "code_applications": (
            "promotion_status",
            "reconciliation_status",
            "reliability_status",
            "route_evidence_json",
            "route_id",
            "donor_id",
            "model_name",
            "end_offset",
            "start_offset",
            "coding_run_id",
            "evidence_unit_id",
            "task_id",
        ),
        "telemetry_spans": (
            "reliability_score",
            "codebook_version_id",
            "evidence_unit_id",
            "coding_run_id",
            "retrieval_mode",
            "donor_id",
            "route_id",
            "event_kind",
        ),
    }.items():
        for column_name in columns:
            if _table_exists(table_name) and _column_exists(table_name, column_name):
                op.drop_column(table_name, column_name)
