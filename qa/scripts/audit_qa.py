"""QA run auditor: provenance, retention, and redaction evidence.

Produces the ``audit`` Compose profile's report and the sanitized evidence
manifest consumed by the promotion gate. Deterministic and importable:
``audit_run`` returns a report dict; ``main`` wires it to the CLI.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RUNS_DIR = ROOT / "qa" / "runs"
DEFAULT_RETENTION_DAYS = 30  # testing-branch QA artifacts; PR artifacts are 7

# Make repo-root imports work when run as a standalone script.
import sys  # noqa: E402

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def audit_run(
    run_dir: Path,
    *,
    source_sha: str | None = None,
    image_digest: str | None = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> dict[str, Any]:
    """Audit one QA run directory; returns a provenance/redaction report."""
    from qa.scripts.scan_qa_artifacts import scan_run

    redaction = scan_run(run_dir)
    seed_manifest = run_dir / "seed_manifest.json"
    seed = None
    if seed_manifest.exists():
        try:
            seed = json.loads(seed_manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            seed = {"error": "invalid seed manifest"}

    return {
        "run_dir": str(run_dir),
        "source_sha": source_sha,
        "image_digest": image_digest,
        "retention_days": retention_days,
        "provenance": {
            "seed_manifest_present": seed_manifest.exists(),
            "seed": seed,
        },
        "redaction": redaction,
        "audit_pass": redaction["clean"] and seed is not None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-sha", help="exact source SHA")
    parser.add_argument("--image-digest", help="immutable image digest")
    parser.add_argument("--runs-dir", default=str(DEFAULT_RUNS_DIR))
    parser.add_argument("--json-out", help="write report JSON here")
    args = parser.parse_args(argv)

    run_dir = Path(args.runs_dir) / args.run_id
    if not run_dir.exists():
        print(f"no such run directory: {run_dir}")
        return 1
    report = audit_run(
        run_dir,
        source_sha=args.source_sha,
        image_digest=args.image_digest,
    )
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["audit_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
