"""Reporting Worker — autonomous drafting of research reports.

Drafts Layer 2/3/4 reports when tasks are marked DONE.
Uses the MECE/Pyramid logic from ReportManager.
"""

import logging
import asyncio
from app.models.database import async_session
from app.core.report_manager import report_manager

logger = logging.getLogger(__name__)

async def spawn_report_drafting(project_id: str, task_id: str):
    """Background task to draft reports after task completion."""
    logger.info(f"Triggering autonomous report drafting for project {project_id} (task {task_id})")
    
    # Wait a moment for any last-minute DB flushes/finding migrations
    await asyncio.sleep(2)
    
    async with async_session() as db:
        try:
            # ReportManager already has check_synthesis_trigger which handles L3/L4
            # We just need to trigger the initial findings routing if it hasn't been done
            # or specifically tell it to refine the reports for this project.
            await report_manager._check_synthesis_trigger(project_id, db)
            logger.info(f"Autonomous reporting cycle completed for {project_id}")
        except Exception as e:
            logger.error(f"Autonomous reporting failed for {project_id}: {e}")
