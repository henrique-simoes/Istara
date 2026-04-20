"""Inbound Message Processor — bridges ChannelRouter to Adaptive Interview Engine.

This service acts as the 'brain' for incoming messages from all platforms
(Telegram, WhatsApp, Slack). It manages the conversational state machine
defined in adaptive_interview.py.
"""

import json
import logging
from sqlalchemy import select
from app.models.database import async_session
from app.models.channel_conversation import ChannelConversation
from app.models.research_deployment import ResearchDeployment
from app.models.channel_message import ChannelMessage
from app.services.adaptive_interview import get_next_action, update_conversation_metadata
from app.api.websocket import broadcast_channel_status

logger = logging.getLogger(__name__)

async def process_inbound_message(instance_id: str, platform: str, sender_id: str, text: str, metadata: dict = None) -> None:
    """The global handler for all inbound channel messages."""
    logger.info("Processing inbound %s message from %s", platform, sender_id)
    
    async with async_session() as db:
        # 1. Find the first active deployment (simplified mapping)
        stmt = select(ResearchDeployment).where(ResearchDeployment.status == "active")
        result = await db.execute(stmt)
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            logger.debug("No active deployment found for incoming message")
            return

        # 2. Find/Create conversation
        stmt = select(ChannelConversation).where(
            ChannelConversation.deployment_id == deployment.id,
            ChannelConversation.participant_id == sender_id
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            from datetime import datetime, timezone
            conversation = ChannelConversation(
                deployment_id=deployment.id,
                participant_id=sender_id,
                participant_name=sender_id,
                state="intro",
                current_question_index=0,
                created_at=datetime.now(timezone.utc)
            )
            db.add(conversation)
            await db.flush()
        
        # 3. Persist the inbound message
        inbound_msg = ChannelMessage(
            instance_id=instance_id,
            thread_id=conversation.id,
            sender_type="participant",
            content=text,
            metadata_json=json.dumps(metadata or {})
        )
        db.add(inbound_msg)
        
        # 4. Get next action from adaptive engine
        action = await get_next_action(conversation, deployment, text)
        
        if action["action"] == "send_message":
            # 5. Send response back
            from app.channels.base import channel_router
            success = await channel_router.send_message(instance_id, sender_id, action["text"])
            
            if success:
                # Persist outbound message
                outbound_msg = ChannelMessage(
                    instance_id=instance_id,
                    thread_id=conversation.id,
                    sender_type="agent",
                    content=action["text"]
                )
                db.add(outbound_msg)
                
                # Update conversation state
                conversation.state = action["state"]
                if "question_index" in action:
                    conversation.current_question_index = action["question_index"]
                if "metadata" in action:
                    update_conversation_metadata(conversation, action["metadata"])
                    
        elif action["action"] == "complete":
            # Send final message if provided
            if action.get("text"):
                from app.channels.base import channel_router
                await channel_router.send_message(instance_id, sender_id, action["text"])
            conversation.state = "completed"
            
        await db.commit()
        
        # 6. Notify frontend
        await broadcast_channel_status(instance_id, "active", f"Processed message from {sender_id}")
