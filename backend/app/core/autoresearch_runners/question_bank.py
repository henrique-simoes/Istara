# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Loop 3: Question Bank Optimization.

Improves research deployment question banks by rewording questions,
adjusting question order, and tuning adaptive configuration to
maximize simulated participant response quality.
"""

from __future__ import annotations

import json
import logging
from typing import Awaitable, Callable

from app.core.autoresearch_runners import BaseLoopRunner

logger = logging.getLogger(__name__)


class QuestionBankRunner(BaseLoopRunner):
    """Optimize research deployment question banks."""

    loop_type = "question_bank"
    needs_persona_lock = False

    # ------------------------------------------------------------------
    # BaseLoopRunner interface
    # ------------------------------------------------------------------

    async def measure_baseline(self, target: str) -> float:
        """Simulate a participant and measure response quality.

        *target* is a deployment_id.
        """
        return await self._evaluate_questions(target)

    async def measure(self, target: str) -> float:
        """Evaluate after question mutation."""
        return await self._evaluate_questions(target)

    async def hypothesize(
        self, target: str, current_score: float, history: list[dict]
    ) -> tuple[str, dict]:
        """LLM suggests question rewording, reordering, or adaptive config changes."""
        from app.core.llm_router import llm_router

        deployment = await self._load_deployment(target)
        questions = json.loads(deployment.questions_json or "[]")
        config = json.loads(deployment.config_json or "{}")

        if not questions:
            raise RuntimeError(f"Deployment '{target}' has no questions")

        # Build history context
        history_ctx = ""
        if history:
            recent = history[-6:]
            history_ctx = "Recent experiments:\n" + "\n".join(
                f"  - {h.get('hypothesis', '?')[:80]} "
                f"(delta={h.get('delta', 0):.4f}, kept={h.get('kept', False)})"
                for h in recent
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a UX research methodology expert optimizing a question bank. "
                    "Suggest ONE improvement from these strategies:\n"
                    "1. REWORD: Improve question clarity or reduce leading bias\n"
                    "2. REORDER: Change question sequence for better flow\n"
                    "3. ADAPTIVE: Modify branching rules or follow-up triggers\n\n"
                    "Respond in this exact JSON format:\n"
                    '{"strategy": "reword|reorder|adaptive", '
                    '"changes": <modified_questions_array>, '
                    '"config_changes": <optional_config_dict>, '
                    '"reason": "<brief reason>"}\n\n'
                    f"Current score: {current_score:.4f}\n"
                    f"{history_ctx}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Current questions:\n{json.dumps(questions, indent=2)}\n\n"
                    f"Current config:\n{json.dumps(config, indent=2)}\n\n"
                    "Suggest one targeted improvement."
                ),
            },
        ]

        try:
            response = await llm_router.chat(
                messages, temperature=0.7, max_tokens=1500
            )
            content = response.get("message", {}).get("content", "").strip()
        except Exception as e:
            raise RuntimeError(f"LLM question hypothesis failed: {e}") from e

        # Parse JSON from response
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                suggestion = json.loads(content[start:end])
            else:
                raise ValueError("No JSON found in response")
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Failed to parse LLM suggestion: {e}") from e

        strategy = suggestion.get("strategy", "reword")
        new_questions = suggestion.get("changes", questions)
        config_changes = suggestion.get("config_changes", {})
        reason = suggestion.get("reason", "LLM-suggested improvement")

        hypothesis = f"[{strategy}] {reason}"
        mutation = {
            "description": f"Strategy: {strategy} - {reason[:80]}",
            "old_questions": questions,
            "new_questions": new_questions,
            "old_config": config,
            "config_changes": config_changes,
        }
        return hypothesis, mutation

    async def apply_mutation(
        self, target: str, mutation: dict
    ) -> Callable[[], Awaitable[None]]:
        """Modify deployment questions in the database.  Returns revert fn."""
        old_questions_json = json.dumps(mutation["old_questions"])
        new_questions_json = json.dumps(mutation["new_questions"])
        old_config = mutation["old_config"]
        config_changes = mutation.get("config_changes", {})

        # Merge config changes
        new_config = {**old_config, **config_changes} if config_changes else old_config
        old_config_json = json.dumps(old_config)
        new_config_json = json.dumps(new_config)

        await self._update_deployment(target, new_questions_json, new_config_json)

        async def _revert() -> None:
            await self._update_deployment(target, old_questions_json, old_config_json)

        return _revert

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_deployment(self, deployment_id: str):
        """Load a ResearchDeployment by ID."""
        from sqlalchemy import select

        from app.models.database import async_session
        from app.models.research_deployment import ResearchDeployment

        async with async_session() as db:
            result = await db.execute(
                select(ResearchDeployment).where(ResearchDeployment.id == deployment_id)
            )
            deployment = result.scalar_one_or_none()
            if not deployment:
                raise ValueError(f"Deployment not found: {deployment_id}")
            return deployment

    async def _update_deployment(
        self, deployment_id: str, questions_json: str, config_json: str
    ) -> None:
        """Update deployment questions and config in the database."""
        from sqlalchemy import select

        from app.models.database import async_session
        from app.models.research_deployment import ResearchDeployment

        async with async_session() as db:
            result = await db.execute(
                select(ResearchDeployment).where(ResearchDeployment.id == deployment_id)
            )
            deployment = result.scalar_one_or_none()
            if deployment:
                deployment.questions_json = questions_json
                deployment.config_json = config_json
                await db.commit()

    async def _evaluate_questions(self, deployment_id: str) -> float:
        """Simulate a participant going through the question bank and score quality."""
        from app.core.llm_router import llm_router

        deployment = await self._load_deployment(deployment_id)
        questions = json.loads(deployment.questions_json or "[]")

        if not questions:
            return 0.0

        # Format questions for the simulated participant
        questions_text = "\n".join(
            f"{i+1}. {q.get('text', q) if isinstance(q, dict) else q}"
            for i, q in enumerate(questions)
        )

        # Simulate a participant responding
        sim_messages = [
            {
                "role": "system",
                "content": (
                    "You are simulating a real user participating in a UX research study. "
                    "Answer each question naturally and honestly as if you were a real "
                    "participant who uses a mobile e-commerce app daily. Provide detailed, "
                    "thoughtful responses that reflect genuine user experience."
                ),
            },
            {
                "role": "user",
                "content": f"Please answer these research questions:\n\n{questions_text}",
            },
        ]

        try:
            response = await llm_router.chat(
                sim_messages, temperature=0.8, max_tokens=1500
            )
            participant_response = response.get("message", {}).get("content", "")
        except Exception as e:
            logger.warning(f"Participant simulation failed: {e}")
            return 0.0

        # Score the response quality
        return await self._score_responses(questions_text, participant_response)

    async def _score_responses(
        self, questions_text: str, responses: str
    ) -> float:
        """Score how well the questions elicited useful research responses."""
        from app.core.llm_router import llm_router

        if not responses or len(responses.strip()) < 30:
            return 0.1

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a UX research quality evaluator. Score how well these "
                    "research questions elicited useful, actionable responses from "
                    "a simulated participant on 0.0-1.0 scale:\n"
                    "- Response depth: detailed vs superficial answers\n"
                    "- Coverage: all questions adequately addressed\n"
                    "- Actionability: responses contain specific, usable insights\n"
                    "- Engagement: natural flow, no confusion or misunderstanding\n"
                    "- Bias avoidance: questions did not lead to biased responses\n"
                    "Respond with ONLY a decimal number."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Questions:\n{questions_text[:1000]}\n\n"
                    f"Participant responses:\n{responses[:1500]}"
                ),
            },
        ]

        try:
            response = await llm_router.chat(messages, temperature=0.1, max_tokens=10)
            score_text = response.get("message", {}).get("content", "").strip()
            for token in score_text.replace(",", ".").split():
                try:
                    val = float(token)
                    return max(0.0, min(1.0, val))
                except ValueError:
                    continue
            return 0.5
        except Exception:
            return 0.5
