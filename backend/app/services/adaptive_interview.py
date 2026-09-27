"""Adaptive Interview Engine — AURA-style conversational state machine for research deployments.

Manages the flow of multi-turn research interviews with informed consent, screening, adaptive
probing, rate limiting, and LLM-judged saturation detection.

Conversation states:
intro -> [consent] -> [screening] -> questions <-> probing -> [closing] -> completed,
with the terminal states declined, screened_out, withdrawn and closed_quota.

Every message the engine sends records ``pending_prompt`` in the conversation metadata: the exact
text the participant was shown and what kind of prompt it was. The inbound processor stores a
participant's message as research data only when it answers a pending question, probe or closing
question, so a greeting, a consent reply or a screener answer never becomes an evidence unit.
"""

import json
import logging
import re
import time
from enum import Enum

from app.models.channel_conversation import ChannelConversation
from app.models.research_deployment import ResearchDeployment

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):  # noqa: UP042 -- StrEnum would change str(member)
    """State machine states for a research conversation."""

    INTRO = "intro"
    CONSENT = "consent"
    SCREENING = "screening"
    QUESTIONS = "questions"
    PROBING = "probing"
    WRAP_UP = "wrap_up"
    CLOSING = "closing"
    COMPLETED = "completed"
    DECLINED = "declined"
    SCREENED_OUT = "screened_out"
    WITHDRAWN = "withdrawn"
    CLOSED_QUOTA = "closed_quota"


# Prompt kinds whose replies are research answers (stored as evidence units).
ANSWER_PROMPT_KINDS = frozenset({"question", "probe", "closing"})
# States in which a participant still owes the study a reply (reminders apply).
AWAITING_REPLY_STATES = frozenset(
    {
        ConversationState.CONSENT.value,
        ConversationState.SCREENING.value,
        ConversationState.QUESTIONS.value,
        ConversationState.PROBING.value,
        ConversationState.CLOSING.value,
    }
)
FINISHED_STATES = frozenset(
    {
        ConversationState.COMPLETED.value,
        ConversationState.DECLINED.value,
        ConversationState.SCREENED_OUT.value,
        ConversationState.WITHDRAWN.value,
        ConversationState.CLOSED_QUOTA.value,
    }
)

DEFAULT_CONSENT_MESSAGE = (
    "Before we start: this is a research study. The research team will store and analyse your "
    "answers to improve the product, and may quote them in research reports without your name. "
    "Taking part is voluntary, and you can stop at any time by replying STOP."
)
CONSENT_INSTRUCTION = "Reply YES to take part, or NO if you'd rather not."
DEFAULT_DECLINED_MESSAGE = "No problem, thank you for letting us know. We won't ask you anything else."
DEFAULT_SCREENED_OUT_MESSAGE = (
    "Thank you! This study is looking for a different group of participants, so we won't need "
    "anything else from you."
)
DEFAULT_WITHDRAWN_MESSAGE = (
    "You've left the study. We won't send you anything else or store anything you send here."
)
DEFAULT_QUOTA_FULL_MESSAGE = (
    "Thank you for your interest! This study already has all the participants it needs."
)
DEFAULT_PAUSED_MESSAGE = (
    "This study is paused at the moment. The research team will pick it up again soon; "
    "nothing you send now will be recorded."
)
DEFAULT_REMINDER_MESSAGE = "Just a gentle reminder, whenever you have a moment:"

_YES = {
    "yes", "y", "yeah", "yep", "yes please", "sure", "ok", "okay", "i agree", "agree", "agreed",
    "i consent", "consent", "sim", "si", "sí", "oui", "ja", "👍",
}
_NO = {
    "no", "n", "nope", "no thanks", "no thank you", "não", "nao", "non", "nein", "decline",
    "i decline", "i do not agree", "i don't agree", "i dont agree", "stop",
}
MAX_CONSENT_ATTEMPTS = 2


def _normalise_reply(text: str) -> str:
    cleaned = re.sub(r"[\s\u00a0]+", " ", str(text or "")).strip().casefold()
    return cleaned.strip(" .!?,;:\"'")


def is_withdrawal(text: str) -> bool:
    """A participant leaves the study by sending exactly STOP (any case, punctuation aside)."""
    return _normalise_reply(text) in {"stop", "unsubscribe", "quit study", "withdraw"}


def consent_reply(text: str) -> bool | None:
    """True for a clear yes, False for a clear no, None when the reply is unclear."""
    normalised = _normalise_reply(text)
    if normalised in _YES:
        return True
    if normalised in _NO:
        return False
    return None


