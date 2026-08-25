#!/usr/bin/env python3
"""Guard against generated-looking public artifacts in the Istara repo."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SOURCES = REPO_ROOT / "tests" / "document_corpus" / "canonical" / "sources"

EXCLUDED_DIR_NAMES = {
    ".compass-forge",
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".vscode",
    ".venv",
    "LLMs",
    "Model_Finetuning",
    "artifacts",
    "backups",
    "cache",
    "data",
    "dist",
    "logs",
    "node_modules",
    "storage",
    "target",
    "tmp",
    "uploads",
}

EXCLUDED_FILE_NAMES = {
    ".mcp.json",
    "opencode.json",
}

EXCLUDED_PARTS = {
    ("tests", "pi_benchmark", "scenarios", "probes_pack.py"),
    ("tests", "pi_benchmark", "test_probes.py"),
    ("tests", "real_user_benchmark", ".results"),
    ("tests", "simulation", ".results"),
    ("tests", "simulation", "test-results"),
    ("tests", "evals", ".results"),
}

TEXT_SUFFIXES = {
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

GLOBAL_FORBIDDEN = {
    "old_repeated_canonical_quote": "I can only approve a recommendation when the system shows which task, transcript, ticket, or survey row produced it",
    "lorem_ipsum_filler": "lorem ipsum dolor",
    "ai_disclaimer": "as an ai language model",
    "personal_home_path": "/Users/studio",
    "machine_checkout_path": "Documents/Istara-main",
    "english_price_placeholder": "$X,XXX/year SaaS",
    "portuguese_price_placeholder": "R$X.XXX/ano SaaS",
    "stale_generated_version": "Generated from the repository on version `2026.04.27`",
}

RETIRED_ROOT_FILES = {
    "AGENT.md",
    "AGENT_ENTRYPOINT.md",
    "CLAUDE.md",
    "COMPLETE_SYSTEM.md",
    "GEMINI.md",
    "PROJECT_ISOLATION_GOAL_SPECIFICATION.md",
    "QWEN.md",
    "SYSTEM_INTEGRITY_GUIDE.md",
    "SYSTEM_PROMPT.md",
    "docs/CODEBASE_HEALTH_PASS.md",
    "docs/PROJECT_SCOPE_AND_RENDERING_ASSESSMENT.md",
    "scripts/update_agent_md.py",
}

RAW_SOURCE_FORBIDDEN = {
    "pre_digested_evidence_heading": "## Evidence unit candidate",
    "pre_digested_coding_hints": "Coding hints:",
    "pre_digested_implication": "Implication candidate:",
    "pre_digested_report_gate": "Report gate reminder:",
    "coverage_template": "This synthetic source supports",
}


def is_excluded(path: Path) -> bool:
    relative = path.relative_to(REPO_ROOT)
    parts = relative.parts
    if relative.name in EXCLUDED_FILE_NAMES:
        return True
    if any(part in EXCLUDED_DIR_NAMES for part in parts):
        return True
    return any(parts[: len(excluded)] == excluded for excluded in EXCLUDED_PARTS)


def iter_public_text_files() -> list[Path]:
    """Return tracked public text files, independent of ambient local artifacts."""
    output: list[Path] = []
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8").split("\0")
    for relative in tracked:
        if not relative:
            continue
        path = REPO_ROOT / relative
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES or is_excluded(path):
            continue
        output.append(path)
    return output


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def scan_global_forbidden(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        relative = path.relative_to(REPO_ROOT)
        if relative.as_posix() in {
            "scripts/public_repo_quality_audit.py",
            "tests/test_public_repo_quality.py",
        }:
            continue
        text = read_text(path).lower()
        for name, phrase in GLOBAL_FORBIDDEN.items():
            if phrase.lower() in text:
                findings.append(f"{relative}: forbidden public artifact phrase: {name}")
    return findings


def scan_canonical_raw_sources() -> list[str]:
    findings: list[str] = []
    if not CANONICAL_SOURCES.exists():
        return [f"{CANONICAL_SOURCES.relative_to(REPO_ROOT)}: canonical sources folder is missing"]
    for path in CANONICAL_SOURCES.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".csv"}:
            continue
        text = read_text(path)
        relative = path.relative_to(REPO_ROOT)
        for name, phrase in RAW_SOURCE_FORBIDDEN.items():
            if phrase in text:
                findings.append(f"{relative}: raw source contains pre-digested artifact marker: {name}")
    return findings


def scan_repeated_source_excerpts() -> list[str]:
    excerpts: Counter[str] = Counter()
    owners: dict[str, Path] = {}
    for path in CANONICAL_SOURCES.rglob("*.md"):
        for line in read_text(path).splitlines():
            if not (line.startswith("Verbatim/source excerpt:") or line.startswith("P")):
                continue
            if line.startswith("P") and not line[1:3].isdigit():
                continue
            normalized = " ".join(line.split())
            if len(normalized) < 80:
                continue
            excerpts[normalized] += 1
            owners.setdefault(normalized, path)

    findings: list[str] = []
    for line, count in excerpts.items():
        if count <= 1:
            continue
        owner = owners[line].relative_to(REPO_ROOT)
        findings.append(f"{owner}: repeated raw-source excerpt appears {count} times: {line[:140]}")
    return findings


def scan_retired_root_files() -> list[str]:
    findings: list[str] = []
    for relative in sorted(RETIRED_ROOT_FILES):
        if (REPO_ROOT / relative).exists():
            findings.append(f"{relative}: retired generated or diagnostic artifact should not be tracked")
    return findings


def audit() -> list[str]:
    paths = iter_public_text_files()
    findings = []
    findings.extend(scan_retired_root_files())
    findings.extend(scan_global_forbidden(paths))
    findings.extend(scan_canonical_raw_sources())
    findings.extend(scan_repeated_source_excerpts())
    return sorted(findings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit non-zero when findings are present")
    args = parser.parse_args()

    findings = audit()
    if findings:
        for finding in findings:
            print(finding)
        return 1 if args.check else 0
    print("public repo quality audit passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
