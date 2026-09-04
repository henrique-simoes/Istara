# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Loop 5: Agent Persona Optimization.

Optimizes agent persona files (SKILLS.md, PROTOCOLS.md) by proposing
targeted edits, measuring task quality before and after, and keeping
improvements.  Uses persona locking to prevent self-evolution from
making concurrent modifications.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Awaitable, Callable

from app.core.agent_identity import persona_file_path, writeable_persona_path
from app.core.autoresearch_runners import BaseLoopRunner

logger = logging.getLogger(__name__)

# Files eligible for optimization (CORE.md is identity-critical, not touched)
MUTABLE_FILES = ["SKILLS.md", "PROTOCOLS.md"]


class PersonaRunner(BaseLoopRunner):
    """Optimize agent persona files via LLM-guided edits."""

    loop_type = "persona"
    needs_persona_lock = True

    def __init__(self) -> None:
        self._file_index = 0

    # ------------------------------------------------------------------
    # BaseLoopRunner interface
    # ------------------------------------------------------------------

    async def measure_baseline(self, target: str) -> float:
        """Run a simulated task through the agent and measure quality.

        *target* is an agent_id.
        """
        return await self._evaluate_agent(target)

    async def measure(self, target: str) -> float:
        """Re-evaluate after persona mutation."""
        return await self._evaluate_agent(target)

    async def hypothesize(
        self, target: str, current_score: float, history: list[dict]
    ) -> tuple[str, dict]:
        """LLM analyzes current persona + history, suggests a file edit."""
        # Cycle through mutable files
        filename = MUTABLE_FILES[self._file_index % len(MUTABLE_FILES)]
        self._file_index += 1

        filepath = persona_file_path(target, filename)
        current_content = ""
        if filepath.exists():
            try:
                current_content = filepath.read_text(encoding="utf-8")
            except Exception:
                pass

        if not current_content:
            raise RuntimeError(f"Persona file not found or empty: {filepath}")

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
                    "You are an agent persona optimizer. Analyze the persona file "
                    "and suggest a targeted improvement to make the agent more "
                    "effective at UX research tasks.\n\n"
                    "RULES:\n"
                    "- Return the COMPLETE modified file content\n"
                    "- Make focused, meaningful changes (1-3 edits)\n"
                    "- Preserve the overall structure and headings\n"
                    "- Improve specificity, add domain expertise, or sharpen protocols\n"
                    "- Do NOT remove existing capabilities unless they conflict\n"
                    f"\nCurrent score: {current_score:.4f}\n"
                    f"{history_ctx}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Improve this {filename} for agent '{target}':\n\n"
                    f"---BEGIN FILE---\n{current_content}\n---END FILE---\n\n"
                    "Return ONLY the improved file content."
                ),
            },
        ]

        try:
            # W6/W9: the persona-file mutation goes through the
            # AgenticDispatcher (``autoresearch.persona.hypothesize``).
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            outcome = await agentic.completion(
                purpose="autoresearch.persona.hypothesize",
                project_id=self.require_project_id(),
                system=messages[0]["content"],
                messages=messages[1:],
                params=TurnParams(temperature=0.7, max_tokens=2000),
                spine_phase="plan",
                engine=self.engine,
            )
            new_content = (outcome.text or "").strip()
        except Exception as e:
            raise RuntimeError(f"LLM persona mutation failed: {e}") from e

        if not new_content or len(new_content) < 50:
            raise RuntimeError("LLM returned empty or trivially short persona content")

        # Strip markdown code fences if present
        if new_content.startswith("```"):
            lines = new_content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            new_content = "\n".join(lines).strip()

        hypothesis = f"Optimize {filename} for agent '{target}'"
        mutation = {
            "description": f"Edit {filename}",
            "filename": filename,
            "old_content": current_content,
            "new_content": new_content,
        }
        return hypothesis, mutation

    async def apply_mutation(self, target: str, mutation: dict) -> Callable[[], Awaitable[None]]:
        """Write modified persona file.  Returns revert function."""
        filename = mutation["filename"]
        old_content = mutation["old_content"]
        new_content = mutation["new_content"]
        filepath = writeable_persona_path(target, filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Write new content
        filepath.write_text(new_content, encoding="utf-8")
        logger.debug(f"PersonaRunner: wrote {filepath}")

        # Invalidate prompt_rag cache so new content is picked up
        self._invalidate_prompt_cache(target)

        async def _revert() -> None:
            filepath.write_text(old_content, encoding="utf-8")
            logger.debug(f"PersonaRunner: reverted {filepath}")
            self._invalidate_prompt_cache(target)

        return _revert

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _invalidate_prompt_cache(self, agent_id: str) -> None:
        """Invalidate prompt_rag caches after persona file changes."""
        try:
            from app.core.prompt_rag import index_agent_sections

            # index_agent_sections is not cached (no lru_cache), so the next
            # call will automatically read fresh files.  If caching is added
            # later, clear it here.
            logger.debug(f"Prompt RAG cache invalidation noted for {agent_id}")
        except Exception:
            pass

    async def _evaluate_agent(self, agent_id: str) -> float:
        """Evaluate agent quality by running a simulated UX research task."""
        from app.core.agent_identity import load_agent_identity

        identity = load_agent_identity(agent_id)
        if not identity:
            logger.warning(f"PersonaRunner: no identity for agent '{agent_id}'")
            return 0.0

        # Simulate a UX research task
        messages = [
            {"role": "system", "content": identity},
            {
                "role": "user",
                "content": (
                    "Analyze these interview findings and provide actionable insights:\n\n"
                    "- 4/5 participants struggled with the checkout button placement\n"
                    "- 3/5 mentioned the search bar was hard to find on mobile\n"
                    "- 2/5 praised the onboarding tutorial but wanted it shorter\n"
                    "- 5/5 found the product comparison feature useful\n"
                    "- 1/5 reported a confusing error message during payment\n\n"
                    "Provide a structured analysis with nuggets, insights, and recommendations."
                ),
            },
        ]

        try:
            # W6/W9: the simulated-task run goes through the AgenticDispatcher
            # (``autoresearch.persona.evaluate``).
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            outcome = await agentic.completion(
                purpose="autoresearch.persona.evaluate",
                project_id=self.require_project_id(),
                system=messages[0]["content"],
                messages=messages[1:],
                params=TurnParams(temperature=0.5, max_tokens=1500),
                spine_phase="execution",
                engine=self.engine,
            )
            content = outcome.text
        except Exception as e:
            logger.warning(f"Agent evaluation failed: {e}")
            return 0.0

        return await self._score_response(content)

    async def _score_response(self, output: str) -> float:
        """Score the agent response quality."""
        if not output or len(output.strip()) < 30:
            return 0.1

        messages = [
            {
                "role": "system",
                "content": (
                    "Score this UX research analysis on 0.0-1.0 considering:\n"
                    "- Evidence grounding: claims linked to specific data points\n"
                    "- Structure: clear sections (nuggets, insights, recommendations)\n"
                    "- Actionability: specific, implementable recommendations\n"
                    "- Analytical depth: goes beyond surface observations\n"
                    "- Professional tone: appropriate for research reports\n"
                    "Respond with ONLY a decimal number."
                ),
            },
            {"role": "user", "content": f"Analysis output:\n{output[:2000]}"},
        ]

        try:
            # W6/W9: the response-quality score goes through the
            # AgenticDispatcher (``autoresearch.persona.score``).
            from app.core.agentic import agentic
            from app.core.agentic.types import TurnParams

            outcome = await agentic.completion(
                purpose="autoresearch.persona.score",
                project_id=self.require_project_id(),
                system=messages[0]["content"],
                messages=messages[1:],
                params=TurnParams(temperature=0.1, max_tokens=10),
                spine_phase="review",
                engine=self.engine,
            )
            score_text = (outcome.text or "").strip()
            for token in score_text.replace(",", ".").split():
                try:
                    val = float(token)
                    return max(0.0, min(1.0, val))
                except ValueError:
                    continue
            return 0.5
        except Exception:
            return 0.5
