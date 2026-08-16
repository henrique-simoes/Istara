#!/usr/bin/env python3
"""No-model validator for the Istara vs Pi comparison run."""

from __future__ import annotations

import gzip
import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPARISON = ROOT.parents[1]
REPO = COMPARISON.parent


FORBIDDEN_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{20,}\b"),
    re.compile(r"\bDEEPSEEK_API_KEY\s*=\s*['\"]?[A-Za-z0-9._~-]{20,}"),
]


ARTICLE_FILES = [
    "outline.md",
    "research-questions.md",
    "systems-under-comparison.md",
    "methodology.md",
    "benchmark-suite.md",
    "metrics-and-statistics.md",
    "results-placeholder.md",
    "qualitative-trace-analysis.md",
    "best-practices-and-migration.md",
    "threats-to-validity.md",
    "reproducibility-appendix.md",
    "review-ledger.md",
]


def load_json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def check_no_secret_text(path: pathlib.Path, failures: list[str]) -> None:
    if path.suffix == ".gz":
        try:
            text = gzip.open(path, "rt", encoding="utf-8").read()
        except Exception as exc:  # pragma: no cover - diagnostic only
            failures.append(f"{path}: cannot read gzip: {exc}")
            return
    else:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            failures.append(f"{path}: forbidden secret-shaped pattern {pattern.pattern!r}")


def main() -> int:
    failures: list[str] = []

    manifest = load_json(ROOT / "manifest.json")
    if manifest["scope"]["istara_application_code_modified"]:
        failures.append("manifest incorrectly marks Istara code as modified")
    if manifest["model_policy"]["local_models_allowed"]:
        failures.append("local models must be disabled")
    if manifest["secret_policy"]["secret_value_logged"]:
        failures.append("secret value must not be logged")

    feature_matrix = load_json(ROOT / "feature-matrix.json")
    inventory = load_json(REPO / "docs/features/inventory.json")
    inventory_ids = {row["id"] for row in inventory["features"]}
    matrix_ids = {row["feature_id"] for row in feature_matrix["features"]}
    missing = sorted(inventory_ids - matrix_ids)
    extra = sorted(matrix_ids - inventory_ids)
    if missing:
        failures.append(f"feature matrix missing {len(missing)} ids: {missing[:8]}")
    if extra:
        failures.append(f"feature matrix has unknown ids: {extra[:8]}")

    for row in feature_matrix["features"]:
        if not row.get("pi_replacement_path"):
            failures.append(f"{row['feature_id']}: missing pi_replacement_path")
        if not row.get("adapter_contract"):
            failures.append(f"{row['feature_id']}: missing adapter_contract")

    article_dir = COMPARISON / "article"
    for name in ARTICLE_FILES:
        if not (article_dir / name).exists():
            failures.append(f"missing article file {name}")

    for path in COMPARISON.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            check_no_secret_text(path, failures)

    result = {
        "validator": "validate_no_model.py",
        "status": "failed" if failures else "passed",
        "feature_count": len(feature_matrix["features"]),
        "article_file_count": len(ARTICLE_FILES),
        "failures": failures,
    }
    (ROOT / "logs" / "no-model-validation.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
