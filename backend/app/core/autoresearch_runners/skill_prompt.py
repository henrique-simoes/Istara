# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Loop 1: Skill Prompt Optimization — the most valuable loop.

Uses 6 mutation operators to iteratively improve skill execute_prompts:
  1. Add constraints        — tighten output rules
  2. Negative examples      — show what NOT to do
  3. Restructure            — reorganize prompt sections
  4. Tighten language       — remove ambiguity, sharpen wording
  5. Remove bloat           — cut redundant/low-value instructions
  6. Counterexamples        — add edge-case handling

Each iteration mutates the prompt, runs the skill 3 times, and keeps or
discards the change based on average quality improvement.
"""

from __future__ import annotations

import json
import logging
from typing import Awaitable, Callable

from app.core.autoresearch_runners import BaseLoopRunner

logger = logging.getLogger(__name__)

MUTATION_OPERATORS = [
    "add_constraints",
    "negative_examples",
    "restructure",
    "tighten_language",
    "remove_bloat",
    "counterexamples",
]

EVAL_RUNS = 3  # Number of evaluation runs per measurement


class SkillPromptRunner(BaseLoopRunner):
    """Optimize skill execute_prompts via LLM-guided mutation."""

    loop_type = "skill_prompt"
    needs_persona_lock = False

    def __init__(self) -> None:
        self._operator_index = 0

    # ------------------------------------------------------------------
    # BaseLoopRunner interface
    # ------------------------------------------------------------------

    async def measure_baseline(self, target: str) -> float:
        """Run skill 3 times on test data, average quality."""
        return await self._multi_eval(target)

    async def measure(self, target: str) -> float:
        """Run skill 3 times after mutation, average quality."""
        return await self._multi_eval(target)

    async def hypothesize(
        self, target: str, current_score: float, history: list[dict]
    ) -> tuple[str, dict]:
        """Use LLM with one of 6 mutation operators to propose a prompt edit."""
        from app.core.llm_router import llm_router
        from app.skills.skill_manager import skill_manager

        defn = skill_manager.get(target)
        if not defn:
            raise ValueError(f"Skill not found: {target}")

        current_prompt = defn.data.get("execute_prompt", "")
        if not current_prompt:
            raise ValueError(f"Skill '{target}' has no execute_prompt")

        # Cycle through mutation operators
        operator = MUTATION_OPERATORS[self._operator_index % len(MUTATION_OPERATORS)]
        self._operator_index += 1

        # Build history context
        history_ctx = ""
        if history:
            kept = [h for h in history[-8:] if h.get("kept")]
            discarded = [h for h in history[-8:] if not h.get("kept")]
            if kept:
                history_ctx += "Improvements that WORKED:\n"
                history_ctx += "\n".join(
                    f"  - {h.get('hypothesis', '?')[:80]}" for h in kept[-4:]
                )
                history_ctx += "\n"
            if discarded:
                history_ctx += "Changes that did NOT help:\n"
                history_ctx += "\n".join(
                    f"  - {h.get('hypothesis', '?')[:80]}" for h in discarded[-4:]
                )
                history_ctx += "\n"

        operator_instructions = {
            "add_constraints": (
                "Add 1-2 specific constraints to the prompt that would improve "
                "output quality. For example: required output format, minimum "
                "evidence counts, citation requirements, or quality gates."
            ),
            "negative_examples": (
                "Add a 'Do NOT' section with 2-3 negative examples showing "
                "common mistakes this skill should avoid. Be specific."
            ),
            "restructure": (
                "Reorganize the prompt structure for clarity. Move the most "
                "important instructions to the top. Group related instructions. "
                "Add clear section headers if missing."
            ),
            "tighten_language": (
                "Tighten the language: replace vague words with precise ones, "
                "remove hedge words ('try to', 'maybe', 'might'), and sharpen "
                "action verbs. Keep the same meaning but make instructions clearer."
            ),
            "remove_bloat": (
                "Remove redundant or low-value instructions that add tokens "
                "without improving output quality. Consolidate duplicated ideas. "
                "Keep the prompt shorter but equally effective."
            ),
            "counterexamples": (
                "Add 1-2 edge-case handling instructions. Think about what "
                "happens with unusual inputs: empty data, conflicting evidence, "
                "ambiguous questions. Add specific guidance for these cases."
            ),
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a prompt optimization expert. Your task is to improve "
                    "a UX research skill prompt using a specific mutation strategy.\n\n"
                    f"MUTATION STRATEGY: {operator}\n"
                    f"INSTRUCTIONS: {operator_instructions[operator]}\n\n"
                    "RULES:\n"
                    "- Return the COMPLETE modified prompt (not just the diff)\n"
                    "- Make targeted, meaningful changes (not superficial)\n"
                    "- Preserve the core intent and output schema references\n"
                    "- Do NOT add generic filler — every instruction should earn its tokens\n"
                    f"\nCurrent score: {current_score:.4f}\n"
                    f"{history_ctx}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Improve this prompt using the '{operator}' strategy:\n\n"
                    f"---BEGIN PROMPT---\n{current_prompt}\n---END PROMPT---\n\n"
                    "Return ONLY the improved prompt text, nothing else."
                ),
            },
        ]

        try:
            response = await llm_router.chat(
                messages, temperature=0.7, max_tokens=2000
            )
            new_prompt = response.get("message", {}).get("content", "").strip()
        except Exception as e:
            raise RuntimeError(f"LLM mutation failed: {e}") from e

        # Validate the new prompt is substantive
        if not new_prompt or len(new_prompt) < 50:
            raise RuntimeError("LLM returned an empty or trivially short prompt")

        # Strip any markdown code fences if the LLM wrapped the output
        if new_prompt.startswith("```"):
            lines = new_prompt.split("\n")
            # Remove first and last fence lines
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            new_prompt = "\n".join(lines).strip()

        hypothesis = f"[{operator}] Mutate execute_prompt for skill '{target}'"
        mutation = {
            "description": f"Operator: {operator}",
            "operator": operator,
            "new_prompt": new_prompt,
            "old_prompt": current_prompt,
        }
        return hypothesis, mutation

    async def apply_mutation(
        self, target: str, mutation: dict
    ) -> Callable[[], Awaitable[None]]:
        """Update the skill's execute_prompt.  Returns a revert function."""
        from app.skills.skill_manager import skill_manager

        old_prompt = mutation["old_prompt"]
        new_prompt = mutation["new_prompt"]

        skill_manager.update_skill(
            target,
            {"execute_prompt": new_prompt},
            changelog_entry=f"Autoresearch: {mutation.get('operator', 'optimize')} mutation",
        )

        async def _revert() -> None:
            skill_manager.update_skill(
                target,
                {"execute_prompt": old_prompt},
                changelog_entry="Autoresearch: reverted prompt mutation",
            )

        return _revert

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    async def _multi_eval(self, skill_name: str) -> float:
        """Run the skill multiple times and return average quality."""
        scores: list[float] = []
        for _ in range(EVAL_RUNS):
            try:
                score = await self._single_eval(skill_name)
                scores.append(score)
            except Exception as e:
                logger.debug(f"Eval run failed: {e}")
                scores.append(0.0)
        return sum(scores) / len(scores) if scores else 0.0

    async def _single_eval(self, skill_name: str) -> float:
        """Execute skill once and score the output quality."""
        from app.core.llm_router import llm_router
        from app.skills.skill_manager import skill_manager

        defn = skill_manager.get(skill_name)
        if not defn:
            return 0.0

        prompt = defn.data.get("execute_prompt", "")
        if not prompt:
            return 0.0

        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    "Execute this UX research skill with the following sample context: "
                    "A mobile e-commerce app interview with 5 participants revealed "
                    "navigation issues in the checkout flow. Generate realistic output."
                ),
            },
        ]

        try:
            response = await llm_router.chat(messages, temperature=0.5, max_tokens=1500)
            content = response.get("message", {}).get("content", "")
        except Exception:
            return 0.0

        return await self._score_output(content, skill_name)

    async def _score_output(self, output: str, skill_name: str) -> float:
        """LLM-based quality scoring on [0, 1] scale."""
        from app.core.llm_router import llm_router

        if not output or len(output.strip()) < 30:
            return 0.1

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict quality evaluator for UX research skill outputs. "
                    "Score the output on a 0.0-1.0 scale considering:\n"
                    "- Completeness: Does it cover all expected output sections?\n"
                    "- Evidence quality: Are findings grounded in specific observations?\n"
                    "- Actionability: Are recommendations concrete and implementable?\n"
                    "- Structure: Is the output well-organized with clear sections?\n"
                    "- Source attribution: Are claims traced to specific data points?\n"
                    "Respond with ONLY a decimal number between 0.0 and 1.0."
                ),
            },
            {
                "role": "user",
                "content": f"Skill: {skill_name}\n\nOutput:\n{output[:2000]}",
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
