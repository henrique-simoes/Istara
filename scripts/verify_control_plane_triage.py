#!/usr/bin/env python3
"""Fail closed when current promotion prerequisites are labeled non-blocking."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

DEFAULT_TRIAGE = Path("docs/promotion/2026-09-09-control-plane-triage.tsv")


def verify(path: Path, *, spec: str, pipeline_run: str, current_review: str) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    errors: list[str] = []
    by_id = {row["public_id"]: row for row in rows}
    acceptance_rows = [
        row for row in rows if row["spec"] == spec and row["kind"] == "spec_requirement"
    ]
    if not acceptance_rows:
        errors.append(f"no acceptance children found for {spec}")
    for row in acceptance_rows:
        if row["bucket"] != "acceptance-prerequisite":
            errors.append(
                f"{row['public_id']}: current-spec acceptance child must be "
                f"acceptance-prerequisite, got {row['bucket']}"
            )

    review = by_id.get(current_review)
    if review is None:
        errors.append(f"missing current-wave review row {current_review}")
    elif not review["public_id"].startswith(f"{pipeline_run}-WAVE-"):
        errors.append(f"{current_review}: does not belong to pipeline {pipeline_run}")
    elif review["bucket"] != "promotion-prerequisite":
        errors.append(
            f"{current_review}: mandatory current-wave review must be "
            f"promotion-prerequisite, got {review['bucket']}"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--triage", type=Path, default=DEFAULT_TRIAGE)
    parser.add_argument("--spec", default="CF-SPEC-30")
    parser.add_argument("--pipeline-run", default="testing-to-main-20260909")
    parser.add_argument(
        "--current-review",
        default="testing-to-main-20260909-WAVE-control-plane-lifecycle-REVIEW",
    )
    args = parser.parse_args()
    errors = verify(
        args.triage,
        spec=args.spec,
        pipeline_run=args.pipeline_run,
        current_review=args.current_review,
    )
    if errors:
        print("FAIL: control-plane triage invariant")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("OK: current-spec acceptance and current-wave review prerequisites are stage-aware")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
