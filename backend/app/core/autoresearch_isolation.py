# Inspired by Karpathy's autoresearch (MIT) — https://github.com/karpathy/autoresearch
"""Autoresearch Isolation Layer — prevents experiments from polluting self-improvement systems.

Uses Python contextvars to create a coroutine-local flag. When active, all learning,
skill recording, and observation methods in existing subsystems become no-ops.

Integration with ResearchDeployment:
Experiments running under this isolation layer should be tracked as temporary
deployments of type "experiment" rather than polluting the regular research pipeline.
This ensures experimental data is collected but not automatically merged into codebooks.

Usage:
    async with autoresearch_context():
        # All code here is isolated from self-improvement systems
        await run_experiment(...)
"""

from __future__ import annotations

import contextvars
from contextlib import asynccontextmanager

# Coroutine-local flag: True when inside an autoresearch experiment
_autoresearch_active: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "autoresearch_active", default=False
)


def is_autoresearch_active() -> bool:
    """Check if the current coroutine is inside an autoresearch experiment."""
    return _autoresearch_active.get()


@asynccontextmanager
async def autoresearch_context():
    """Context manager that marks the current coroutine as an autoresearch experiment.

    While active:
    - agent_learning.record_*() methods return early (no records created)
    - skill_manager.record_execution() returns early (no stats polluted)
    - self_evolution.scan_for_promotions() filters out [autoresearch] learnings
    - meta_hyperagent.observe_cycle() filters out autoresearch-tagged stats
    
    The experiment's findings are still captured but not automatically merged
    into permanent knowledge graphs until promoted via the ResearchDeployment workflow.
    """
    token = _autoresearch_active.set(True)
    try:
        yield
    finally:
        _autoresearch_active.reset(token)
