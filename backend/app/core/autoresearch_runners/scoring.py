"""Measurement for autoresearch runners: strict scores, independent judges, no fabricated numbers.

Every failure returns None, which the engine records as ``not_runnable`` and leaves out of the
statistics. A failed or unparsable judge call is not a score of 0.5, and "8/10" is not 1.0
(audit findings AR-4, AR-5). The LLM judge is pinned to an endpoint other than the one under test
when one exists (AR-6). When the project's assurance mode excludes LLM judges, a typed decision
model scores the output instead, through the same calibrated, closed-answer contract.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_UNIT_SCORE = re.compile(r"^\s*(?:0(?:\.\d+)?|1(?:\.0+)?|\.\d+)\s*$")
_LEVELS = (
    "Unusable: misses the task or contradicts its evidence",
    "Weak: partly answers the task with notable gaps or unsupported claims",
    "Adequate: answers the task with minor gaps",
    "Good: complete, grounded and actionable",
    "Excellent: complete, grounded, actionable and clearly structured",
)


def parse_unit_score(text: str | None) -> float | None:
    """A reply that is only a number in [0, 1], else None. No partial matches, no clamping."""
    if text is None or not _UNIT_SCORE.match(text):
        return None
    value = float(text.strip())
    return value if 0.0 <= value <= 1.0 else None


async def _judge_endpoint(project_id: str, avoid: set[str]) -> tuple[bool, str | None]:
    """``(ok, endpoint_id)``: an admitted endpoint not under test, or the default route if none
    is under test; ``(False, None)`` when every endpoint is under test."""
    if not avoid:
        return True, None
    try:
        from app.core.agentic import agentic

        catalog = agentic.model_manager().catalog(project_id=project_id)
    except Exception as exc:
        logger.debug("Judge catalog lookup failed: %s", exc)
        return False, None
    for info in catalog:
        endpoint_id = (getattr(info, "endpoint_id", "") or "").strip()
        if endpoint_id and endpoint_id not in avoid:
            return True, endpoint_id
    return False, None


async def _decider_score(project_id: str, skill_name: str, output: str) -> float | None:
    from app.core.decider.access import open_decider
    from app.core.decider.contract import Score
    from app.core.decider.registry import DeciderUnavailableError
    from app.services.assurance_policies import load_project_assurance

    policy = await load_project_assurance(project_id)
    for endpoint_id in policy.decider_endpoint_ids:
        try:
            client = await open_decider(endpoint_id, project_id)
        except DeciderUnavailableError:
            continue
        outcome = await client.decide(
            {"skill": skill_name, "output": output[:6000]},
            {"quality": Score("How good is this UX research skill output?", list(_LEVELS))},
        )
        if outcome.ok:
            dist = outcome.answers["quality"]
            expected = sum(int(level) * p for level, p in dist.items())
            return expected / (len(_LEVELS) - 1)
    return None


@dataclass(frozen=True)
class JudgePlan:
    """How to score one output. ``use_llm`` False means ``score`` is final (None: unmeasurable)."""

    use_llm: bool
    endpoint_id: str | None = None
    score: float | None = None

    def params(self) -> Any:
        from app.core.agentic.types import TurnParams

        return TurnParams(endpoint_id=self.endpoint_id, temperature=0.1, max_tokens=10)


def judge_messages(subject: str, output: str) -> list[dict[str, str]]:
    return [{"role": "user", "content": f"Skill: {subject}\n\nOutput:\n{output[:2000]}"}]


async def plan_judge(
    runner: Any,
    *,
    skill_name: str,
    output: str,
    avoid_endpoint_ids: Iterable[str] = (),
) -> JudgePlan:
    """Choose the measurement for ``output``.

    A decision model scores it when the project's assurance mode excludes LLM judges. Otherwise
    the caller runs its own LLM judge through the dispatcher (``agentic.completion``), on the
    endpoint named here, which is never one under test.
    """
    project_id = runner.require_project_id()
    try:
        from app.core.assurance import plan_validation
        from app.services.assurance_policies import load_project_assurance

        plan = plan_validation(await load_project_assurance(project_id))
    except Exception:
        plan = None
    if plan is not None and not plan.run_llm:
        try:
            return JudgePlan(False, score=await _decider_score(project_id, skill_name, output))
        except Exception as exc:
            logger.debug("Decider scoring failed: %s", exc)
            return JudgePlan(False)
    ok, endpoint_id = await _judge_endpoint(project_id, {e for e in avoid_endpoint_ids if e})
    return JudgePlan(True, endpoint_id=endpoint_id) if ok else JudgePlan(False)
