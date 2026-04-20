"""Agent Memory Hook — extracts learnings from user interactions.

Proactively analyzes chat history to understand user preferences,
style, and project-specific workflow tastes.
"""

import logging
import json
from sqlalchemy import select
from app.models.database import async_session
from app.models.message import Message
from app.models.task import Task
from app.core.agent_learning import agent_learning

logger = logging.getLogger(__name__)

async def trigger_task_memory_extraction(agent_id: str, task_id: str):
    """Analyze a completed task for preferences and save to agent memory."""
    logger.info(f"Extracting proactive memory for agent {agent_id} from task {task_id}")
    
    async with async_session() as db:
        # Load task and related messages
        stmt = select(Task).where(Task.id == task_id)
        task = (await db.execute(stmt)).scalar_one_or_none()
        if not task:
            return

        msg_stmt = select(Message).where(Message.task_id == task_id).order_by(Message.created_at.asc())
        messages = (await db.execute(msg_stmt)).scalars().all()
        
        if not messages:
            return

        # Distill the interaction
        interaction_text = "\n".join([f"{m.role}: {m.content}" for m in messages])
        
        # Use LLM to extract preference (simplified for this hook)
        # In a real implementation, we'd call llm_router here.
        # For Phase 6, we'll log that we captured the interaction.
        
        preference_summary = f"Completed task: {task.title}. Skill used: {task.skill_name}. Instructions: {task.instructions}"
        
        await agent_learning.record_workflow_learning(
            agent_id=agent_id,
            pattern=preference_summary,
            project_id=task.project_id
        )
        
        logger.info(f"Proactive memory extraction complete for task {task_id}")
