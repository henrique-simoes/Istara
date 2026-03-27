"""Research Deployment Service — orchestrates interviews, surveys, diary studies via messaging."""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel_conversation import ChannelConversation
from app.models.channel_instance import ChannelInstance
from app.models.channel_message import ChannelMessage
from app.models.finding import Nugget
from app.models.research_deployment import ResearchDeployment

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Deployment CRUD
# ---------------------------------------------------------------------------


async def create_deployment(
    db: AsyncSession,
    project_id: str,
    name: str,
    deployment_type: str,
    questions: list[dict],
    channel_instance_ids: list[str],
    config: dict | None = None,
    target_responses: int = 0,
) -> ResearchDeployment:
    """Create a new research deployment."""
    deployment = ResearchDeployment(
        id=str(uuid.uuid4()),
        project_id=project_id,
        name=name,
        deployment_type=deployment_type,
        questions_json=json.dumps(questions),
        config_json=json.dumps(config or {}),
        channel_instance_ids_json=json.dumps(channel_instance_ids),
        target_responses=target_responses,
    )
    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)
    logger.info("Created deployment %s (%s) for project %s", deployment.id, name, project_id)
    return deployment


async def get_deployment(db: AsyncSession, deployment_id: str) -> ResearchDeployment | None:
    """Fetch a single deployment by id."""
    return await db.get(ResearchDeployment, deployment_id)


async def list_deployments(
    db: AsyncSession, project_id: str | None = None
) -> list[ResearchDeployment]:
    """List deployments, optionally filtered by project."""
    query = select(ResearchDeployment).order_by(ResearchDeployment.created_at.desc())
    if project_id:
        query = query.where(ResearchDeployment.project_id == project_id)
    result = await db.execute(query)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


