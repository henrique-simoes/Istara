"""QA synthetic seeder ingestion contract tests (real evidence-unit path).

The seeder's ``--api-base`` mode must drive the REAL documents ingestion route
(POST /api/documents -> persist_document_source_evidence_units) with explicit
QA-provisional provenance, then record live evidence-unit handles in the seed
manifest. These tests use httpx.MockTransport so the wrapper stays hermetic.
"""

from __future__ import annotations

import json

from pathlib import Path

import httpx
import pytest

from qa.scripts.seed_synthetic import (
    PROVISIONAL_METADATA,
    load_corpora_manifest,
    seed_plan,
    write_seed_manifest,
    ingest_slice_via_api,
)

ROOT = Path(__file__).resolve().parent.parent
CORPORA = ROOT / "qa" / "corpora" / "manifest.json"
RUN_ID = "ingest-run-001"
SLICE = "coding-reliability"


def _manifest():
    return load_corpora_manifest(CORPORA)


def _fake_backend_handler(request: httpx.Request) -> httpx.Response:
    """Deterministic fake of the QA backend's real routes."""
    if request.method == "GET" and request.url.path == "/api/projects":
        return httpx.Response(
            200,
            json=[
                {
                    "id": "proj-qa-1",
                    "name": f"qa-synthetic-{SLICE}-{RUN_ID}",
                    "description": "existing",
                }
            ],
        )
    if request.method == "POST" and request.url.path == "/api/projects":
        return httpx.Response(201, json={"id": "proj-qa-1", "name": json.loads(request.content)["name"]})
    if request.method == "POST" and request.url.path == "/api/documents":
        payload = json.loads(request.content)
        # The real documents route would stamp this metadata on every unit.
        assert payload["qa_provisional"] is True
        assert payload["source_kind"] == "synthetic_qa"
        assert payload["project_id"] == "proj-qa-1"
        assert payload["content_text"]
        return httpx.Response(
            201,
            json={
                "id": f"doc-{payload['title']}",
                "project_id": payload["project_id"],
                "title": payload["title"],
                "research_spine": {
                    "artifact_state": "raw_source",
                    "source_evidence_state": "source_evidence_ready",
                    "source_evidence_units": 1,
                    "report_allowed": False,
                },
            },
        )
    if request.method == "GET" and request.url.path.endswith("/evidence-units"):
        project_id = request.url.path.split("/")[-2]
        assert project_id == "proj-qa-1"
        return httpx.Response(
            200,
            json=[
                {
                    "id": f"eu-{i}",
                    "project_id": "proj-qa-1",
                    "source_document_id": f"doc-synthetic-synthetic-coding-00{i}",
                    "source_id": f"document:doc-synthetic-synthetic-coding-00{i}:v1",
                    "stable_id": f"document:doc-synthetic-synthetic-coding-00{i}:v1#EU-0001",
                    "unit_index": 1,
                    "unit_type": "source_span",
                    "metadata": dict(PROVISIONAL_METADATA),
                }
                for i in (1, 2)
            ],
        )
    return httpx.Response(404, json={"detail": "not found"})


def test_ingest_slice_reuses_existing_project_and_returns_handles():
    manifest = _manifest()
    result = ingest_slice_via_api(
        api_base="http://qa-backend:8000",
        run_id=RUN_ID,
        slice_id=SLICE,
        manifest=manifest,
        transport=httpx.MockTransport(_fake_backend_handler),
    )
    assert result["project_id"] == "proj-qa-1"
    assert result["project_name"] == f"qa-synthetic-{SLICE}-{RUN_ID}"
    # two sources in the coding-reliability slice -> two documents
    assert len(result["document_ids"]) == 2
    assert result["evidence_unit_count"] == 2
    assert result["api_base"] == "http://qa-backend:8000"
    assert result["ingested_at"]


def test_ingest_slice_creates_project_when_absent():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/api/projects":
            return httpx.Response(200, json=[])
        if request.method == "POST" and request.url.path == "/api/projects":
            return httpx.Response(201, json={"id": "proj-new", "name": json.loads(request.content)["name"]})
        if request.method == "POST" and request.url.path == "/api/documents":
            return httpx.Response(
                201, json={"id": "doc-1", "project_id": "proj-new", "title": "x"}
            )
        if request.method == "GET" and request.url.path.endswith("/evidence-units"):
            return httpx.Response(200, json=[])
        return httpx.Response(404, json={"detail": "not found"})

    result = ingest_slice_via_api(
        api_base="http://localhost:8000",
        run_id=RUN_ID,
        slice_id=SLICE,
        manifest=_manifest(),
        transport=httpx.MockTransport(handler),
    )
    assert result["project_id"] == "proj-new"
    assert result["evidence_unit_count"] == 0


def test_ingest_slice_fails_closed_on_unknown_slice():
    with pytest.raises(KeyError):
        ingest_slice_via_api(
            api_base="http://localhost:8000",
            run_id=RUN_ID,
            slice_id="nope",
            manifest=_manifest(),
            transport=httpx.MockTransport(_fake_backend_handler),
        )


def test_ingested_manifest_records_live_handles(tmp_path):
    manifest = _manifest()
    plan = seed_plan(SLICE, manifest, RUN_ID)
    plan["ingestion"] = ingest_slice_via_api(
        api_base="http://qa-backend:8000",
        run_id=RUN_ID,
        slice_id=SLICE,
        manifest=manifest,
        transport=httpx.MockTransport(_fake_backend_handler),
    )
    out = write_seed_manifest(plan, tmp_path)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["is_qa_provisional"] is True
    assert loaded["promotion_blocked"] is True
    assert loaded["ingestion"]["project_id"] == "proj-qa-1"
    assert loaded["ingestion"]["evidence_unit_count"] == 2
    assert all(uid.startswith("eu-") for uid in loaded["ingestion"]["evidence_unit_ids"])


def test_offline_plan_mode_has_no_ingestion():
    # Without --api-base the seeder stays hermetic: plan-only, no network.
    plan = seed_plan(SLICE, _manifest(), "offline-run-001")
    assert "ingestion" not in plan
    assert plan["is_qa_provisional"] is True
