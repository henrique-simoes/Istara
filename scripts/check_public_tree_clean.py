#!/usr/bin/env python3
"""Block personal, runtime, and research-lab artifacts from public commits."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BLOCKED_PREFIXES = (
    "Model_Finetuning/",
    "LLMs/",
    "backend/data/",
    "data/",
    "Istara-Projects/",
    ".qwen/",
)

BLOCKED_SUFFIXES = (
    ".db",
    ".sqlite",
    ".sqlite3",
    ".ogg",
    ".wav",
    ".mp3",
    ".m4a",
    ".mp4",
    ".mov",
    ".jsonl",
    ".safetensors",
    ".gguf",
    ".bin",
    ".pt",
    ".pth",
)

BLOCKED_EXACT = {
    "backend/.env",
    "backend/.env.local",
    "frontend/.env.local",
    ".env",
    ".env.local",
    "current_plans.md",
    "old_plans.md",
    "current_plans_finetune.md",
    "planner_finetune.md",
    "example.md",
}


def run_git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    return result.stdout


def staged_files() -> list[str]:
    return [
        line.strip()
        for line in run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"]).splitlines()
        if line.strip()
    ]


def changed_files(base: str, head: str) -> list[str]:
    return [
        line.strip()
        for line in run_git(["diff", "--name-only", "--diff-filter=ACMR", f"{base}..{head}"]).splitlines()
        if line.strip()
    ]


def path_is_blocked(path: str) -> str | None:
    if path in BLOCKED_EXACT:
        return "local/runtime control file"
    if path.startswith(BLOCKED_PREFIXES):
        return "personal, runtime, model, or local tool directory"
    if path.endswith(BLOCKED_SUFFIXES):
        return "binary/media/database/model/generated dataset artifact"
    if Path(path).name.startswith("audit") and path.endswith("_diff.patch"):
        return "local audit scratch patch"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true", help="check staged files")
    parser.add_argument("--base", help="base ref for branch checks")
    parser.add_argument("--head", default="HEAD", help="head ref for branch checks")
    args = parser.parse_args()

    if args.staged:
        files = staged_files()
    elif args.base:
        files = changed_files(args.base, args.head)
    else:
        parser.error("provide --staged or --base")

    issues: list[str] = []
    for path in files:
        reason = path_is_blocked(path)
        if reason:
            issues.append(f"{path}: {reason}")

    if issues:
        print("Public-tree cleanliness check failed:\n")
        for issue in issues:
            print(f"- {issue}")
        print("\nMove personal/runtime artifacts outside the public repo or keep them ignored.")
        return 1

    print("Public-tree cleanliness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
