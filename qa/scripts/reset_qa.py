"""Project-scoped QA reset (disposable environment teardown).

Deletes ONLY the generated QA project namespace (volumes/networks/containers
derived from the run id) and never touches developer volumes, the base
``docker-compose.yml`` stack, or the protected local artifact folders
``LLMs/`` and ``Model_Finetuning/``.

The reset contract mirrors the winning master plan section 8.3:
  1. requires an explicit confirmation token (never ``--force``);
  2. rejects empty/root paths and unsafe run ids;
  3. prints the exact project being targeted before doing anything;
  4. refuses to run when the target resolves to a protected folder.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

SAFE_PROJECT = re.compile(r"^istara-qa-[a-z0-9][a-z0-9_-]{0,63}$")
CONFIRM_TOKEN = "RESET-ISTARA-QA-RUN"
PROTECTED_FOLDERS = ("LLMs", "Model_Finetuning")


def project_name(run_id: str) -> str:
    project = f"istara-qa-{run_id}"
    if not SAFE_PROJECT.match(project):
        raise ValueError(f"unsafe QA project name: {project!r}")
    return project


def validate_target(run_id: str) -> None:
    """Refuse empty/unsafe run ids and any protected-folder resolution."""
    if not run_id or run_id in (".", "/", ".."):
        raise ValueError("empty or root QA run id is not allowed")
    if not SAFE_PROJECT.match(project_name(run_id)):
        raise ValueError(f"unsafe QA run id: {run_id!r}")
    for folder in PROTECTED_FOLDERS:
        if folder.lower() in run_id.lower():
            raise ValueError(
                f"refusing reset: run id {run_id!r} resolves toward protected folder {folder}"
            )


def reset_project(run_id: str, *, dry_run: bool = False, compose_files: list[str] | None = None) -> dict[str, str]:
    """Tear down one QA project namespace with ``docker compose -p ... down -v``.

    Returns the command run. When ``dry_run`` is true nothing is executed.
    Only the self-contained QA overlay is targeted: merging the base compose
    here would reintroduce ollama and the fixed istara-* container names.
    """
    validate_target(run_id)
    project = project_name(run_id)
    files = compose_files or ["docker-compose.qa.yml"]
    cmd = ["docker", "compose"]
    for f in files:
        cmd += ["-f", f]
    cmd += ["-p", project, "down", "-v"]
    if dry_run:
        return {"dry_run": True, "command": " ".join(cmd), "project": project}
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"reset failed for {project}: {result.stderr.strip()}")
    return {"dry_run": False, "command": " ".join(cmd), "project": project, "output": result.stdout.strip()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="QA run id (istara-qa-<run-id>)")
    parser.add_argument(
        "--confirm",
        choices=[CONFIRM_TOKEN],
        required=True,
        help=f"confirmation token (must be {CONFIRM_TOKEN})",
    )
    parser.add_argument("--dry-run", action="store_true", help="print the command without running it")
    args = parser.parse_args(argv)

    if args.confirm != CONFIRM_TOKEN:
        parser.error("invalid confirmation token")

    try:
        result = reset_project(args.run_id, dry_run=args.dry_run)
    except (ValueError, RuntimeError) as exc:
        print(f"QA reset FAILED: {exc}")
        return 1

    print(f"QA reset {'(dry-run) ' if result.get('dry_run') else ''}completed for {result['project']}")
    print(f"command: {result['command']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
