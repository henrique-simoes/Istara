#!/usr/bin/env python3
"""Validate Istara skill definition JSON files.

The canonical skill source is backend/app/skills/definitions/*.json. This
script verifies that every definition file is parseable JSON and that each
output_schema field is parseable when represented as a JSON string.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS_DIR = REPO_ROOT / "backend" / "app" / "skills" / "definitions"
ALL_SKILLS_FILE = REPO_ROOT / "backend" / "app" / "skills" / "all_skills.py"


@dataclass
class ValidationResult:
    checked: int = 0
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def _schema_is_empty(schema: Any) -> bool:
    return schema is None or schema == "" or schema == {}


def _validate_output_schema(path: Path, data: dict[str, Any], result: ValidationResult) -> None:
    schema = data.get("output_schema")
    if _schema_is_empty(schema):
        return

    if isinstance(schema, str):
        try:
            json.loads(schema)
        except json.JSONDecodeError as exc:
            result.failures.append(f"{path}: output_schema is not valid JSON: {exc}")
        return

    if isinstance(schema, (dict, list)):
        try:
            json.dumps(schema)
        except (TypeError, ValueError) as exc:
            result.failures.append(f"{path}: output_schema is not JSON-serializable: {exc}")
        return

    result.failures.append(
        f"{path}: output_schema must be a JSON string, object, array, or empty value; got {type(schema).__name__}"
    )


def _skill_names_from_all_skills() -> set[str]:
    if not ALL_SKILLS_FILE.exists():
        return set()

    source = ALL_SKILLS_FILE.read_text(encoding="utf-8")
    names: set[str] = set()

    for match in re.finditer(r"skill_name\s*=\s*(['\"])(?P<name>[^'\"]+)\1", source):
        names.add(match.group("name"))

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return names

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "skill_name" and isinstance(keyword.value, ast.Constant):
                    if isinstance(keyword.value.value, str):
                        names.add(keyword.value.value)

    return names


def validate_skill_definitions(
    definitions_dir: Path = DEFINITIONS_DIR,
    warn_on_drift: bool = True,
) -> ValidationResult:
    result = ValidationResult()

    if not definitions_dir.exists():
        result.failures.append(f"{definitions_dir}: definitions directory does not exist")
        return result

    definition_files = sorted(
        path for path in definitions_dir.glob("*.json") if not path.name.startswith("_")
    )
    if not definition_files:
        result.failures.append(f"{definitions_dir}: no skill definition files found")
        return result

    definition_names: set[str] = set()

    for path in definition_files:
        result.checked += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            result.failures.append(f"{path}: invalid JSON file: {exc}")
            continue

        if not isinstance(data, dict):
            result.failures.append(f"{path}: root must be a JSON object")
            continue

        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            result.failures.append(f"{path}: missing non-empty string field 'name'")
        else:
            definition_names.add(name)
            expected = f"{name}.json"
            if path.name != expected:
                result.warnings.append(f"{path}: filename does not match skill name '{name}'")

        _validate_output_schema(path, data, result)

    if warn_on_drift:
        legacy_names = _skill_names_from_all_skills()
        missing = sorted(legacy_names - definition_names)
        if missing:
            result.warnings.append(
                "all_skills.py defines skills missing from definitions/: " + ", ".join(missing)
            )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-drift-warning",
        action="store_true",
        help="Skip warnings about skills present in all_skills.py but missing from definitions/.",
    )
    args = parser.parse_args()

    result = validate_skill_definitions(warn_on_drift=not args.no_drift_warning)

    print(f"Checked {result.checked} skill definition files")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for failure in result.failures:
        print(f"ERROR: {failure}")

    if result.ok:
        print("Skill definition validation passed")
        return 0

    print("Skill definition validation failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
