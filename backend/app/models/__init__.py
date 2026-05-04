"""Database model package.

The package exposes a small compatibility layer without eagerly importing every
model module. Eager imports from this package create broad dependency cycles
because individual models depend on ``app.models.database``.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "Base": ("app.models.database", "Base"),
    "get_db": ("app.models.database", "get_db"),
    "async_session": ("app.models.database", "async_session"),
    "init_db": ("app.models.database", "init_db"),
    "Project": ("app.models.project", "Project"),
    "ProjectPhase": ("app.models.project", "ProjectPhase"),
    "Task": ("app.models.task", "Task"),
    "TaskStatus": ("app.models.task", "TaskStatus"),
    "TaskReviewEvent": ("app.models.task_review", "TaskReviewEvent"),
    "Message": ("app.models.message", "Message"),
    "Nugget": ("app.models.finding", "Nugget"),
    "Fact": ("app.models.finding", "Fact"),
    "Insight": ("app.models.finding", "Insight"),
    "Recommendation": ("app.models.finding", "Recommendation"),
    "Codebook": ("app.models.codebook", "Codebook"),
    "Code": ("app.models.codebook", "Code"),
    "Document": ("app.models.document", "Document"),
    "DocumentStatus": ("app.models.document", "DocumentStatus"),
    "DocumentSource": ("app.models.document", "DocumentSource"),
    "ReasoningMemoryItem": ("app.models.reasoning_memory", "ReasoningMemoryItem"),
    "ImprovementProposal": ("app.models.improvement_governance", "ImprovementProposal"),
    "DGMHArchiveVariant": ("app.models.dgmh_archive", "DGMHArchiveVariant"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value
