"""Autoresearch loop for decision models: search the triage question's wording against human labels.

Target: a decider endpoint id. The runner reuses the code-application triage question set and the
project's own labelled triage trajectories (human reconciliation decisions), which
``app.services.decider_triage.labelled_triage_states`` prepares read-only. Each variant of the
question is asked once per labelled item and cached; each measurement scores a fresh random half
of those items by ``1 - binary Brier`` of P(supports) against the label, a strictly proper
scoring rule that the wording cannot inflate without improving the probabilities (governance
critique #11). Kept variants are governed
proposals like every autoresearch result; nothing changes the production question by itself.

It calls the decider (live, metered), so it runs only when a researcher starts the experiment.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.autoresearch_runners import BaseLoopRunner

logger = logging.getLogger(__name__)

MAX_ITEMS = 120
MIN_ITEMS = 20

VARIANTS: tuple[dict[str, Any], ...] = (
    {
        "name": "production",
        "instructions": "How does the evidence unit relate to applying the code `{code}` to it?",
        "options": {
            "supports": "The evidence unit expresses the code as its definition describes.",
            "contradicts": (
                "The evidence unit expresses the opposite of the code, or meets an exclusion "
                "criterion."
            ),
            "says_nothing": "The evidence unit does not address what the code describes.",
        },
    },
    {
        "name": "read_on_its_own",
        "instructions": (
            "Reading only the evidence unit, does it express the meaning of the code `{code}` as "
            "the code's definition and criteria describe?"
        ),
        "options": {
            "supports": "Yes: the unit itself states what the code describes.",
            "contradicts": "No: the unit states the opposite, or an exclusion criterion applies.",
            "says_nothing": "No: the unit is about something else or names a related topic only.",
        },
    },
    {
        "name": "exclusion_first",
        "instructions": (
            "Check the exclusion criteria of the code `{code}` first, then its definition. How "
            "does the evidence unit relate to the code?"
        ),
        "options": {
            "supports": "No exclusion criterion applies and the unit expresses the definition.",
            "contradicts": "An exclusion criterion applies, or the unit expresses the opposite.",
            "says_nothing": "The unit does not address the code's definition at all.",
        },
    },
)


class DecisionPolicyRunner(BaseLoopRunner):
    loop_type = "decision_policy"
    needs_persona_lock = False

    def __init__(self, *, items: list[dict[str, Any]] | None = None, client: Any = None) -> None:
        self._variant = 0
        self._tested: set[int] = set()
        self._items = items
        self._client = client
        self._cache: dict[tuple[int, str], float | None] = {}
        self._draws = random.Random(20261018)

    async def _load_items(self, target: str) -> list[dict[str, Any]]:
        """Labelled code-application triage items of this project and decider (read-only).

        The triage service prepares them, so this self-improvement module never reads research
        models itself (``tests/test_self_improvement_artifact_boundary.py``).
        """
        if self._items is not None:
            return self._items
        from app.services.decider_triage import labelled_triage_states

        self._items = await labelled_triage_states(
            self.require_project_id(), target, limit=MAX_ITEMS
        )
        return self._items

    async def _p_supports(self, variant: int, item: dict[str, Any]) -> float | None:
        key = (variant, item["id"])
        if key in self._cache:
            return self._cache[key]
        p = await self._ask(variant, item)
        self._cache[key] = p
        return p

    async def _ask(self, variant: int, item: dict[str, Any]) -> float | None:
        from app.core.decider.contract import Choice

        spec = VARIANTS[variant]
        instructions = spec["instructions"].format(code=item["code_name"])
        question = Choice(instructions, dict(spec["options"]))
        outcome = await self._client.decide(item["state"], {"relation": question})
        if not outcome.ok:
            return None
        return outcome.answers["relation"]["supports"]

    async def _score(self, variant: int, target: str) -> float | None:
        items = await self._load_items(target)
        if len(items) < MIN_ITEMS or self._client is None:
            return None
        half = self._draws.sample(items, len(items) // 2)
        errors = []
        for item in half:
            p = await self._p_supports(variant, item)
            if p is None:
                return None
            errors.append((p - item["label"]) ** 2)
        return 1.0 - sum(errors) / len(errors)

    async def _ensure_client(self, target: str) -> None:
        if self._client is None:
            from app.core.decider.access import open_decider

            self._client = await open_decider(target, self.require_project_id())

    async def measure_baseline(self, target: str) -> float | None:
        await self._ensure_client(target)
        self._tested = {0}
        return await self._score(0, target)

    async def measure_incumbent(self, target: str) -> float | None:
        return await self._score(0, target)

    async def measure(self, target: str) -> float | None:
        return await self._score(self._variant, target)

    async def hypothesize(
        self, target: str, current_score: float, history: list[dict]
    ) -> tuple[str, dict]:
        untested = [i for i in range(len(VARIANTS)) if i not in self._tested]
        if not untested:
            raise RuntimeError("every question variant has been tested")
        variant = untested[0]
        self._tested.add(variant)
        name = VARIANTS[variant]["name"]
        return (
            f"Question wording '{name}' gives better-calibrated triage than production",
            {"description": f"decision question variant {name}", "variant": name},
        )

    async def apply_mutation(self, target: str, mutation: dict) -> Callable[[], Awaitable[None]]:
        names = [v["name"] for v in VARIANTS]
        self._variant = names.index(mutation["variant"])

        async def _revert() -> None:
            self._variant = 0

        return _revert
