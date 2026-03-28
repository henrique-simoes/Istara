"""Automated backup manager for ReClaw data.

Handles full and incremental backups of databases, vector stores, uploads,
project repos, agent personas, skill definitions, and configuration files.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import tarfile
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select

from app.config import settings
from app.models.backup import BackupRecord
from app.models.database import async_session

logger = logging.getLogger(__name__)

# Thread pool for blocking I/O (SQLite VACUUM, checksums, tar creation)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="backup")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: str | Path) -> str:
    """Compute SHA-256 hex digest for a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _redact_env_content(content: str) -> str:
    """Replace API key / secret values in .env content with [REDACTED]."""
    redacted_lines: list[str] = []
    sensitive_patterns = re.compile(
        r"(key|secret|token|password|credential)", re.IGNORECASE
    )
    for line in content.splitlines(keepends=True):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, _, value = stripped.partition("=")
            if sensitive_patterns.search(key):
                redacted_lines.append(f"{key}=[REDACTED]\n")
                continue
        redacted_lines.append(line)
    return "".join(redacted_lines)


def _safe_sqlite_copy(src_db_path: str, dest_path: str) -> None:
    """Create a consistent SQLite copy using VACUUM INTO (run in thread)."""
    if not Path(src_db_path).exists():
        return
    conn = sqlite3.connect(src_db_path)
    try:
        conn.execute(f"VACUUM INTO '{dest_path}'")
    finally:
        conn.close()


def _dir_file_count(dir_path: str | Path) -> int:
    """Count files inside a directory recursively."""
    count = 0
    p = Path(dir_path)
    if p.is_dir():
        for _ in p.rglob("*"):
            count += 1
    return count


def _dir_size(dir_path: str | Path) -> int:
    """Total size in bytes of all files in a directory."""
    total = 0
    p = Path(dir_path)
    if p.is_dir():
        for f in p.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total


def _count_subdirs(dir_path: str | Path) -> int:
    """Count immediate subdirectories."""
    p = Path(dir_path)
    if not p.is_dir():
        return 0
    return sum(1 for d in p.iterdir() if d.is_dir())


# ---------------------------------------------------------------------------
# BackupManager
# ---------------------------------------------------------------------------


