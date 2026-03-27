"""Adaptive Interview Engine — AURA-style conversational state machine for research deployments.

Manages the flow of multi-turn research interviews with adaptive probing,
rate limiting, and LLM-judged saturation detection.

Conversation states: intro -> questions -> probing -> wrap_up -> completed
"""

import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel_conversation import ChannelConversation
from app.models.research_deployment import ResearchDeployment

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """State machine states for a research conversation."""

    INTRO = "intro"
    QUESTIONS = "questions"
    PROBING = "probing"
    WRAP_UP = "wrap_up"
    COMPLETED = "completed"


# ---------------------------------------------------------------------------
# Action helpers
# ---------------------------------------------------------------------------


def _build_action(
    action_type: str,
    text: str,
    *,
    state: str = "",
    question_index: int | None = None,
    metadata: dict | None = None,
) -> dict:
    """Build a standardized action dict."""
    result: dict = {"action": action_type, "text": text}
    if state:
        result["state"] = state
    if question_index is not None:
        result["question_index"] = question_index
    if metadata:
        result["metadata"] = metadata
    return result


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------


async def get_next_action(
    conversation: ChannelConversation,
    deployment: ResearchDeployment,
    last_message: str,
) -> dict:
    """Determine the next action based on the current conversation state.

    Returns a dict with:
    - action: "send_message" | "complete" | "wait"
    - text: the message text to send (if applicable)
    - state: the new conversation state
    - question_index: (optional) index of the question being asked
    """
    questions = json.loads(deployment.questions_json)
    config = json.loads(deployment.config_json)
    metadata = _parse_metadata(conversation)
    current_state = metadata.get("state", ConversationState.INTRO)

    # Rate limiting — check if we need to wait between questions
    delay_seconds = config.get("delay_between_questions", 0)
    if delay_seconds > 0:
        last_sent = metadata.get("last_sent_at", 0)
        elapsed = time.time() - last_sent
        if elapsed < delay_seconds:
            return _build_action(
                "wait",
                "",
                state=current_state,
                metadata={"wait_seconds": round(delay_seconds - elapsed, 1)},
            )

    # --- State machine transitions ---

    if current_state == ConversationState.INTRO:
        return _handle_intro(config, questions, metadata)

    if current_state == ConversationState.QUESTIONS:
        return await _handle_questions(
            conversation, deployment, questions, config, metadata, last_message
        )

    if current_state == ConversationState.PROBING:
        return await _handle_probing(
            conversation, deployment, config, metadata, last_message
        )

    if current_state == ConversationState.WRAP_UP:
        return _handle_wrap_up(config, metadata)

    # Already completed
    return _build_action("complete", "", state=ConversationState.COMPLETED)


def _handle_intro(config: dict, questions: list[dict], metadata: dict) -> dict:
    """Handle the intro state — send greeting and first question."""
    intro_message = config.get(
        "intro_message",
        "Hi! Thank you for participating in this research study. "
        "Your responses will help us improve our product.",
    )

    if questions:
        text = f"{intro_message}\n\nLet's begin:\n{questions[0]['text']}"
        metadata["state"] = ConversationState.QUESTIONS
        metadata["last_sent_at"] = time.time()
        return _build_action(
            "send_message",
            text,
            state=ConversationState.QUESTIONS,
            question_index=0,
            metadata=metadata,
        )

    # No questions — go straight to wrap-up
    metadata["state"] = ConversationState.WRAP_UP
    return _build_action(
        "send_message",
        intro_message,
        state=ConversationState.WRAP_UP,
        metadata=metadata,
    )


async def _handle_questions(
    conversation: ChannelConversation,
    deployment: ResearchDeployment,
    questions: list[dict],
    config: dict,
    metadata: dict,
    last_message: str,
) -> dict:
    """Handle the questions state — advance to next question or transition to probing."""
    q_index = conversation.current_question_index

    # Check if we should probe the current answer before moving on
    if config.get("adaptive", False) and last_message:
        needs_probe = await _should_probe(deployment, last_message, config)
        if needs_probe:
            clarification = await generate_clarification(conversation, last_message, config)
            if clarification:
                metadata["state"] = ConversationState.PROBING
                metadata["probe_count"] = metadata.get("probe_count", 0) + 1
                metadata["last_sent_at"] = time.time()
                return _build_action(
                    "send_message",
                    clarification,
                    state=ConversationState.PROBING,
                    question_index=q_index,
                    metadata=metadata,
                )

    # Move to next question
    if q_index < len(questions):
        metadata["last_sent_at"] = time.time()
        return _build_action(
            "send_message",
            questions[q_index]["text"],
            state=ConversationState.QUESTIONS,
            question_index=q_index,
            metadata=metadata,
        )

    # All questions done — wrap up
    metadata["state"] = ConversationState.WRAP_UP
    return _handle_wrap_up(config, metadata)


