"""The decision_policy autoresearch runner (CF-SPEC-1, Phase 6).

The decider is stubbed per (variant, item): the test controls how well calibrated each wording is
and checks that the runner's objective (1 - binary Brier on a random half of labelled items) prefers
the better-calibrated wording, caches decider calls, and refuses to score too few labels.
"""

import asyncio
import random

from app.core.autoresearch_runners.decision_policy import MIN_ITEMS, VARIANTS, DecisionPolicyRunner


def _items(n: int, seed: int = 1):
    rng = random.Random(seed)
    return [{"id": f"i{k}", "application": None, "label": rng.randint(0, 1)} for k in range(n)]


def _runner(items, quality):
    """``quality[v]``: how far variant v's probability sits from the label (0 = perfect)."""
    runner = DecisionPolicyRunner(items=items, client=object())
    runner.bind_project("p1")
    calls = []

    async def fake_ask(variant, item):
        calls.append((variant, item["id"]))
        miss = quality[variant]
        return 1.0 - miss if item["label"] else miss

    runner._ask = fake_ask
    return runner, calls


def test_better_calibrated_wording_scores_higher_and_calls_are_cached():
    items = _items(60)
    runner, calls = _runner(items, {0: 0.4, 1: 0.1, 2: 0.45})

    async def scenario():
        baseline = await runner.measure_baseline("kev")
        hypothesis, mutation = await runner.hypothesize("kev", baseline, [])
        revert = await runner.apply_mutation("kev", mutation)
        candidate = await runner.measure("kev")
        await revert()
        incumbent = await runner.measure_incumbent("kev")
        return baseline, mutation, candidate, incumbent

    baseline, mutation, candidate, incumbent = asyncio.run(scenario())
    assert mutation["variant"] == VARIANTS[1]["name"]
    assert abs(baseline - (1 - 0.4**2)) < 1e-9 and abs(incumbent - baseline) < 1e-9
    assert abs(candidate - (1 - 0.1**2)) < 1e-9
    assert len(calls) == len(set(calls))  # each (variant, item) asked once


def test_too_few_labels_cannot_be_scored():
    runner, _ = _runner(_items(MIN_ITEMS - 1), {0: 0.2, 1: 0.2, 2: 0.2})
    assert asyncio.run(runner.measure_baseline("kev")) is None


def test_variants_are_exhausted_explicitly():
    runner, _ = _runner(_items(40), {0: 0.2, 1: 0.2, 2: 0.2})

    async def scenario():
        await runner.measure_baseline("kev")
        names = [(await runner.hypothesize("kev", 0.0, []))[1]["variant"] for _ in range(2)]
        try:
            await runner.hypothesize("kev", 0.0, [])
        except RuntimeError:
            return names, True
        return names, False

    names, exhausted = asyncio.run(scenario())
    assert names == [VARIANTS[1]["name"], VARIANTS[2]["name"]] and exhausted
