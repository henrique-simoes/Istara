"""Agent Orchestrator facade for Istara's autonomous work loop.

The orchestration implementation is split into lifecycle, execution, and
research modules. This facade preserves legacy imports of ``AgentOrchestrator``
and the singleton ``agent``.
"""

from __future__ import annotations

from app.core.agent_execution import AgentExecutionMixin
from app.core.agent_lifecycle import AgentLifecycleMixin
from app.core.agent_models import (
    _META_SKILL_SIMILARITY_THRESHOLD,
    ResearchPlan,
    ResearchStep,
    _resolve_project_folder,
)
from app.core.agent_research import AgentResearchMixin
from app.core.ollama import ollama


class AgentOrchestrator(AgentLifecycleMixin, AgentExecutionMixin, AgentResearchMixin):
    """Autonomous agent that picks tasks and runs skills."""

    pass


agent = AgentOrchestrator()

__all__ = [
    "AgentOrchestrator",
    "ResearchPlan",
    "ResearchStep",
    "_META_SKILL_SIMILARITY_THRESHOLD",
    "_resolve_project_folder",
    "agent",
    "ollama",
]
