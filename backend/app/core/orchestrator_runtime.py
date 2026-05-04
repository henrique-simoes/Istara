"""Runtime hooks for waking the task orchestrator without static cycles."""

from importlib import import_module


def wake_orchestrator() -> None:
    """Wake the singleton task orchestrator when it is available."""
    orchestrator = getattr(import_module("app.core.agent"), "agent")
    orchestrator.wake()
