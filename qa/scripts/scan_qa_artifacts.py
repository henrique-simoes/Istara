"""QA artifact redaction scanner.

Scans logs/artifacts under a QA run directory for private-endpoint
fingerprints, tokens, and key material. CI and the ``audit`` Compose profile
fail on any hit. Extends the ``check_public_tree_clean.py`` philosophy to
runtime artifacts: raw source text, tokens, and full provider responses are
never uploaded.

Importable and deterministic: ``scan_path`` returns a report dict with no
side effects; ``main`` wires it to the CLI.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RUNS_DIR = ROOT / "qa" / "runs"

# Private-host fingerprints: local/LAN IPs, mDNS names, localhost aliases,
# and private URL forms. These are never allowed in public QA artifacts.
PRIVATE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "private-ipv4",
        re.compile(
            r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b"
        ),
    ),
    ("loopback", re.compile(r"\b127\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
    ("localhost", re.compile(r"\blocalhost\b", re.IGNORECASE)),
    ("mdns-host", re.compile(r"\b[\w-]+\.local\b", re.IGNORECASE)),
    ("multivac-host", re.compile(r"\bmultivac\b", re.IGNORECASE)),
]

# Token/key material patterns.
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "bearer-token",
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE),
    ),
    (
        "api-key",
        re.compile(
            r"\b(sk-[A-Za-z0-9]{12,}|api[_-]?key\s*[=:]\s*[A-Za-z0-9._-]{8,})\b",
            re.IGNORECASE,
        ),
    ),
    (
        "jwt",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
        ),
    ),
    (
        "connection-string",
        re.compile(r"\b(postgres(ql)?|mysql|redis|mongodb)(\+[a-z]+)?://[^\s\"']+"),
    ),
]


def scan_text(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for label, pattern in PRIVATE_PATTERNS + SECRET_PATTERNS:
        for match in pattern.finditer(text):
            hits.append(
                {
                    "pattern": label,
                    "match": match.group(0)[:64],
                    "offset": match.start(),
                }
            )
    return hits


def scan_path(path: Path, max_bytes: int = 2 * 1024 * 1024) -> dict[str, Any]:
    """Scan one file; returns a report dict (deterministic, no side effects)."""
    if not path.is_file():
        return {"path": str(path), "exists": False, "hits": [], "truncated": False}
    data = path.read_bytes()
    truncated = len(data) > max_bytes
    text = data[:max_bytes].decode("utf-8", errors="replace")
    return {
        "path": str(path),
        "exists": True,
        "truncated": truncated,
        "hits": scan_text(text),
    }


def scan_run(
    run_dir: Path,
    suffixes: tuple[str, ...] = (".json", ".log", ".txt", ".yaml", ".yml", ".csv"),
) -> dict[str, Any]:
    """Scan an entire run directory tree."""
    files = sorted(
        p for p in run_dir.rglob("*") if p.is_file() and p.suffix in suffixes
    )
    reports = [scan_path(p) for p in files]
    all_hits = [h for r in reports for h in r["hits"]]
    return {
        "run_dir": str(run_dir),
        "files_scanned": len(reports),
        "hit_count": len(all_hits),
        "hits": all_hits,
        "clean": not all_hits,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", help="QA run id (scans qa/runs/<run-id>)")
    parser.add_argument("--path", help="scan a single file or directory instead")
    parser.add_argument("--runs-dir", default=str(DEFAULT_RUNS_DIR))
    args = parser.parse_args(argv)

    if args.path:
        target = Path(args.path)
        report = scan_run(target) if target.is_dir() else scan_path(target)
    elif args.run_id:
        target = Path(args.runs_dir) / args.run_id
        if not target.exists():
            print(f"no such run directory: {target}")
            return 1
        report = scan_run(target)
    else:
        parser.error("provide --run-id or --path")

    print(f"Scanned {report['files_scanned']} files; {report['hit_count']} hits")
    for hit in report["hits"]:
        print(f"  {hit['pattern']}: {hit['match']!r}")
    if not report["clean"]:
        print(
            "Redaction scan FAILED: private fingerprints or secrets found in artifacts"
        )
        return 1
    print("Redaction scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
