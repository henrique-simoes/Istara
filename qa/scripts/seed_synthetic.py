"""Synthetic QA corpus seeder (Research Spine provisional-only).

Ingests named canonical corpus slices through the real evidence-unit path so
every synthetic span becomes a real EvidenceUnit row with
``source_kind = synthetic_qa`` — never a bypass of the ingestion contract.
Every seeded artifact is stamped provisional (``is_qa_provisional = true``);
the promotion gate is asserted to never be reachable from synthetic rows.

This module is intentionally importable and deterministic (no network, no
model calls). The actual HTTP ingestion path is a thin, explicit wrapper that
callers (scripts/istara-qa.sh / CI) invoke only against a running QA stack.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slice", required=True, help="canonical corpus slice id")
    parser.add_argument("--run-id", required=True, help="QA run id (istara-qa-<run-id>)")
    parser.add_argument("--runs-dir", default=str(DEFAULT_RUNS_DIR), help="qa/runs root")
    args = parser.parse_args(argv)

    manifest = load_corpora_manifest()
    plan = seed_plan(args.slice, manifest, args.run_id)
    out = write_seed_manifest(plan, Path(args.runs_dir))
    print(json.dumps(plan, indent=2))
    print(f"seed manifest written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
