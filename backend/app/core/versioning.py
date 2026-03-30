"""Git-based versioning system for project data."""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.config import settings


@dataclass
class VersionEntry:
    """A single version in the history."""

    commit_hash: str
    message: str
    author: str
    timestamp: datetime
    files_changed: list[str]


class ProjectVersioning:
    """Git-based version control for a project's data."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self.project_dir = Path(settings.projects_dir) / project_id
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def _run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the project directory."""
        return subprocess.run(
            ["git", *args],
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            check=check,
            timeout=30,
        )

    def init(self) -> None:
        """Initialize git repo for the project if not already initialized."""
        git_dir = self.project_dir / ".git"
        if git_dir.exists():
            return

        self._run_git("init")
        self._run_git("config", "user.email", "istara@local")
        self._run_git("config", "user.name", "Istara")

        # Initial commit
        readme = self.project_dir / "README.md"
        readme.write_text(f"# Project: {self.project_id}\n\nManaged by Istara.\n")
        self._run_git("add", ".")
        self._run_git("commit", "-m", "Initialize project")

    def save_file(self, filename: str, content: str, message: str | None = None) -> str:
        """Save a file and create a versioned commit.

        Args:
            filename: Name of the file to save.
            content: File content.
            message: Commit message (auto-generated if not provided).

        Returns:
            Commit hash.
        """
        self.init()

        file_path = self.project_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        self._run_git("add", filename)

        commit_msg = message or f"Update {filename}"
        result = self._run_git("commit", "-m", commit_msg, check=False)

        if result.returncode != 0 and "nothing to commit" in result.stdout:
            # No changes
            return self._get_head_hash()

        return self._get_head_hash()

    def save_json(self, filename: str, data: dict, message: str | None = None) -> str:
        """Save a JSON file and create a versioned commit."""
        content = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        return self.save_file(filename, content, message)

    def _get_head_hash(self) -> str:
        """Get the current HEAD commit hash."""
        result = self._run_git("rev-parse", "HEAD", check=False)
        return result.stdout.strip() if result.returncode == 0 else ""

    def get_history(self, limit: int = 50) -> list[VersionEntry]:
        """Get version history for the project.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of version entries, newest first.
        """
        self.init()

        result = self._run_git(
            "log",
            f"-{limit}",
            "--format=%H|%s|%an|%aI",
            "--name-only",
            check=False,
        )

        if result.returncode != 0:
            return []

        entries: list[VersionEntry] = []
        current_entry: dict | None = None
        current_files: list[str] = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                if current_entry:
                    entries.append(
                        VersionEntry(
                            **current_entry,
                            files_changed=current_files,
                        )
                    )
                    current_entry = None
                    current_files = []
                continue

            if "|" in line and line.count("|") >= 3:
                if current_entry:
                    entries.append(
                        VersionEntry(
                            **current_entry,
                            files_changed=current_files,
                        )
                    )
                    current_files = []

                parts = line.split("|", 3)
                current_entry = {
                    "commit_hash": parts[0],
                    "message": parts[1],
                    "author": parts[2],
                    "timestamp": datetime.fromisoformat(parts[3]),
                }
            elif current_entry and line.strip():
                current_files.append(line.strip())

        if current_entry:
            entries.append(
                VersionEntry(**current_entry, files_changed=current_files)
            )

        return entries

    def get_diff(self, commit_hash: str) -> str:
        """Get the diff for a specific commit.

        Args:
            commit_hash: The commit to show diff for.

        Returns:
            Diff text.
        """
        result = self._run_git("diff", f"{commit_hash}~1", commit_hash, check=False)
        return result.stdout if result.returncode == 0 else ""

    def rollback(self, commit_hash: str) -> str:
        """Rollback to a specific commit.

        Args:
            commit_hash: The commit to rollback to.

        Returns:
            New commit hash after rollback.
        """
        self._run_git("revert", "--no-commit", f"{commit_hash}..HEAD", check=False)
        self._run_git("commit", "-m", f"Rollback to {commit_hash[:8]}", check=False)
        return self._get_head_hash()

    def get_file(self, filename: str, commit_hash: str | None = None) -> str | None:
        """Get file content at a specific version.

        Args:
            filename: File to retrieve.
            commit_hash: Specific version (HEAD if None).

        Returns:
            File content or None if not found.
        """
        ref = commit_hash or "HEAD"
        result = self._run_git("show", f"{ref}:{filename}", check=False)
        return result.stdout if result.returncode == 0 else None