def _as_int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _as_float(value: object, default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def normalise_screener(value: object) -> list[dict]:
    """Return screener items as ``[{"text": str, "accept": [str, ...]}]``."""
    items: list[dict] = []
    if not isinstance(value, list):
        return items
    for raw in value:
        if isinstance(raw, str):
            raw = {"text": raw}
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        accept = raw.get("accept") or raw.get("accepted_answers") or []
        if isinstance(accept, str):
            accept = [part for part in accept.split(",")]
        items.append({"text": text, "accept": [str(a).strip() for a in accept if str(a).strip()]})
    return items


def deployment_config(deployment: ResearchDeployment) -> dict:
    """Return the deployment config with canonical keys.

    The deployment wizard saves ``adaptive_enabled`` / ``max_follow_ups``; older rows and the
    channel-deployment skill use ``adaptive`` / ``max_probes_per_question``. Both spellings are
    honoured here so the researcher's setting always takes effect.
    """
    try:
        raw = json.loads(deployment.config_json or "{}")
    except (json.JSONDecodeError, TypeError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    config = dict(raw)
    config["adaptive"] = bool(raw.get("adaptive", raw.get("adaptive_enabled", False)))
    config["max_probes_per_question"] = max(
        0, _as_int(raw.get("max_probes_per_question", raw.get("max_follow_ups", 2)), 2)
    )
    config["consent_required"] = bool(raw.get("consent_required", False))
    config["consent_message"] = str(raw.get("consent_message") or DEFAULT_CONSENT_MESSAGE)
    config["screener"] = normalise_screener(raw.get("screener"))
    config["closing_question"] = str(raw.get("closing_question") or "").strip()
    config["reminder_after_hours"] = max(0.0, _as_float(raw.get("reminder_after_hours", 0), 0.0))
    config["max_reminders"] = max(0, _as_int(raw.get("max_reminders", 1), 1))
    return config


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


def _prompt(
    metadata: dict,
    kind: str,
    text: str,
    *,
    question_index: int | None = None,
) -> None:
    """Record what the participant is being shown, so their reply is attributed to it."""
    metadata["pending_prompt"] = {"kind": kind, "text": text, "question_index": question_index}
    metadata["last_sent_at"] = time.time()


def _send(
    metadata: dict,
    state: ConversationState,
    text: str,
    *,
    kind: str,
    prompt_text: str | None = None,
    question_index: int | None = None,
) -> dict:
    _prompt(metadata, kind, prompt_text if prompt_text is not None else text,
            question_index=question_index)
    metadata["state"] = state.value
    return _build_action(
        "send_message",
        text,
        state=state.value,
        question_index=question_index,
        metadata=metadata,
    )


def _finish(metadata: dict, state: ConversationState, text: str) -> dict:
    metadata.pop("pending_prompt", None)
    metadata["state"] = state.value
    metadata["last_sent_at"] = time.time()
    return _build_action("complete", text, state=state.value, metadata=metadata)


def _question_text(questions: list[dict], index: int) -> str:
    item = questions[index]
    return str(item.get("text") if isinstance(item, dict) else item)


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
    questions = json.loads(deployment.questions_json or "[]")
    config = deployment_config(deployment)
    metadata = _parse_metadata(conversation)
    current_state = metadata.get("state") or conversation.state or ConversationState.INTRO.value
    if current_state == "active":
        current_state = ConversationState.INTRO.value

    if current_state in FINISHED_STATES:
        return _build_action("complete", "", state=current_state)

    # A participant can leave at any point after the study has started talking to them.
    if current_state != ConversationState.INTRO.value and is_withdrawal(last_message):
        metadata["withdrawn_at"] = time.time()
        return _finish(metadata, ConversationState.WITHDRAWN, DEFAULT_WITHDRAWN_MESSAGE)

    # Rate limiting — check if we need to wait between questions
    delay_seconds = _as_float(config.get("delay_between_questions", 0), 0.0)
    if delay_seconds > 0 and current_state not in {
        ConversationState.INTRO.value,
        ConversationState.CONSENT.value,
        ConversationState.SCREENING.value,
    }:
        last_sent = metadata.get("last_sent_at", 0)
        elapsed = time.time() - last_sent
        if elapsed < delay_seconds:
            return _build_action(
                "wait",
                "",
                state=current_state,
                metadata={**metadata, "wait_seconds": round(delay_seconds - elapsed, 1)},
            )

    # --- State machine transitions ---

    if current_state == ConversationState.INTRO.value:
        return _handle_intro(config, questions, metadata)

    if current_state == ConversationState.CONSENT.value:
        return _handle_consent(config, questions, metadata, last_message)

    if current_state == ConversationState.SCREENING.value:
        return _handle_screening(config, questions, metadata, last_message)

    if current_state == ConversationState.QUESTIONS.value:
        return await _handle_questions(
            conversation, deployment, questions, config, metadata, last_message
        )

    if current_state == ConversationState.PROBING.value:
        return await _handle_probing(
            conversation, deployment, questions, config, metadata, last_message
        )

    if current_state == ConversationState.CLOSING.value:
        return _finish(metadata, ConversationState.COMPLETED, _thank_you(config))

    if current_state == ConversationState.WRAP_UP.value:
        return _handle_wrap_up(config, metadata)

    # Already completed
    return _build_action("complete", "", state=ConversationState.COMPLETED.value)


def _intro_message(config: dict) -> str:
    return str(
        config.get("intro_message")
        or "Hi! Thank you for participating in this research study. "
        "Your responses will help us improve our product."
    )


def _thank_you(config: dict) -> str:
    return str(
        config.get("thank_you_message")
        or "Thank you for your time and thoughtful responses! Your input is invaluable."
    )


def _start_screener_or_questions(
    config: dict, questions: list[dict], metadata: dict, *, lead: str = ""
) -> dict:
    prefix = f"{lead}\n\n" if lead else ""
    screener = config.get("screener") or []
    if screener:
        metadata["screener_index"] = 0
        text = screener[0]["text"]
        return _send(
            metadata, ConversationState.SCREENING, f"{prefix}{text}", kind="screener",
            prompt_text=text,
        )
    return _first_question(config, questions, metadata, lead=lead)


def _first_question(config: dict, questions: list[dict], metadata: dict, *, lead: str = "") -> dict:
    if questions:
        text = _question_text(questions, 0)
        body = f"{lead}\n\nLet's begin:\n{text}" if lead else text
        return _send(
            metadata, ConversationState.QUESTIONS, body, kind="question", prompt_text=text,
            question_index=1,
        )
    return _handle_wrap_up(config, metadata, lead=lead)


def _handle_intro(config: dict, questions: list[dict], metadata: dict) -> dict:
    """Send the greeting, then consent, the screener, or the first question."""
    intro_message = _intro_message(config)
    if config.get("consent_required"):
        consent_text = f"{config['consent_message']}\n\n{CONSENT_INSTRUCTION}"
        metadata["consent_attempts"] = 0
        return _send(
            metadata,
            ConversationState.CONSENT,
            f"{intro_message}\n\n{consent_text}",
            kind="consent",
            prompt_text=consent_text,
        )
    return _start_screener_or_questions(config, questions, metadata, lead=intro_message)


def _handle_consent(
    config: dict, questions: list[dict], metadata: dict, last_message: str
) -> dict:
    """Record the participant's consent decision; nothing they send before a yes is stored."""
    decision = consent_reply(last_message)
    if decision is True:
        metadata["consent"] = {"given": True, "at": time.time()}
        return _start_screener_or_questions(config, questions, metadata, lead="Thank you!")
    attempts = int(metadata.get("consent_attempts", 0)) + 1
    metadata["consent_attempts"] = attempts
    if decision is False or attempts >= MAX_CONSENT_ATTEMPTS:
        metadata["consent"] = {"given": False, "at": time.time()}
        return _finish(metadata, ConversationState.DECLINED, DEFAULT_DECLINED_MESSAGE)
    return _send(
        metadata,
        ConversationState.CONSENT,
        f"Sorry, I didn't catch that. {CONSENT_INSTRUCTION}",
        kind="consent",
    )


def _screener_accepts(item: dict, answer: str) -> bool:
    accepted = {_normalise_reply(a) for a in item.get("accept") or []}
    return not accepted or _normalise_reply(answer) in accepted


def _handle_screening(
    config: dict, questions: list[dict], metadata: dict, last_message: str
) -> dict:
    """Ask each screener question; answers go to metadata, never to research evidence."""
    screener = config.get("screener") or []
    index = int(metadata.get("screener_index", 0))
    if index >= len(screener):
        return _first_question(config, questions, metadata)
    item = screener[index]
    qualified = _screener_accepts(item, last_message)
    answers = list(metadata.get("screener_answers") or [])
    answers.append(
        {"question": item["text"], "answer": str(last_message or "").strip(), "qualified": qualified}
    )
    metadata["screener_answers"] = answers
    if not qualified:
        return _finish(
            metadata,
            ConversationState.SCREENED_OUT,
            str(config.get("screened_out_message") or DEFAULT_SCREENED_OUT_MESSAGE),
        )
    index += 1
    metadata["screener_index"] = index
    if index < len(screener):
        return _send(metadata, ConversationState.SCREENING, screener[index]["text"], kind="screener")
    return _first_question(config, questions, metadata, lead="Thanks, you're a great fit.")


def _next_question_or_wrap_up(
    config: dict, questions: list[dict], metadata: dict, q_index: int
) -> dict:
    """Send the question after ``q_index`` (1-based count of questions shown so far)."""
    metadata["probe_count"] = 0
    if q_index < len(questions):
        return _send(
            metadata,
            ConversationState.QUESTIONS,
            _question_text(questions, q_index),
            kind="question",
            question_index=q_index + 1,
        )
    return _handle_wrap_up(config, metadata)


async def _handle_questions(
    conversation: ChannelConversation,
    deployment: ResearchDeployment,
    questions: list[dict],
    config: dict,
    metadata: dict,
    last_message: str,
) -> dict:
    """Handle the questions state — probe the answer or advance to the next question."""
    q_index = conversation.current_question_index

    if config.get("adaptive") and config.get("max_probes_per_question", 0) > 0 and last_message:
        needs_probe = await _should_probe(deployment, last_message, config)
        if needs_probe:
            clarification = await generate_clarification(
                conversation,
                last_message,
                config,
                project_id=deployment.project_id,
            )
            if clarification:
                metadata["probe_count"] = 1
                return _send(
                    metadata,
                    ConversationState.PROBING,
                    clarification,
                    kind="probe",
                    question_index=q_index,
                )

    return _next_question_or_wrap_up(config, questions, metadata, q_index)


async def _handle_probing(
    conversation: ChannelConversation,
    deployment: ResearchDeployment,
    questions: list[dict],
    config: dict,
    metadata: dict,
    last_message: str,
) -> dict:
    """Handle the probing state — probe again, or return to the question flow."""
    max_probes = config.get("max_probes_per_question", 2)
    probe_count = int(metadata.get("probe_count", 0))
    q_index = conversation.current_question_index

    if probe_count >= max_probes or await _is_saturated(
        last_message,
        config,
        project_id=deployment.project_id,
    ):
        return _next_question_or_wrap_up(config, questions, metadata, q_index)

    clarification = await generate_clarification(
        conversation,
        last_message,
        config,
        project_id=deployment.project_id,
    )
    if clarification:
        metadata["probe_count"] = probe_count + 1
        return _send(
            metadata, ConversationState.PROBING, clarification, kind="probe", question_index=q_index
        )

    # Probe generation failed: move on rather than leave the participant waiting on nothing.
    return _next_question_or_wrap_up(config, questions, metadata, q_index)


def _handle_wrap_up(config: dict, metadata: dict, *, lead: str = "") -> dict:
    """Ask the closing question on its own, or thank the participant and finish."""
    closing = str(config.get("closing_question") or "").strip()
    if closing and not metadata.get("closing_asked"):
        metadata["closing_asked"] = True
        body = f"{lead}\n\n{closing}" if lead else closing
        return _send(metadata, ConversationState.CLOSING, body, kind="closing", prompt_text=closing)
    thank_you = _thank_you(config)
    return _finish(metadata, ConversationState.COMPLETED, f"{lead}\n\n{thank_you}" if lead else thank_you)


# ---------------------------------------------------------------------------
# Clarification / probing
# ---------------------------------------------------------------------------


async def generate_clarification(
    conversation: ChannelConversation,
    response: str,
    config: dict | None = None,
    project_id: str | None = None,
) -> str | None:
    """Use LLM to generate a probing/clarification question based on the response."""
    config = config or {}
    research_goals = config.get("research_goals", "Understand user experience and needs")
    deployment_type = config.get("deployment_type", "interview")

    try:
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

        # W5: the clarification probe goes through the AgenticDispatcher
        # (``channel.clarify``).
        from app.core.agentic import agentic
        from app.core.agentic.types import TurnParams

        outcome = await agentic.completion(
            purpose="channel.clarify",
            project_id=project_id or "",
            system=None,
            messages=[{"role": "user", "content": prompt}],
            params=TurnParams(),
        )
        content = outcome.text.strip()
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


async def _is_saturated(
    response: str,
    config: dict,
    project_id: str | None = None,
) -> bool:
    """Check if the probing has reached saturation.

    Uses LLM to judge whether further probing would yield new information.
    Falls back to a word-count heuristic if LLM is unavailable.
    """
    if config.get("saturation_check_llm", False):
        try:
            prompt = (
                "A research participant just gave this response to a follow-up probe:\n"
                f'"{response}"\n\n'
                "Has this response added meaningful new information, or is the "
                "participant repeating themselves / giving minimal answers?\n"
                'Respond with exactly "SATURATED" or "NOT_SATURATED".'
            )
            # W5: the saturation judgment goes through the AgenticDispatcher
            # (``channel.saturation``).
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            outcome = await agentic.completion(
                purpose="channel.saturation",
                project_id=project_id or "",
                system=None,
                messages=[{"role": "user", "content": prompt}],
                params=TurnParams(),
            )
            content = outcome.text.strip().upper()
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


def update_conversation_metadata(conversation: ChannelConversation, metadata: dict) -> None:
    """Update the conversation's metadata_json field in-place."""
    conversation.metadata_json = json.dumps(metadata)
