"""Synthetic QA corpus seeder (Research Spine provisional-only).

Ingests named canonical corpus slices through the real evidence-unit path so
every synthetic span becomes a real EvidenceUnit row with
``source_kind = synthetic_qa`` — never a bypass of the ingestion contract.
Every seeded artifact is stamped provisional (``is_qa_provisional = true``);
the promotion gate is asserted to never be reachable from synthetic rows.

The ingestion wrapper posts each raw source span to the QA backend's real
``POST /api/documents`` route (which persists EvidenceUnit rows through
``persist_document_source_evidence_units``), then reads the live evidence-unit
handles back into the seed manifest. The seeder is intentionally deterministic
(no network, no model calls) when ``--api-base`` is omitted — that offline mode
only computes the plan, so unit tests and CI stay hermetic. Callers
(``scripts/istara-qa.sh seed`` / the compose ``qa-seeder`` service / CI) pass
``--api-base`` to ingest against a running QA stack.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
CORPORA_MANIFEST = ROOT / "qa" / "corpora" / "manifest.json"
DEFAULT_RUNS_DIR = ROOT / "qa" / "runs"

# Research Spine promotion gates; synthetic rows may never reach accepted/
# reportable states while is_qa_provisional is true.
PROMOTION_GATES = (
    "accepted",
    "accepted_after_reconciliation",
    "needs_reconciliation",
    "needs_human_review",
    "blocked",
)

SAFE_RUN_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

# Stamped on every EvidenceUnit ingested by the QA seeder (metadata) and on
# the seed manifest. The backend coding-run guard blocks promotion for any
# unit carrying this marker (see run_independent_coding_run).
PROVISIONAL_METADATA = {
    "is_qa_provisional": True,
    "source_kind": "synthetic_qa",
    "promotion_blocked": True,
    "qa_run_boundary": "synthetic_qa_provisional",
}


def load_corpora_manifest(path: Path = CORPORA_MANIFEST) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"corpora manifest missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def span_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def seed_plan(
    slice_id: str,
    manifest: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    """Compute the seed manifest for one corpus slice (deterministic).

    Never ingests anything itself; returns the exact artifact contract that an
    HTTP ingestion wrapper must satisfy, including span hashes and the
    provisional flag that blocks promotion.
    """
    if not SAFE_RUN_ID.match(run_id):
        raise ValueError(f"unsafe run id: {run_id!r}")

    slices = {s.get("slice_id"): s for s in manifest.get("slices", [])}
    if slice_id not in slices:
        raise KeyError(
            f"unknown corpus slice {slice_id!r}; known: {sorted(slices)}"
        )
    slice_info = slices[slice_id]
    sources = slice_info.get("sources", [])
    spans = []
    for source in sources:
        text = source.get("text", "")
        spans.append(
            {
                "source_id": source.get("id"),
                "span_sha256": span_hash(text),
                "kind": source.get("kind", "synthetic_qa"),
                "provenance": source.get("provenance", "generated"),
            }
        )
    return {
        "run_id": run_id,
        "slice_id": slice_id,
        "source_kind": "synthetic_qa",
        "is_qa_provisional": True,
        "promotion_blocked": True,
        "promotion_gates": list(PROMOTION_GATES),
        "span_count": len(spans),
        "spans": spans,
        "artifact": f"qa/runs/{run_id}/seed_manifest.json",
    }


def write_seed_manifest(plan: dict[str, Any], runs_dir: Path = DEFAULT_RUNS_DIR) -> Path:
    run_dir = runs_dir / plan["run_id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / "seed_manifest.json"
    out.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Real evidence-unit ingestion (HTTP wrapper against a running QA stack)
# ---------------------------------------------------------------------------


def _project_name(run_id: str, slice_id: str) -> str:
    return f"qa-synthetic-{slice_id}-{run_id}"


def _find_or_create_project(client: Any, project_name: str, description: str) -> dict[str, Any]:
    """Reuse an existing run-scoped QA project or create it."""
    list_response = client.get("/api/projects")
    list_response.raise_for_status()
    for project in list_response.json() or []:
        if project.get("name") == project_name:
            return project
    create_response = client.post(
        "/api/projects",
        json={"name": project_name, "description": description, "phase": "discover"},
    )
    create_response.raise_for_status()
    return create_response.json()


def _post_synthetic_document(
    client: Any,
    *,
    project_id: str,
    run_id: str,
    slice_id: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    """Post one raw source span through the real documents ingestion route.

    ``qa_provisional``/``source_kind`` are explicit provenance fields on the
    document payload; the backend stamps them onto every EvidenceUnit's
    metadata so synthetic rows can never be promoted.
    """
    source_id = str(source.get("id") or "")
    text = str(source.get("text") or "")
    payload = {
        "project_id": project_id,
        "title": f"synthetic-{source_id}",
        "description": (
            f"Synthetic QA corpus source {source_id} (slice {slice_id}, run {run_id})."
        ),
        "file_name": f"{source_id}.txt",
        "file_type": "txt",
        "tags": ["synthetic-qa", "qa-provisional"],
        "phase": "discover",
        "content_text": text,
        "content_preview": text[:2000],
        "qa_provisional": True,
        "source_kind": source.get("kind", "synthetic_qa"),
    }
    response = client.post("/api/documents", json=payload)
    response.raise_for_status()
    return response.json()


def _list_evidence_units(client: Any, project_id: str) -> list[dict[str, Any]]:
    response = client.get(f"/api/research-validity/{project_id}/evidence-units")
    response.raise_for_status()
    return list(response.json() or [])


def ingest_slice_via_api(
    *,
    api_base: str,
    run_id: str,
    slice_id: str,
    manifest: dict[str, Any],
    timeout: float = 120.0,
    transport: Any = None,
) -> dict[str, Any]:
    """Ingest one canonical slice through the REAL evidence-unit path.

    Creates (or reuses) a run-scoped QA project, POSTs each raw source span
    through the real documents route (which persists EvidenceUnit rows via
    ``persist_document_source_evidence_units``), then reads the live
    evidence-unit handles back for the seed manifest. Every ingested unit is
    stamped provisional (``is_qa_provisional``/``promotion_blocked``) and can
    never reach accepted/reportable states.

    ``transport`` is only used by tests (httpx.MockTransport) to keep the
    wrapper hermetic and importable.
    """
    import httpx

    slices = {s.get("slice_id"): s for s in manifest.get("slices", [])}
    if slice_id not in slices:
        raise KeyError(f"unknown corpus slice {slice_id!r}; known: {sorted(slices)}")
    sources = slices[slice_id].get("sources", [])
    if not sources:
        raise ValueError(f"corpus slice {slice_id!r} has no sources to ingest")

    project_name = _project_name(run_id, slice_id)
    description = (
        f"Disposable QA synthetic corpus project for slice {slice_id} "
        f"(run {run_id}). Provisional-only: no row may become report evidence."
    )
    client_kwargs: dict[str, Any] = {"base_url": api_base.rstrip("/"), "timeout": timeout}
    if transport is not None:
        client_kwargs["transport"] = transport
    with httpx.Client(**client_kwargs) as client:
        project = _find_or_create_project(client, project_name, description)
        project_id = str(project.get("id") or "")
        if not project_id:
            raise RuntimeError("QA project creation returned no project id")

        document_ids: list[str] = []
        for source in sources:
            document = _post_synthetic_document(
                client,
                project_id=project_id,
                run_id=run_id,
                slice_id=slice_id,
                source=source,
            )
            document_ids.append(str(document.get("id") or ""))

        units = _list_evidence_units(client, project_id)
        # Record only THIS run's units (fresh documents per run): re-seeding a
        # run id must never claim units created by an earlier attempt.
        run_units = [
            u
            for u in units
            if str(u.get("source_document_id") or "") in set(document_ids)
        ]

    return {
        "api_base": api_base.rstrip("/"),
        "project_id": project_id,
        "project_name": project_name,
        "document_ids": document_ids,
        "evidence_unit_ids": [str(u.get("id") or "") for u in run_units],
        "evidence_unit_count": len(run_units),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slice", required=True, help="canonical corpus slice id")
    parser.add_argument("--run-id", required=True, help="QA run id (istara-qa-<run-id>)")
    parser.add_argument("--runs-dir", default=str(DEFAULT_RUNS_DIR), help="qa/runs root")
    parser.add_argument(
        "--api-base",
        default=os.environ.get("QA_API_BASE", ""),
        help=(
            "QA backend base URL. When set, ingest the slice through the real "
            "evidence-unit path and record live handles in the manifest."
        ),
    )
    args = parser.parse_args(argv)

    manifest = load_corpora_manifest()
    plan = seed_plan(args.slice, manifest, args.run_id)
    if args.api_base:
        plan["ingestion"] = ingest_slice_via_api(
            api_base=args.api_base,
            run_id=args.run_id,
            slice_id=args.slice,
            manifest=manifest,
        )
    out = write_seed_manifest(plan, Path(args.runs_dir))
    print(json.dumps(plan, indent=2))
    print(f"seed manifest written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
