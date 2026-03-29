"""Watch directories for new/modified files and auto-ingest them."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path

from watchfiles import awatch, Change

from app.core.embeddings import embed_chunks
from app.core.file_processor import get_supported_extensions, process_file
from app.core.rag import VectorStore
from app.api.websocket import broadcast_file_processed, broadcast_suggestion

logger = logging.getLogger(__name__)


class FileWatcher:
    """Watches configured directories for file changes and auto-processes them."""

    def __init__(self) -> None:
        self._running = False
        self._watched_dirs: dict[str, str] = {}  # dir_path → project_id
        self._processed_files: dict[str, float] = {}  # file_path → last_modified
        self._state_file = Path("data/watcher_state.json")
        self._load_state()

    def _load_state(self) -> None:
        """Load processed file state from disk."""
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text())
                self._processed_files = data.get("processed_files", {})
                self._watched_dirs = data.get("watched_dirs", {})
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_state(self) -> None:
        """Save processed file state to disk (atomic write)."""
        from app.core.checkpoint import atomic_write

        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(
            self._state_file,
            json.dumps(
                {
                    "processed_files": self._processed_files,
                    "watched_dirs": self._watched_dirs,
                },
                indent=2,
            ),
        )

    def add_watch(self, directory: str, project_id: str) -> None:
        """Add a directory to watch for a specific project."""
        self._watched_dirs[directory] = project_id
        self._save_state()
        logger.info(f"Watching directory: {directory} for project {project_id}")

    def remove_watch(self, directory: str) -> None:
        """Remove a directory from watching."""
        self._watched_dirs.pop(directory, None)
        self._save_state()
        logger.info(f"Stopped watching: {directory}")

    def get_watches(self) -> dict[str, str]:
        """Get all watched directories."""
        return dict(self._watched_dirs)

    # ── File classification for auto-task creation ──────────────────────

    def _classify_file(self, file_path: Path) -> list[tuple[str, str, str]]:
        """Classify a file and return applicable (skill_name, task_title, priority) tuples."""
        filename = file_path.name.lower()
        ext = file_path.suffix.lower()
        stem = file_path.stem

        # Read first 500 chars for content-based heuristics
        try:
            preview = file_path.read_text(errors="replace")[:500].lower()
        except Exception:
            preview = ""

        tasks: list[tuple[str, str, str]] = []

        # Interview transcripts
        if "interview" in filename or "transcript" in filename or \
           ("[00:" in preview and "interviewer:" in preview):
            tasks.append(("user-interviews", f"Analyze interview: {stem}", "high"))
            tasks.append(("thematic-analysis", f"Thematic analysis: {stem}", "medium"))

        # Survey data
        elif ext == ".csv" and ("survey" in filename or "respondent" in preview):
            tasks.append(("survey-design", f"Analyze survey: {stem}", "high"))
            if "would_recommend" in preview or "nps" in preview:
                tasks.append(("nps-analysis", f"NPS analysis: {stem}", "medium"))
            if "sus" in filename or "usability" in preview:
                tasks.append(("sus-umux-scoring", f"SUS/UMUX scoring: {stem}", "medium"))

        # Usability test reports
        elif "usability" in filename or ("completion rate" in preview and "sus score" in preview):
            tasks.append(("usability-testing", f"Review usability test: {stem}", "high"))
            tasks.append(("heuristic-evaluation", f"Heuristic review: {stem}", "low"))

        # Field/research notes
        elif "field-notes" in filename or "field notes" in preview:
            tasks.append(("field-studies", f"Analyze field notes: {stem}", "high"))
            tasks.append(("empathy-mapping", f"Empathy map from: {stem}", "medium"))

        # Diary studies
        elif "diary" in filename or ("day " in preview and "mood" in preview):
            tasks.append(("diary-studies", f"Analyze diary study: {stem}", "high"))
            tasks.append(("longitudinal-tracking", f"Longitudinal tracking: {stem}", "medium"))

        # Competitive analysis
        elif "competitor" in filename or "competitive" in filename:
            tasks.append(("competitive-analysis", f"Competitive analysis: {stem}", "high"))

        # Analytics data
        elif ext == ".csv" and ("sessions" in preview or "bounce_rate" in preview or "conversions" in preview):
            tasks.append(("analytics-review", f"Analytics review: {stem}", "high"))
            if "variant" in preview or "a/b" in preview or "ab-test" in filename:
                tasks.append(("ab-test-analysis", f"A/B test analysis: {stem}", "high"))

        # Fallback: unclassified research document
        elif ext in {".txt", ".md", ".pdf", ".docx"}:
            tasks.append(("research-synthesis", f"Synthesize: {stem}", "low"))

        return tasks

    async def _create_research_tasks(self, file_path: Path, project_id: str) -> int:
        """Create research tasks for a processed file based on its classification.

        Returns:
            Number of tasks created.
        """
        skill_tasks = self._classify_file(file_path)
        if not skill_tasks:
            return 0

        from app.models.database import async_session
        from app.models.task import Task, TaskStatus
        from sqlalchemy import select, func

        created = 0
        async with async_session() as db:
            for skill_name, task_title, priority in skill_tasks:
                # Deduplication: skip if task already exists for this file + skill
                existing = await db.execute(
                    select(func.count(Task.id)).where(
                        Task.project_id == project_id,
                        Task.skill_name == skill_name,
                        Task.description.contains(file_path.name),
                        Task.status.in_([TaskStatus.BACKLOG, TaskStatus.IN_PROGRESS]),
                    )
                )
                if (existing.scalar() or 0) > 0:
                    continue

                # Get max position
                result = await db.execute(
                    select(func.max(Task.position)).where(Task.project_id == project_id)
                )
                max_pos = result.scalar() or 0

                task = Task(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    title=task_title,
                    description=f"Auto-created from file: {file_path.name}",
                    skill_name=skill_name,
                    agent_id="reclaw-main",
                    priority=priority,
                    position=max_pos + 1,
                )
                db.add(task)
                created += 1

            if created > 0:
                await db.commit()

        # Notify user and wake agent
        if created > 0:
            try:
                await broadcast_suggestion(
                    f"New research file: {file_path.name} — created {created} analysis task(s).",
                    project_id,
                )
            except Exception:
                pass

            try:
                from app.core.agent import agent as agent_orchestrator
                agent_orchestrator.wake()
            except Exception:
                pass

            logger.info(f"Created {created} tasks for {file_path.name} in project {project_id}")

        return created

    # ── Document registration ──────────────────────────────────────────

    async def _register_document(self, file_path: Path, project_id: str) -> None:
        """Register a processed file as a Document in the database.

        Ensures every file in the project folder appears in the Documents UI.
        Skips if a document for this file already exists.
        """
        from app.models.database import async_session
        from app.models.document import Document, DocumentSource, DocumentStatus
        from sqlalchemy import select

        async with async_session() as db:
            # Check if already registered
            existing = await db.execute(
                select(Document.id).where(
                    Document.project_id == project_id,
                    Document.file_name == file_path.name,
                )
            )
            if existing.scalar_one_or_none():
                return  # Already tracked

            stat = file_path.stat()
            suffix = file_path.suffix.lower()

            # Read preview for text-based files
            content_preview = ""
            content_text = ""
            if suffix in {".txt", ".md", ".csv", ".json"}:
                try:
                    text = file_path.read_text(errors="replace")
                    content_preview = text[:2000]
                    content_text = text
                except Exception:
                    pass

            title = file_path.stem.replace("-", " ").replace("_", " ").title()

            doc = Document(
                id=str(uuid.uuid4()),
                project_id=project_id,
                title=title,
                description=f"File detected in project folder: {file_path.name}",
                file_path=str(file_path),
                file_name=file_path.name,
                file_type=suffix,
                file_size=stat.st_size,
                status=DocumentStatus.READY,
                source=DocumentSource.PROJECT_FILE,
                content_preview=content_preview,
                content_text=content_text,
            )
            doc.set_tags([])

            db.add(doc)
            await db.commit()

            # Notify via WebSocket
            try:
                from app.api.websocket import broadcast_document_event
                await broadcast_document_event(
                    "document_created", doc.id, title, project_id
                )
            except Exception:
                pass

            logger.info(f"Registered document: {file_path.name} for project {project_id}")

    # ── File processing ─────────────────────────────────────────────────

    # Cloud-sync temp file patterns to skip
    _TEMP_PATTERNS = {
        ".partial", ".tmp", ".crdownload", ".download", ".part",
    }
    _TEMP_PREFIXES = ("~$", ".~", "._")

    def _is_temp_file(self, path: Path) -> bool:
        """Check if a file is a temporary/partial file from cloud sync or editors."""
        name = path.name
        suffix = path.suffix.lower()
        if suffix in self._TEMP_PATTERNS:
            return True
        if any(name.startswith(p) for p in self._TEMP_PREFIXES):
            return True
        if name.endswith("~"):
            return True
        return False

    async def _process_file(self, file_path: Path, project_id: str) -> dict | None:
        """Process a single file and ingest into the vector store.

        Returns:
            Summary dict of what was processed, or None if skipped/failed.
        """
        # Skip cloud-sync temp files
        if self._is_temp_file(file_path):
            return None

        # Skip if file disappeared (cloud conflict resolution)
        if not file_path.exists():
            return None

        suffix = file_path.suffix.lower()
        if suffix not in get_supported_extensions():
            return None

        # Check if already processed and not modified
        stat = file_path.stat()
        file_key = str(file_path)
        last_modified = stat.st_mtime

        if file_key in self._processed_files:
            if self._processed_files[file_key] >= last_modified:
                return None  # Already processed, not modified

        logger.info(f"Processing file: {file_path}")

        # Process the file
        result = process_file(file_path)
        if result.error:
            logger.error(f"Error processing {file_path}: {result.error}")
            return {"file": file_key, "error": result.error}

        if not result.chunks:
            logger.warning(f"No text extracted from {file_path}")
            return None

        # Delete old embeddings for this source
        store = VectorStore(project_id)
        await store.delete_by_source(file_key)

        # Embed and store
        embedded = await embed_chunks(result.chunks)
        count = await store.add_chunks(embedded)

        # Mark as processed
        self._processed_files[file_key] = last_modified
        self._save_state()

        summary = {
            "file": file_key,
            "chunks": count,
            "total_chars": result.total_chars,
            "pages": result.pages,
        }
        logger.info(f"Processed {file_path}: {count} chunks indexed")

        # Notify UI via WebSocket
        try:
            await broadcast_file_processed(file_path.name, count, project_id)
        except Exception:
            pass  # Don't fail file processing if broadcast fails

        # Auto-create research tasks based on file classification
        try:
            await self._create_research_tasks(file_path, project_id)
        except Exception as e:
            logger.warning(f"Failed to create research tasks for {file_path}: {e}")

        # Register as a Document in the Documents system
        try:
            await self._register_document(file_path, project_id)
        except Exception as e:
            logger.warning(f"Failed to register document for {file_path}: {e}")

        return summary

    async def scan_directory(self, directory: str, project_id: str) -> list[dict]:
        """Scan a directory and process all supported files.

        Returns:
            List of processing summaries.
        """
        dir_path = Path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning(f"Directory not found: {directory}")
            return []

        results = []
        supported = set(get_supported_extensions())

        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported:
                result = await self._process_file(file_path, project_id)
                if result:
                    results.append(result)

        return results

    async def start(self) -> None:
        """Start watching all configured directories."""
        self._running = True
        logger.info(f"File watcher started. Watching {len(self._watched_dirs)} directories.")

        # Initial scan of all watched directories
        for directory, project_id in self._watched_dirs.items():
            await self.scan_directory(directory, project_id)

        # Watch for changes
        dirs_to_watch = [d for d in self._watched_dirs if Path(d).exists()]
        if not dirs_to_watch:
            # No directories to watch — just sleep and periodically check for new watches
            while self._running:
                await asyncio.sleep(10)
                dirs_to_watch = [d for d in self._watched_dirs if Path(d).exists()]
                if dirs_to_watch:
                    break

        if not self._running:
            return

        try:
            async for changes in awatch(*dirs_to_watch):
                if not self._running:
                    break

                for change_type, path_str in changes:
                    if change_type in (Change.added, Change.modified):
                        file_path = Path(path_str)
                        if not file_path.is_file():
                            continue

                        # Find which project this file belongs to
                        for watch_dir, project_id in self._watched_dirs.items():
                            if str(file_path).startswith(watch_dir):
                                await self._process_file(file_path, project_id)
                                break
        except asyncio.CancelledError:
            logger.info("File watcher cancelled.")

    def stop(self) -> None:
        """Stop the file watcher."""
        self._running = False
        logger.info("File watcher stopped.")