async def activate_deployment(db: AsyncSession, deployment_id: str) -> dict:
    """Activate a deployment — marks it ready to receive responses."""
    deployment = await db.get(ResearchDeployment, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found")

    deployment.state = "active"

    questions = json.loads(deployment.questions_json)
    config = json.loads(deployment.config_json)
    intro = config.get(
        "intro_message",
        f"Hi! We're conducting a {deployment.deployment_type}. Your responses are valuable to us.",
    )
    first_q = questions[0]["text"] if questions else "Please share your thoughts."

    channel_ids = json.loads(deployment.channel_instance_ids_json)

    await db.commit()
    logger.info("Activated deployment %s across %d channel(s)", deployment_id, len(channel_ids))
    return {
        "status": "activated",
        "deployment_id": deployment_id,
        "intro": intro,
        "first_question": first_q,
        "channels": channel_ids,
    }


async def pause_deployment(db: AsyncSession, deployment_id: str) -> dict:
    """Pause a deployment — no new messages are sent to participants."""
    deployment = await db.get(ResearchDeployment, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found")
    deployment.state = "paused"
    await db.commit()
    logger.info("Paused deployment %s", deployment_id)
    return {"status": "paused", "deployment_id": deployment_id}


async def complete_deployment(db: AsyncSession, deployment_id: str) -> dict:
    """Mark a deployment as completed."""
    deployment = await db.get(ResearchDeployment, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment {deployment_id} not found")
    deployment.state = "completed"
    await db.commit()
    logger.info("Completed deployment %s", deployment_id)
    return {"status": "completed", "deployment_id": deployment_id}


# ---------------------------------------------------------------------------
# Response handling
# ---------------------------------------------------------------------------


async def handle_response(
    db: AsyncSession,
    deployment_id: str,
    conversation_id: str,
    message_text: str,
) -> dict:
    """Process a participant response and determine the next action.

    Returns a dict with an 'action' key:
    - next_question: more questions remain
    - ask_followup: adaptive follow-up generated
    - complete: all questions answered
    - error: something went wrong
    """
    conversation = await db.get(ChannelConversation, conversation_id)
    deployment = await db.get(ResearchDeployment, deployment_id)
    if not conversation or not deployment:
        return {"action": "error", "error": "Conversation or deployment not found"}

    questions = json.loads(deployment.questions_json)
    config = json.loads(deployment.config_json)

    # Determine which question was just answered
    q_index = conversation.current_question_index
    q_text = questions[q_index]["text"] if q_index < len(questions) else "follow-up"

    # Create a nugget from the response
    nugget = Nugget(
        id=str(uuid.uuid4()),
        project_id=deployment.project_id,
        text=f"Q: {q_text}\nA: {message_text}",
        source=f"deployment:{deployment.name}",
        source_location=f"conversation:{conversation_id}",
        tags=json.dumps([deployment.deployment_type, "channel-research"]),
    )
    db.add(nugget)

    # Advance question index
    conversation.current_question_index += 1
    conversation.last_message_at = datetime.now(timezone.utc)

    # Check if all scripted questions have been answered
    if conversation.current_question_index >= len(questions):
        # Adaptive follow-ups
        if config.get("adaptive", False):
            follow_up = await _generate_adaptive_followup(
                db, deployment, conversation, message_text
            )
            if follow_up:
                await db.commit()
                return {"action": "ask_followup", "question": follow_up, "nugget_id": nugget.id}

        # Mark completed
        conversation.state = "completed"
        conversation.completed_at = datetime.now(timezone.utc)
        deployment.current_responses += 1
        await db.commit()
        return {
            "action": "complete",
            "thank_you": config.get(
                "thank_you_message", "Thank you for your responses!"
            ),
            "nugget_id": nugget.id,
        }

    # Send next question
    next_q = questions[conversation.current_question_index]
    await db.commit()
    return {
        "action": "next_question",
        "question": next_q["text"],
        "question_index": conversation.current_question_index,
        "nugget_id": nugget.id,
    }


async def _generate_adaptive_followup(
    db: AsyncSession,
    deployment: ResearchDeployment,
    conversation: ChannelConversation,
    last_response: str,
) -> str | None:
    """Use LLM to generate adaptive follow-up questions based on conversation context."""
    config = json.loads(deployment.config_json)
    max_followups = config.get("max_followups", 3)
    questions = json.loads(deployment.questions_json)
    followup_count = conversation.current_question_index - len(questions)
    if followup_count >= max_followups:
        return None

    try:
        from app.core.llm_router import llm_router

        prompt = (
            f"You are a UX researcher conducting a {deployment.deployment_type}.\n"
            f'The participant just answered: "{last_response}"\n'
            f"Research goals: {config.get('research_goals', 'Understand user experience')}\n\n"
            "Based on this response, generate ONE follow-up question that would "
            "clarify or deepen the insight.\n"
            'If the response is clear and complete, respond with "NONE".\n'
            "Only output the question text, nothing else."
        )

        result = await llm_router.chat([{"role": "user", "content": prompt}])
        followup = result.get("content", "").strip()
        if followup and followup.upper() != "NONE":
            return followup
    except Exception as e:
        logger.warning("Adaptive follow-up generation failed: %s", e)
    return None


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


async def get_deployment_analytics(db: AsyncSession, deployment_id: str) -> dict:
    """Get comprehensive analytics for a deployment."""
    deployment = await db.get(ResearchDeployment, deployment_id)
    if not deployment:
        return {}

    # Get conversations for this deployment
    result = await db.execute(
        select(ChannelConversation).where(
            ChannelConversation.deployment_id == deployment_id
        )
    )
    conversations = list(result.scalars().all())

    # Get messages for these conversations
    conv_ids = [c.id for c in conversations]
    messages: list[ChannelMessage] = []
    if conv_ids:
        msg_result = await db.execute(
            select(ChannelMessage).where(ChannelMessage.thread_id.in_(conv_ids))
        )
        messages = list(msg_result.scalars().all())

    questions = json.loads(deployment.questions_json)

    # Per-question stats
    per_question_stats = []
    for i, q in enumerate(questions):
        responses_for_q = [c for c in conversations if c.current_question_index > i]
        per_question_stats.append(
            {
                "index": i,
                "text": q.get("text", ""),
                "response_count": len(responses_for_q),
                "skip_count": len(conversations) - len(responses_for_q),
            }
        )

    completed = [c for c in conversations if c.state == "completed"]
    active = [c for c in conversations if c.state == "active"]
    failed = [c for c in conversations if c.state in ("expired", "error")]

    # Average completion time
    completion_times = []
    for c in completed:
        if c.completed_at and c.started_at:
            delta = (c.completed_at - c.started_at).total_seconds()
            completion_times.append(delta)
    avg_completion_seconds = (
        sum(completion_times) / len(completion_times) if completion_times else 0
    )

    response_rate = (
        len(completed) / len(conversations) * 100 if conversations else 0
    )
    completion_rate = (
        len(completed) / deployment.target_responses * 100
        if deployment.target_responses
        else 0
    )

    return {
        "deployment_id": deployment_id,
        "deployment_name": deployment.name,
        "deployment_type": deployment.deployment_type,
        "state": deployment.state,
        "target_responses": deployment.target_responses,
        "current_responses": deployment.current_responses,
        "response_rate": round(response_rate, 1),
        "completion_rate": round(min(completion_rate, 100), 1),
        "active_conversations": len(active),
        "completed_conversations": len(completed),
        "failed_conversations": len(failed),
        "total_conversations": len(conversations),
        "total_messages": len(messages),
        "avg_completion_seconds": round(avg_completion_seconds, 1),
        "per_question_stats": per_question_stats,
        "most_answered_questions": sorted(
            per_question_stats, key=lambda x: x["response_count"], reverse=True
        ),
        "least_answered_questions": sorted(
            per_question_stats, key=lambda x: x["response_count"]
        ),
    }


async def get_deployment_overview(db: AsyncSession, project_id: str) -> dict:
    """Cross-deployment summary for a project."""
    result = await db.execute(
        select(ResearchDeployment).where(
            ResearchDeployment.project_id == project_id
        )
    )
    deployments = list(result.scalars().all())
    active = [d for d in deployments if d.state == "active"]

    # Count conversations in last 24h
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    conv_result = await db.execute(
        select(func.count(ChannelConversation.id)).where(
            ChannelConversation.started_at >= cutoff
        )
    )
    recent_conversations = conv_result.scalar() or 0

    return {
        "total_deployments": len(deployments),
        "active_deployments": [
            {
                "id": d.id,
                "name": d.name,
                "type": d.deployment_type,
                "state": d.state,
                "progress": round(
                    d.current_responses / d.target_responses * 100
                    if d.target_responses
                    else 0,
                    1,
                ),
                "current_responses": d.current_responses,
                "target_responses": d.target_responses,
            }
            for d in active
        ],
        "completed_deployments": len(
            [d for d in deployments if d.state == "completed"]
        ),
        "last_24h_conversations_initiated": recent_conversations,
    }


# ---------------------------------------------------------------------------
# Conversation helpers
# ---------------------------------------------------------------------------


async def list_conversations(
    db: AsyncSession, deployment_id: str
) -> list[ChannelConversation]:
    """List all conversations for a deployment."""
    result = await db.execute(
        select(ChannelConversation)
        .where(ChannelConversation.deployment_id == deployment_id)
        .order_by(ChannelConversation.started_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation(
    db: AsyncSession, conversation_id: str
) -> ChannelConversation | None:
    """Get a single conversation by id."""
    return await db.get(ChannelConversation, conversation_id)


async def get_conversation_transcript(
    db: AsyncSession, conversation_id: str
) -> list[dict]:
    """Get the full message transcript for a conversation."""
    result = await db.execute(
        select(ChannelMessage)
        .where(ChannelMessage.thread_id == conversation_id)
        .order_by(ChannelMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [m.to_dict() for m in messages]