async def _handle_probing(
    conversation: ChannelConversation,
    deployment: ResearchDeployment,
    config: dict,
    metadata: dict,
    last_message: str,
) -> dict:
    """Handle the probing state — continue probing or return to questions."""
    max_probes = config.get("max_probes_per_question", 2)
    probe_count = metadata.get("probe_count", 0)

    # Check saturation
    if probe_count >= max_probes or await _is_saturated(last_message, config):
        # Return to questions flow
        metadata["state"] = ConversationState.QUESTIONS
        metadata["probe_count"] = 0
        questions = json.loads(deployment.questions_json)
        q_index = conversation.current_question_index

        if q_index < len(questions):
            metadata["last_sent_at"] = time.time()
            return _build_action(
                "send_message",
                questions[q_index]["text"],
                state=ConversationState.QUESTIONS,
                question_index=q_index,
                metadata=metadata,
            )
        # All questions done
        metadata["state"] = ConversationState.WRAP_UP
        return _handle_wrap_up(config, metadata)

    # Generate another probe
    clarification = await generate_clarification(conversation, last_message, config)
    if clarification:
        metadata["probe_count"] = probe_count + 1
        metadata["last_sent_at"] = time.time()
        return _build_action(
            "send_message",
            clarification,
            state=ConversationState.PROBING,
            metadata=metadata,
        )

    # Probe generation failed — move on
    metadata["state"] = ConversationState.QUESTIONS
    metadata["probe_count"] = 0
    return _build_action(
        "send_message",
        "",
        state=ConversationState.QUESTIONS,
        metadata=metadata,
    )


def _handle_wrap_up(config: dict, metadata: dict) -> dict:
    """Handle the wrap-up state — send closing message."""
    thank_you = config.get(
        "thank_you_message",
        "Thank you for your time and thoughtful responses! Your input is invaluable.",
    )
    closing = config.get("closing_question", "")
    text = f"{closing}\n\n{thank_you}" if closing else thank_you

    metadata["state"] = ConversationState.COMPLETED
    metadata["last_sent_at"] = time.time()
    return _build_action(
        "complete",
        text,
        state=ConversationState.COMPLETED,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Clarification / probing
# ---------------------------------------------------------------------------


async def generate_clarification(
    conversation: ChannelConversation,
    response: str,
    config: dict | None = None,
) -> str | None:
    """Use LLM to generate a probing/clarification question based on the response."""
    config = config or {}
    research_goals = config.get("research_goals", "Understand user experience and needs")
    deployment_type = config.get("deployment_type", "interview")

    try:
        from app.core.llm_router import llm_router

        prompt = (
            f"You are an expert UX researcher conducting a {deployment_type}.\n"
            f'The participant just said: "{response}"\n'
            f"Research goals: {research_goals}\n\n"
            "Generate ONE short, empathetic follow-up question that:\n"
            "- Asks the participant to elaborate on a specific detail\n"
            "- Uses open-ended phrasing (avoid yes/no questions)\n"
            "- Feels natural and conversational\n\n"
            'If the response is already clear and complete, respond with "NONE".\n'
            "Only output the question text, nothing else."
        )

        result = await llm_router.chat([{"role": "user", "content": prompt}])
        content = result.get("content", "").strip()
        if content and content.upper() != "NONE":
            return content
    except Exception as e:
        logger.warning("Clarification generation failed: %s", e)
    return None


# ---------------------------------------------------------------------------
# Saturation & probing heuristics
# ---------------------------------------------------------------------------


async def _should_probe(
    deployment: ResearchDeployment,
    response: str,
    config: dict,
) -> bool:
    """Determine whether the response warrants a probing follow-up.

    Uses a simple heuristic: short responses (< min_words) often benefit
    from probing. Longer, detailed responses do not.
    """
    min_words = config.get("min_words_for_skip_probe", 15)
    word_count = len(response.split())
    if word_count >= min_words:
        return False
    return True


async def _is_saturated(response: str, config: dict) -> bool:
    """Check if the probing has reached saturation.

    Uses LLM to judge whether further probing would yield new information.
    Falls back to a word-count heuristic if LLM is unavailable.
    """
    if config.get("saturation_check_llm", False):
        try:
            from app.core.llm_router import llm_router

            prompt = (
                "A research participant just gave this response to a follow-up probe:\n"
                f'"{response}"\n\n'
                "Has this response added meaningful new information, or is the "
                "participant repeating themselves / giving minimal answers?\n"
                'Respond with exactly "SATURATED" or "NOT_SATURATED".'
            )
            result = await llm_router.chat([{"role": "user", "content": prompt}])
            content = result.get("content", "").strip().upper()
            return "SATURATED" in content
        except Exception:
            pass

    # Heuristic fallback: very short probe responses suggest saturation
    return len(response.split()) < 5


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------


def _parse_metadata(conversation: ChannelConversation) -> dict:
    """Parse the conversation's metadata_json field."""
    try:
        return json.loads(conversation.metadata_json) if conversation.metadata_json else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def update_conversation_metadata(
    conversation: ChannelConversation, metadata: dict
) -> None:
    """Update the conversation's metadata_json field in-place."""
    conversation.metadata_json = json.dumps(metadata)
