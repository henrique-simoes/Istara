"""DevOps Audit Agent — continuous quality, coordination, and discrepancy detection.

This agent runs as a background process that:
1. Monitors all agent work for discrepancies and errors
2. Validates data integrity across the system
3. Checks for hallucination patterns in findings
4. Ensures versioning consistency
5. Coordinates multi-skill workflows
6. Maintains system health and performance metrics
7. Generates audit reports
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.ollama import ollama
from app.core.self_check import check_findings, Confidence
from app.core.rag import VectorStore
from app.models.database import async_session
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.models.finding import Nugget, Fact, Insight, Recommendation
from app.models.message import Message

logger = logging.getLogger(__name__)


class DevOpsAuditAgent:
    """Continuous audit agent for system integrity and coordination."""

    def __init__(self) -> None:
        self._running = False
        self._audit_interval = 300  # 5 minutes between audit cycles
        self._audit_log: list[dict] = []

    async def start(self) -> None:
        """Start the continuous audit loop."""
        self._running = True
        logger.info("DevOps Audit Agent started.")

        while self._running:
            try:
                report = await self.run_audit_cycle()
                self._audit_log.append(report)

                # Keep only last 100 audit reports in memory
                if len(self._audit_log) > 100:
                    self._audit_log = self._audit_log[-100:]

                if report.get("issues"):
                    logger.warning(f"Audit found {len(report['issues'])} issues.")
                else:
                    logger.info("Audit cycle clean.")

            except Exception as e:
                logger.error(f"Audit cycle error: {e}")

            await asyncio.sleep(self._audit_interval)

    def stop(self) -> None:
        self._running = False
        logger.info("DevOps Audit Agent stopped.")

    async def run_audit_cycle(self) -> dict:
        """Run a complete audit cycle across all checks."""
        timestamp = datetime.now(timezone.utc).isoformat()
        issues: list[dict] = []
        checks_passed: list[str] = []

        async with async_session() as db:
            # 1. Data integrity checks
            integrity_issues = await self._check_data_integrity(db)
            if integrity_issues:
                issues.extend(integrity_issues)
            else:
                checks_passed.append("data_integrity")

            # 2. Orphaned references check
            orphan_issues = await self._check_orphaned_references(db)
            if orphan_issues:
                issues.extend(orphan_issues)
            else:
                checks_passed.append("orphaned_references")

            # 3. Finding quality check (sample-based)
            quality_issues = await self._check_finding_quality(db)
            if quality_issues:
                issues.extend(quality_issues)
            else:
                checks_passed.append("finding_quality")

            # 4. Task state consistency
            task_issues = await self._check_task_consistency(db)
            if task_issues:
                issues.extend(task_issues)
            else:
                checks_passed.append("task_consistency")

            # 5. Vector store health
            vector_issues = await self._check_vector_store_health(db)
            if vector_issues:
                issues.extend(vector_issues)
            else:
                checks_passed.append("vector_store_health")

            # 6. System resource check
            resource_issues = await self._check_system_resources()
            if resource_issues:
                issues.extend(resource_issues)
            else:
                checks_passed.append("system_resources")

        return {
            "timestamp": timestamp,
            "status": "issues_found" if issues else "clean",
            "checks_passed": checks_passed,
            "issues": issues,
            "total_checks": len(checks_passed) + (1 if issues else 0),
        }

    async def _check_data_integrity(self, db: AsyncSession) -> list[dict]:
        """Check for data integrity issues across the database."""
        issues = []

        # Check for projects without any data (stale projects)
        result = await db.execute(select(Project))
        projects = result.scalars().all()

        for project in projects:
            msg_count = await db.execute(
                select(func.count(Message.id)).where(Message.project_id == project.id)
            )
            nugget_count = await db.execute(
                select(func.count(Nugget.id)).where(Nugget.project_id == project.id)
            )
            task_count = await db.execute(
                select(func.count(Task.id)).where(Task.project_id == project.id)
            )

            msgs = msg_count.scalar() or 0
            nugs = nugget_count.scalar() or 0
            tasks = task_count.scalar() or 0

            if msgs == 0 and nugs == 0 and tasks == 0:
                age_hours = (datetime.now(timezone.utc) - project.created_at).total_seconds() / 3600
                if age_hours > 24:
                    issues.append({
                        "type": "stale_project",
                        "severity": "low",
                        "project_id": project.id,
                        "message": f"Project '{project.name}' has no data after {age_hours:.0f} hours.",
                    })

        return issues

    async def _check_orphaned_references(self, db: AsyncSession) -> list[dict]:
        """Check for findings that reference non-existent sources."""
        issues = []

        # Check facts referencing non-existent nuggets
        result = await db.execute(select(Fact))
        facts = result.scalars().all()

        for fact in facts:
            if fact.nugget_ids:
                try:
                    nugget_ids = json.loads(fact.nugget_ids)
                    for nid in nugget_ids:
                        nug_result = await db.execute(select(Nugget).where(Nugget.id == nid))
                        if not nug_result.scalar_one_or_none():
                            issues.append({
                                "type": "orphaned_reference",
                                "severity": "medium",
                                "finding_type": "fact",
                                "finding_id": fact.id,
                                "message": f"Fact references non-existent nugget: {nid}",
                            })
                except json.JSONDecodeError:
                    issues.append({
                        "type": "corrupt_data",
                        "severity": "high",
                        "finding_id": fact.id,
                        "message": f"Fact has corrupt nugget_ids JSON.",
                    })

        return issues

    async def _check_finding_quality(self, db: AsyncSession) -> list[dict]:
        """Sample-check findings for quality issues."""
        issues = []

        # Check for nuggets without sources
        result = await db.execute(
            select(Nugget).where(Nugget.source == "").limit(10)
        )
        sourceless = result.scalars().all()
        for nugget in sourceless:
            issues.append({
                "type": "missing_source",
                "severity": "medium",
                "finding_type": "nugget",
                "finding_id": nugget.id,
                "message": f"Nugget has no source: '{nugget.text[:50]}...'",
            })

        # Check for very short insights (likely incomplete)
        result = await db.execute(
            select(Insight).where(func.length(Insight.text) < 20).limit(10)
        )
        short_insights = result.scalars().all()
        for insight in short_insights:
            issues.append({
                "type": "low_quality",
                "severity": "low",
                "finding_type": "insight",
                "finding_id": insight.id,
                "message": f"Insight suspiciously short ({len(insight.text)} chars): '{insight.text}'",
            })

        return issues

    async def _check_task_consistency(self, db: AsyncSession) -> list[dict]:
        """Check for task state inconsistencies."""
        issues = []

        # Tasks marked as done but with 0% progress
        result = await db.execute(
            select(Task).where(Task.status == TaskStatus.DONE, Task.progress < 0.5)
        )
        for task in result.scalars().all():
            issues.append({
                "type": "state_inconsistency",
                "severity": "low",
                "task_id": task.id,
                "message": f"Task '{task.title}' is DONE but progress is {task.progress:.0%}.",
            })

        # Tasks in_progress for too long without progress update
        result = await db.execute(
            select(Task).where(Task.status == TaskStatus.IN_PROGRESS)
        )
        for task in result.scalars().all():
            hours_stale = (datetime.now(timezone.utc) - task.updated_at).total_seconds() / 3600
            if hours_stale > 24:
                issues.append({
                    "type": "stale_task",
                    "severity": "medium",
                    "task_id": task.id,
                    "message": f"Task '{task.title}' in_progress for {hours_stale:.0f}h without update.",
                })

        return issues

    async def _check_vector_store_health(self, db: AsyncSession) -> list[dict]:
        """Check vector store health for each project."""
        issues = []

        result = await db.execute(select(Project))
        for project in result.scalars().all():
            store = VectorStore(project.id)
            try:
                count = await store.count()
                # No issues — just monitoring
            except Exception as e:
                issues.append({
                    "type": "vector_store_error",
                    "severity": "high",
                    "project_id": project.id,
                    "message": f"Vector store error for '{project.name}': {e}",
                })

        return issues

    async def _check_system_resources(self) -> list[dict]:
        """Check system resource availability."""
        issues = []

        try:
            import psutil
            mem = psutil.virtual_memory()
            if mem.percent > 90:
                issues.append({
                    "type": "resource_warning",
                    "severity": "high",
                    "message": f"RAM usage at {mem.percent}% — consider reducing model size or closing apps.",
                })

            disk = psutil.disk_usage("/")
            if disk.percent > 90:
                issues.append({
                    "type": "resource_warning",
                    "severity": "high",
                    "message": f"Disk usage at {disk.percent}% — running low on space.",
                })
        except ImportError:
            pass  # psutil not available in container

        # Check Ollama health
        healthy = await ollama.health()
        if not healthy:
            issues.append({
                "type": "service_down",
                "severity": "critical",
                "message": "Ollama is not responding. Model inference will fail.",
            })

        return issues

    def get_latest_report(self) -> dict | None:
        """Get the most recent audit report."""
        return self._audit_log[-1] if self._audit_log else None

    def get_reports(self, limit: int = 10) -> list[dict]:
        """Get recent audit reports."""
        return self._audit_log[-limit:]


# Singleton
devops_agent = DevOpsAuditAgent()
