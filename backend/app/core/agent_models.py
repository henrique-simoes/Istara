"""Data models and shared helpers for the Istara agent orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings

_META_SKILL_SIMILARITY_THRESHOLD = 0.6


def _resolve_project_folder(project, project_id: str) -> Path:
    if project and getattr(project, "watch_folder_path", None):
        return Path(project.watch_folder_path)
    return Path(settings.upload_dir) / project_id


@dataclass
class ResearchStep:
    """A single step in a research plan."""

    id: str
    description: str
    skill_name: str | None = None
    status: str = "pending"  # pending | executing | completed | failed
    result: str = ""
    depends_on: list[str] = field(default_factory=list)


@dataclass
class ResearchPlan:
    """A decomposed research plan with ordered steps."""

    question: str
    steps: list[ResearchStep] = field(default_factory=list)
    past_steps: list[ResearchStep] = field(default_factory=list)
    status: str = "planning"  # planning | executing | replanning | complete

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "status": self.status,
            "steps": [
                {
                    "id": s.id,
                    "desc": s.description,
                    "skill": s.skill_name,
                    "status": s.status,
                    "result": s.result[:200],
                    "depends_on": s.depends_on,
                }
                for s in self.steps
            ],
            "completed": [
                {"id": s.id, "desc": s.description, "status": s.status} for s in self.past_steps
            ],
        }
