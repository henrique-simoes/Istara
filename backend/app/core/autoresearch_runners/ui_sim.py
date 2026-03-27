# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Loop 2: UI Simulation Optimization — the most complex loop.

Evaluates UI components for accessibility and UX quality using LLM-based
analysis, proposes improvements, and measures the impact.  Uses git stash
for safe file modifications with guaranteed rollback.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Awaitable, Callable

from app.core.autoresearch_runners import BaseLoopRunner

logger = logging.getLogger(__name__)


class UISimRunner(BaseLoopRunner):
    """Optimize UI components for accessibility and UX quality."""

    loop_type = "ui_sim"
    needs_persona_lock = False

    # ------------------------------------------------------------------
    # BaseLoopRunner interface
    # ------------------------------------------------------------------

    async def measure_baseline(self, target: str) -> float:
        """Run accessibility evaluation on the component.

        *target* is a component file path (relative or absolute).
        """
        return await self._evaluate_component(target)

    async def measure(self, target: str) -> float:
        """Re-evaluate after component modification."""
        return await self._evaluate_component(target)

    async def hypothesize(
        self, target: str, current_score: float, history: list[dict]
    ) -> tuple[str, dict]:
        """LLM analyzes component code and proposes an accessibility/UX improvement."""
        from app.core.llm_router import llm_router

        filepath = Path(target)
        if not filepath.exists():
            raise RuntimeError(f"Component file not found: {target}")

        try:
            current_code = filepath.read_text(encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"Cannot read component: {e}") from e

        if not current_code.strip():
            raise RuntimeError(f"Component file is empty: {target}")

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
                    "You are a UI accessibility and UX optimization expert. "
                    "Analyze the component code and propose ONE targeted improvement.\n\n"
                    "Focus areas (in priority order):\n"
                    "1. ARIA labels and roles for screen readers\n"
                    "2. Keyboard navigation and focus management\n"
                    "3. Color contrast and visual accessibility\n"
                    "4. Touch target sizes for mobile\n"
                    "5. Error state handling and user feedback\n"
                    "6. Semantic HTML structure\n\n"
                    "RULES:\n"
                    "- Return the COMPLETE modified file content\n"
                    "- Make ONE focused change (not multiple unrelated changes)\n"
                    "- Preserve all existing functionality\n"
                    "- Add comments explaining accessibility improvements\n"
                    f"\nCurrent score: {current_score:.4f}\n"
                    f"{history_ctx}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Improve this component ({filepath.name}):\n\n"
                    f"---BEGIN CODE---\n{current_code[:3000]}\n---END CODE---\n\n"
                    "Return ONLY the improved file content."
                ),
            },
        ]

        try:
            response = await llm_router.chat(
                messages, temperature=0.5, max_tokens=3000
            )
            new_code = response.get("message", {}).get("content", "").strip()
        except Exception as e:
            raise RuntimeError(f"LLM UI mutation failed: {e}") from e

        if not new_code or len(new_code) < 20:
            raise RuntimeError("LLM returned empty or trivially short code")

        # Strip markdown code fences if present
        if new_code.startswith("```"):
            lines = new_code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            new_code = "\n".join(lines).strip()

        hypothesis = f"Improve accessibility/UX of {filepath.name}"
        mutation = {
            "description": f"A11y/UX improvement for {filepath.name}",
            "filepath": str(filepath),
            "old_code": current_code,
            "new_code": new_code,
        }
        return hypothesis, mutation

    async def apply_mutation(
        self, target: str, mutation: dict
    ) -> Callable[[], Awaitable[None]]:
        """Write modified component file.  Returns revert function.

        Uses direct file write + backup instead of git stash for simpler
        isolation within the autoresearch context.
        """
        filepath = Path(mutation["filepath"])
        old_code = mutation["old_code"]
        new_code = mutation["new_code"]

        # Write the modified file
        filepath.write_text(new_code, encoding="utf-8")
        logger.debug(f"UISimRunner: wrote modified {filepath}")

        async def _revert() -> None:
            filepath.write_text(old_code, encoding="utf-8")
            logger.debug(f"UISimRunner: reverted {filepath}")

        return _revert

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    async def _evaluate_component(self, target: str) -> float:
        """Evaluate component accessibility and UX quality via LLM analysis."""
        from app.core.llm_router import llm_router

        filepath = Path(target)
        if not filepath.exists():
            logger.warning(f"UISimRunner: component not found: {target}")
            return 0.0

        try:
            code = filepath.read_text(encoding="utf-8")
        except Exception:
            return 0.0

        if not code.strip():
            return 0.0

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a WCAG 2.1 accessibility auditor. Evaluate this UI "
                    "component and score it on 0.0-1.0 based on:\n\n"
                    "1. ARIA attributes (0.2): Proper labels, roles, live regions\n"
                    "2. Keyboard access (0.2): Tab order, focus indicators, shortcuts\n"
                    "3. Semantic HTML (0.15): Correct element usage, heading hierarchy\n"
                    "4. Visual a11y (0.15): Contrast hints, responsive text, icons\n"
                    "5. Error handling (0.15): Accessible error messages, form validation\n"
                    "6. Touch targets (0.15): Adequate size, spacing for mobile\n\n"
                    "Respond with ONLY a decimal number between 0.0 and 1.0."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Component: {filepath.name}\n\n"
                    f"Code:\n{code[:3000]}"
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
        except Exception as e:
            logger.warning(f"Component evaluation failed: {e}")
            return 0.5