class BackupManager:
    """Singleton backup manager with scheduled background operation."""

    def __init__(self) -> None:
        self._running = False
        self._check_interval = 300  # seconds between checks (5 min)
        self._task: asyncio.Task | None = None

    # -- Scheduled loop ------------------------------------------------------

    async def start_scheduled(self) -> None:
        """Background loop — check if a backup is due based on interval."""
        if not settings.backup_enabled:
            logger.info("Backup system disabled via config.")
            return

        self._running = True
        logger.info("Backup scheduler started (interval=%dh).", settings.backup_interval_hours)

        while self._running:
            try:
                await self._maybe_run_scheduled()
            except Exception:
                logger.exception("Backup scheduler tick error")
            await asyncio.sleep(self._check_interval)

    def stop(self) -> None:
        """Stop the scheduled loop."""
        self._running = False
        logger.info("Backup scheduler stopped.")

    async def _maybe_run_scheduled(self) -> None:
        """Run a backup if the configured interval has elapsed."""
        async with async_session() as db:
            result = await db.execute(
                select(BackupRecord)
                .where(BackupRecord.status.in_(["completed", "verified"]))
                .order_by(BackupRecord.created_at.desc())
                .limit(1)
            )
            last = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        interval_seconds = settings.backup_interval_hours * 3600

        if last and last.created_at:
            last_ts = last.created_at
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)
            elapsed = (now - last_ts).total_seconds()
            if elapsed < interval_seconds:
                return  # Not due yet

        # Determine backup type
        backup_type = self._determine_backup_type(last)
        logger.info("Scheduled %s backup starting.", backup_type)

        try:
            await self.create_backup(backup_type=backup_type)
        except Exception:
            logger.exception("Scheduled backup failed")

    def _determine_backup_type(self, last_backup: BackupRecord | None) -> str:
        """Decide between full and incremental backup."""
        if last_backup is None:
            return "full"

        # Find the last full backup
        # If it's been more than backup_full_interval_days since last full, do full
        state_path = Path(settings.backup_dir) / "_last_backup_state.json"
        if not state_path.exists():
            return "full"

        try:
            state = json.loads(state_path.read_text())
            last_full_ts = state.get("last_full_at")
            if not last_full_ts:
                return "full"
            last_full_dt = datetime.fromisoformat(last_full_ts)
            if last_full_dt.tzinfo is None:
                last_full_dt = last_full_dt.replace(tzinfo=timezone.utc)
            days_since_full = (datetime.now(timezone.utc) - last_full_dt).total_seconds() / 86400
            if days_since_full >= settings.backup_full_interval_days:
                return "full"
            return "incremental"
        except Exception:
            return "full"

    # -- Create backup -------------------------------------------------------

    async def create_backup(self, backup_type: str = "full") -> dict:
        """Create a tar.gz backup archive.

        Steps:
        1. Create temp directory
        2. Copy all components
        3. Generate manifest with SHA-256 checksums
        4. Create tar.gz archive
        5. Record BackupRecord in DB
        6. Enforce retention
        """
        record_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f"reclaw_backup_{timestamp}.tar.gz"
        archive_path = Path(settings.backup_dir) / filename

        # Create DB record (in_progress)
        async with async_session() as db:
            record = BackupRecord(
                id=record_id,
                filename=filename,
                backup_type=backup_type,
                status="in_progress",
            )
            db.add(record)
            await db.commit()

        # Broadcast start event
        await self._broadcast("backup_started", record_id, {"backup_type": backup_type})

        loop = asyncio.get_running_loop()
        try:
            # Determine parent for incremental
            parent_id = None
            previous_checksums: dict[str, str] = {}
            if backup_type == "incremental":
                parent_id, previous_checksums = await self._load_incremental_state()
                if not parent_id:
                    backup_type = "full"  # Fallback to full if no parent

            # Do the heavy work in thread pool
            result = await loop.run_in_executor(
                _executor,
                self._build_archive_sync,
                str(archive_path),
                backup_type,
                previous_checksums,
            )

            manifest = result["manifest"]
            total_size = result["total_size"]
            file_count = result["file_count"]
            archive_checksum = result["archive_checksum"]
            components = manifest.get("components", {})

            # Update DB record
            async with async_session() as db:
                rec_result = await db.execute(
                    select(BackupRecord).where(BackupRecord.id == record_id)
                )
                rec = rec_result.scalar_one()
                rec.status = "completed"
                rec.size_bytes = total_size
                rec.file_count = file_count
                rec.checksum = archive_checksum
                rec.components = json.dumps(components)
                rec.parent_id = parent_id
                rec.backup_type = backup_type
                await db.commit()

            # Save incremental state
            await loop.run_in_executor(
                _executor,
                self._save_incremental_state,
                record_id,
                backup_type,
                manifest.get("checksums", {}),
                now.isoformat(),
            )

            # Enforce retention
            await self.enforce_retention()

            await self._broadcast("backup_completed", record_id, {
                "backup_type": backup_type,
                "size_bytes": total_size,
                "file_count": file_count,
            })

            logger.info(
                "Backup completed: %s (%s, %d bytes, %d files)",
                filename, backup_type, total_size, file_count,
            )

            return {
                "id": record_id,
                "filename": filename,
                "backup_type": backup_type,
                "size_bytes": total_size,
                "file_count": file_count,
                "status": "completed",
                "components": components,
                "checksum": archive_checksum,
            }

        except Exception as exc:
            # Mark as failed
            async with async_session() as db:
                rec_result = await db.execute(
                    select(BackupRecord).where(BackupRecord.id == record_id)
                )
                rec = rec_result.scalar_one_or_none()
                if rec:
                    rec.status = "failed"
                    rec.error_message = str(exc)[:2000]
                    await db.commit()

            await self._broadcast("backup_failed", record_id, {"error": str(exc)[:500]})
            logger.exception("Backup failed: %s", filename)
            raise

    def _build_archive_sync(
        self,
        archive_path: str,
        backup_type: str,
        previous_checksums: dict[str, str],
    ) -> dict:
        """Build the tar.gz archive (blocking — runs in executor)."""
        with tempfile.TemporaryDirectory(prefix="reclaw_backup_") as tmp_dir:
            tmp = Path(tmp_dir)
            checksums: dict[str, str] = {}
            components: dict[str, dict] = {}

            # ── 1. Main SQLite database ──
            main_db_src = "./data/reclaw.db"
            if Path(main_db_src).exists():
                dest = tmp / "data" / "reclaw.db"
                dest.parent.mkdir(parents=True, exist_ok=True)
                _safe_sqlite_copy(main_db_src, str(dest))
                if dest.exists():
                    checksums["data/reclaw.db"] = _sha256_file(dest)
                    components["database"] = {
                        "size_bytes": dest.stat().st_size,
                    }

            # ── 2. Embedding cache SQLite ──
            embed_db_src = "./data/embedding_cache.db"
            if Path(embed_db_src).exists():
                dest = tmp / "data" / "embedding_cache.db"
                dest.parent.mkdir(parents=True, exist_ok=True)
                _safe_sqlite_copy(embed_db_src, str(dest))
                if dest.exists():
                    checksums["data/embedding_cache.db"] = _sha256_file(dest)

            # ── 3. LanceDB vector stores ──
            lance_src = "./data/lance_db"
            if Path(lance_src).is_dir():
                lance_dest = tmp / "data" / "lance_db"
                self._copy_dir(lance_src, str(lance_dest), checksums, backup_type, previous_checksums)
                stores = _count_subdirs(lance_dest) if lance_dest.exists() else 0
                components["lance_db"] = {"stores": stores}

            # ── 4. BM25 keyword indexes ──
            kw_src = "./data/keyword_index"
            if Path(kw_src).is_dir():
                kw_dest = tmp / "data" / "keyword_index"
                self._copy_dir(kw_src, str(kw_dest), checksums, backup_type, previous_checksums)
                kw_files = _dir_file_count(kw_dest) if kw_dest.exists() else 0
                components["keyword_index"] = {"files": kw_files}

            # ── 5. Uploaded files ──
            uploads_src = settings.upload_dir
            if Path(uploads_src).is_dir():
                uploads_dest = tmp / "data" / "uploads"
                self._copy_dir(uploads_src, str(uploads_dest), checksums, backup_type, previous_checksums)
                upload_dirs = _count_subdirs(uploads_dest) if uploads_dest.exists() else 0
                components["uploads"] = {"dirs": upload_dirs}

            # ── 6. Project git repos ──
            projects_src = settings.projects_dir
            if Path(projects_src).is_dir():
                projects_dest = tmp / "data" / "projects"
                self._copy_dir(projects_src, str(projects_dest), checksums, backup_type, previous_checksums)
                proj_count = _count_subdirs(projects_dest) if projects_dest.exists() else 0
                components["projects"] = {"count": proj_count}

            # ── 7. Watcher state ──
            watcher_src = "./data/watcher_state.json"
            if Path(watcher_src).exists():
                dest = tmp / "data" / "watcher_state.json"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(watcher_src, str(dest))
                checksums["data/watcher_state.json"] = _sha256_file(dest)

            # ── 8. Agent persona files ──
            personas_src = "./backend/app/agents/personas"
            if Path(personas_src).is_dir():
                personas_dest = tmp / "backend" / "app" / "agents" / "personas"
                self._copy_dir(personas_src, str(personas_dest), checksums, backup_type, previous_checksums)
                persona_count = sum(1 for f in Path(personas_src).rglob("*.md"))
                components["personas"] = {"count": persona_count}

            # ── 9. Skill definitions ──
            skills_src = "./backend/app/skills/definitions"
            if Path(skills_src).is_dir():
                skills_dest = tmp / "backend" / "app" / "skills" / "definitions"
                self._copy_dir(skills_src, str(skills_dest), checksums, backup_type, previous_checksums)
                skill_count = sum(1 for f in Path(skills_src).rglob("*.json"))
                components["skills"] = {"count": skill_count}

            # ── 10. Agent proposals ──
            proposals_src = "./data/_agent_proposals.json"
            if Path(proposals_src).exists():
                dest = tmp / "data" / "_agent_proposals.json"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(proposals_src, str(dest))
                checksums["data/_agent_proposals.json"] = _sha256_file(dest)

            # ── 11. .env config (REDACTED) ──
            env_src = "./backend/.env"
            if Path(env_src).exists():
                dest = tmp / "backend" / ".env"
                dest.parent.mkdir(parents=True, exist_ok=True)
                raw = Path(env_src).read_text()
                dest.write_text(_redact_env_content(raw))
                checksums["backend/.env"] = _sha256_file(dest)

            # ── Build manifest ──
            total_size = sum(
                f.stat().st_size for f in Path(tmp).rglob("*") if f.is_file()
            )
            file_count = sum(1 for f in Path(tmp).rglob("*") if f.is_file())

            manifest = {
                "version": "1.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "backup_type": backup_type,
                "parent_backup_id": None,
                "total_size_bytes": total_size,
                "file_count": file_count,
                "checksums": checksums,
                "components": components,
            }

            manifest_path = tmp / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2))

            # ── Create tar.gz ──
            with tarfile.open(archive_path, "w:gz") as tar:
                for item in Path(tmp).rglob("*"):
                    arcname = str(item.relative_to(tmp))
                    tar.add(str(item), arcname=arcname)

            archive_checksum = _sha256_file(archive_path)

            # Harden permissions: owner read/write only (0600)
            try:
                os.chmod(archive_path, 0o600)
            except OSError:
                pass  # May fail on some filesystems

            return {
                "manifest": manifest,
                "total_size": Path(archive_path).stat().st_size,
                "file_count": file_count,
                "archive_checksum": archive_checksum,
            }

    def _copy_dir(
        self,
        src: str,
        dest: str,
        checksums: dict[str, str],
        backup_type: str,
        previous_checksums: dict[str, str],
    ) -> None:
        """Copy a directory tree, optionally skipping unchanged files for incremental."""
        src_path = Path(src)
        dest_path = Path(dest)

        if not src_path.is_dir():
            return

        for item in src_path.rglob("*"):
            if item.is_file():
                rel = str(item.relative_to(Path("."))) if str(item).startswith("./") else str(item)
                # Normalize path for manifest
                try:
                    rel = str(item.relative_to(Path(".")))
                except ValueError:
                    rel = str(item)

                if backup_type == "incremental":
                    current_hash = _sha256_file(item)
                    if rel in previous_checksums and previous_checksums[rel] == current_hash:
                        continue  # Unchanged, skip

                target = dest_path / item.relative_to(src_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(item), str(target))

                # Use the archive-relative path for checksums
                archive_rel = str(target.relative_to(dest_path.parents[len(dest_path.parts) - 2]))
                # Simpler: compute from what we know the archive layout will be
                try:
                    # The temp dir structure mirrors the source layout
                    parts = dest_path.parts
                    # Find the temp dir root (first component after /tmp/...)
                    # We need the path relative to the temp root
                    # Since we can't easily get temp root here, use src-based rel path
                    archive_key = str(Path(src).parent / item.relative_to(src_path))
                    # Normalize: remove leading ./
                    if archive_key.startswith("./"):
                        archive_key = archive_key[2:]
                    checksums[archive_key] = _sha256_file(target)
                except Exception:
                    checksums[rel] = _sha256_file(target)

    # -- Incremental state ---------------------------------------------------

    async def _load_incremental_state(self) -> tuple[str | None, dict[str, str]]:
        """Load the last backup state for incremental comparison."""
        state_path = Path(settings.backup_dir) / "_last_backup_state.json"
        if not state_path.exists():
            return None, {}

        try:
            state = json.loads(state_path.read_text())
            parent_id = state.get("last_full_id") or state.get("last_backup_id")
            checksums = state.get("checksums", {})
            return parent_id, checksums
        except Exception:
            return None, {}

    def _save_incremental_state(
        self,
        backup_id: str,
        backup_type: str,
        checksums: dict[str, str],
        timestamp: str,
    ) -> None:
        """Persist state for future incremental comparisons."""
        state_path = Path(settings.backup_dir) / "_last_backup_state.json"

        state: dict = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text())
            except Exception:
                state = {}

        state["last_backup_id"] = backup_id
        state["last_backup_at"] = timestamp
        state["checksums"] = checksums

        if backup_type == "full":
            state["last_full_id"] = backup_id
            state["last_full_at"] = timestamp

        state_path.write_text(json.dumps(state, indent=2))
        try:
            os.chmod(str(state_path), 0o600)
        except OSError:
            pass

    # -- Restore -------------------------------------------------------------

    async def restore_from_backup(self, backup_id: str) -> dict:
        """Extract archive, verify checksums, restore DB and filesystem dirs."""
        async with async_session() as db:
            result = await db.execute(
                select(BackupRecord).where(BackupRecord.id == backup_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                raise ValueError(f"Backup record not found: {backup_id}")

        archive_path = Path(settings.backup_dir) / record.filename
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

        await self._broadcast("backup_restore_started", backup_id, {})

        loop = asyncio.get_running_loop()

        try:
            # Extract and restore in thread pool
            restore_result = await loop.run_in_executor(
                _executor,
                self._restore_sync,
                str(archive_path),
            )

            await self._broadcast("backup_restore_completed", backup_id, restore_result)
            logger.info("Restore completed from backup %s", backup_id)
            return {"status": "restored", "backup_id": backup_id, **restore_result}

        except Exception as exc:
            await self._broadcast("backup_restore_failed", backup_id, {"error": str(exc)[:500]})
            logger.exception("Restore failed for backup %s", backup_id)
            raise

    def _restore_sync(self, archive_path: str) -> dict:
        """Extract and restore backup files (blocking)."""
        restored_components: list[str] = []

        with tempfile.TemporaryDirectory(prefix="reclaw_restore_") as tmp_dir:
            # Extract
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(tmp_dir)

            tmp = Path(tmp_dir)

            # Load and verify manifest
            manifest_path = tmp / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text())
                checksums = manifest.get("checksums", {})

                # Verify checksums
                for rel_path, expected_hash in checksums.items():
                    file_path = tmp / rel_path
                    if file_path.exists():
                        actual_hash = _sha256_file(file_path)
                        if actual_hash != expected_hash:
                            logger.warning(
                                "Checksum mismatch during restore: %s (expected %s, got %s)",
                                rel_path, expected_hash, actual_hash,
                            )

            # Restore database
            db_src = tmp / "data" / "reclaw.db"
            if db_src.exists():
                shutil.copy2(str(db_src), "./data/reclaw.db")
                restored_components.append("database")

            # Restore embedding cache
            embed_src = tmp / "data" / "embedding_cache.db"
            if embed_src.exists():
                shutil.copy2(str(embed_src), "./data/embedding_cache.db")
                restored_components.append("embedding_cache")

            # Restore directories
            dir_mappings = {
                "data/lance_db": "./data/lance_db",
                "data/keyword_index": "./data/keyword_index",
                "data/uploads": settings.upload_dir,
                "data/projects": settings.projects_dir,
                "backend/app/agents/personas": "./backend/app/agents/personas",
                "backend/app/skills/definitions": "./backend/app/skills/definitions",
            }

            for archive_dir, target_dir in dir_mappings.items():
                src_dir = tmp / archive_dir
                if src_dir.is_dir():
                    target = Path(target_dir)
                    # Merge: copy files from backup into target without deleting existing
                    for item in src_dir.rglob("*"):
                        if item.is_file():
                            rel = item.relative_to(src_dir)
                            dest = target / rel
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(item), str(dest))
                    restored_components.append(archive_dir.split("/")[-1])

            # Restore individual files
            watcher_src = tmp / "data" / "watcher_state.json"
            if watcher_src.exists():
                shutil.copy2(str(watcher_src), "./data/watcher_state.json")
                restored_components.append("watcher_state")

            proposals_src = tmp / "data" / "_agent_proposals.json"
            if proposals_src.exists():
                shutil.copy2(str(proposals_src), "./data/_agent_proposals.json")
                restored_components.append("agent_proposals")

        return {
            "restored_components": restored_components,
            "component_count": len(restored_components),
        }

    # -- Verify --------------------------------------------------------------

    async def verify_backup(self, backup_id: str) -> dict:
        """Extract archive and verify all SHA-256 checksums match manifest."""
        async with async_session() as db:
            result = await db.execute(
                select(BackupRecord).where(BackupRecord.id == backup_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                raise ValueError(f"Backup record not found: {backup_id}")

        archive_path = Path(settings.backup_dir) / record.filename
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

        loop = asyncio.get_running_loop()
        verify_result = await loop.run_in_executor(
            _executor,
            self._verify_sync,
            str(archive_path),
        )

        # Update record status
        now = datetime.now(timezone.utc)
        async with async_session() as db:
            rec_result = await db.execute(
                select(BackupRecord).where(BackupRecord.id == backup_id)
            )
            rec = rec_result.scalar_one()
            rec.verified_at = now
            if verify_result["valid"]:
                rec.status = "verified"
            else:
                rec.error_message = "; ".join(verify_result["mismatches"][:5])
            await db.commit()

        return verify_result

    def _verify_sync(self, archive_path: str) -> dict:
        """Verify archive checksums (blocking)."""
        with tempfile.TemporaryDirectory(prefix="reclaw_verify_") as tmp_dir:
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(tmp_dir, filter="data")

            # Fix permissions so git object files are readable
            for root, dirs, files in os.walk(tmp_dir):
                for d in dirs:
                    try:
                        os.chmod(os.path.join(root, d), 0o755)
                    except OSError:
                        pass
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), 0o644)
                    except OSError:
                        pass

            tmp = Path(tmp_dir)
            manifest_path = tmp / "manifest.json"
            if not manifest_path.exists():
                return {"valid": False, "mismatches": ["manifest.json missing"], "checked": 0}

            manifest = json.loads(manifest_path.read_text())
            checksums = manifest.get("checksums", {})

            mismatches: list[str] = []
            checked = 0

            for rel_path, expected_hash in checksums.items():
                file_path = tmp / rel_path
                if not file_path.exists():
                    mismatches.append(f"missing: {rel_path}")
                    continue
                actual_hash = _sha256_file(file_path)
                checked += 1
                if actual_hash != expected_hash:
                    mismatches.append(f"mismatch: {rel_path}")

            return {
                "valid": len(mismatches) == 0,
                "checked": checked,
                "total_expected": len(checksums),
                "mismatches": mismatches,
            }

    # -- Retention -----------------------------------------------------------

    async def enforce_retention(self) -> int:
        """Delete oldest backups exceeding retention_count. Returns count deleted."""
        async with async_session() as db:
            result = await db.execute(
                select(BackupRecord)
                .where(BackupRecord.status.in_(["completed", "verified"]))
                .order_by(BackupRecord.created_at.desc())
            )
            all_records = result.scalars().all()

            if len(all_records) <= settings.backup_retention_count:
                return 0

            to_delete = all_records[settings.backup_retention_count:]
            deleted = 0

            for record in to_delete:
                # Remove archive file
                archive_path = Path(settings.backup_dir) / record.filename
                if archive_path.exists():
                    try:
                        archive_path.unlink()
                    except OSError:
                        logger.warning("Could not delete backup file: %s", archive_path)

                await db.execute(
                    delete(BackupRecord).where(BackupRecord.id == record.id)
                )
                deleted += 1

            await db.commit()
            if deleted:
                logger.info("Retention: deleted %d old backup(s).", deleted)
            return deleted

    # -- Size estimate -------------------------------------------------------

    def get_backup_size_estimate(self) -> dict:
        """Calculate approximate size of the next backup."""
        estimates: dict[str, int] = {}

        # Database
        db_path = Path("./data/reclaw.db")
        if db_path.exists():
            estimates["database"] = db_path.stat().st_size

        embed_path = Path("./data/embedding_cache.db")
        if embed_path.exists():
            estimates["embedding_cache"] = embed_path.stat().st_size

        # Directories
        dir_paths = {
            "lance_db": "./data/lance_db",
            "keyword_index": "./data/keyword_index",
            "uploads": settings.upload_dir,
            "projects": settings.projects_dir,
            "personas": "./backend/app/agents/personas",
            "skills": "./backend/app/skills/definitions",
        }

        for name, path in dir_paths.items():
            if Path(path).is_dir():
                estimates[name] = _dir_size(path)

        total = sum(estimates.values())
        # Estimate compression ratio (~40% for mixed content)
        compressed_estimate = int(total * 0.6)

        return {
            "uncompressed_bytes": total,
            "compressed_estimate_bytes": compressed_estimate,
            "components": estimates,
        }

    # -- List ----------------------------------------------------------------

    async def list_backups(self) -> list[dict]:
        """Return all BackupRecord dicts ordered by creation date desc."""
        async with async_session() as db:
            result = await db.execute(
                select(BackupRecord).order_by(BackupRecord.created_at.desc())
            )
            return [r.to_dict() for r in result.scalars().all()]

    # -- Delete --------------------------------------------------------------

    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a single backup record and its archive file."""
        async with async_session() as db:
            result = await db.execute(
                select(BackupRecord).where(BackupRecord.id == backup_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                return False

            # Remove file
            archive_path = Path(settings.backup_dir) / record.filename
            if archive_path.exists():
                archive_path.unlink()

            await db.execute(
                delete(BackupRecord).where(BackupRecord.id == record.id)
            )
            await db.commit()
            return True

    # -- Get archive path ----------------------------------------------------

    async def get_archive_path(self, backup_id: str) -> Path | None:
        """Return the archive file path for a backup, or None."""
        async with async_session() as db:
            result = await db.execute(
                select(BackupRecord).where(BackupRecord.id == backup_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                return None

        path = Path(settings.backup_dir) / record.filename
        return path if path.exists() else None

    # -- Broadcast helper ----------------------------------------------------

    async def _broadcast(self, event: str, backup_id: str, details: dict) -> None:
        """Broadcast a backup event via WebSocket."""
        try:
            from app.api.websocket import broadcast_backup_event
            await broadcast_backup_event(event, backup_id, details)
        except Exception:
            logger.debug("Could not broadcast backup event: %s", event, exc_info=True)


# Module-level singleton
backup_manager = BackupManager()
