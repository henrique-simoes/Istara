"""Skill definition contracts and path helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

SOURCE_SKILLS_DIR = Path(__file__).parent / "definitions"
SKILLS_DIR = SOURCE_SKILLS_DIR


def runtime_skills_dir() -> Path:
    return Path(settings.runtime_skills_dir)


def skill_definition_dirs() -> list[Path]:
    return [SOURCE_SKILLS_DIR, runtime_skills_dir()]


def writeable_skill_path(name: str, *, source: bool = False) -> Path:
    if source:
        if not settings.allow_source_skill_mutation:
            raise PermissionError(
                "Source skill mutation is disabled. Set ALLOW_SOURCE_SKILL_MUTATION=true "
                "only for deliberate product-default edits."
            )
        return SOURCE_SKILLS_DIR / f"{name}.json"
    return runtime_skills_dir() / f"{name}.json"


class SkillDefinition:
    """A skill loaded from its definition file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8"))
        self._validate()

    def _validate(self) -> None:
        required = [
            "name",
            "display_name",
            "description",
            "phase",
            "skill_type",
            "plan_prompt",
            "execute_prompt",
            "output_schema",
        ]
        for field in required:
            if field not in self.data:
                raise ValueError(f"Skill definition missing required field: {field} in {self.path}")

    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def display_name(self) -> str:
        return self.data["display_name"]

    @property
    def phase(self) -> str:
        return self.data["phase"]

    @property
    def version(self) -> str:
        return self.data.get("version", "1.0.0")

    @property
    def enabled(self) -> bool:
        return self.data.get("enabled", True)

    @property
    def metadata(self) -> dict:
        return self.data.get("metadata", {})

    def to_dict(self) -> dict:
        return {**self.data, "file": str(self.path.name)}


class SkillUpdateProposal:
    """A proposed improvement to a skill, pending user approval."""

    def __init__(
        self,
        skill_name: str,
        field: str,
        current_value: str,
        proposed_value: str,
        reason: str,
        confidence: float = 0.5,
        project_id: str = "",
    ) -> None:
        self.id = f"{skill_name}_{field}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        self.project_id = str(project_id or "").strip()
        self.skill_name = skill_name
        self.field = field
        self.current_value = current_value
        self.proposed_value = proposed_value
        self.reason = reason
        self.confidence = confidence
        self.status = "pending"
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.reviewed_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "skill_name": self.skill_name,
            "field": self.field,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "reason": self.reason,
            "confidence": self.confidence,
            "status": self.status,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
        }


@dataclass
class SkillCreationProposal:
    """A proposed new skill definition, pending user approval."""

    id: str
    proposed_definition: dict
    source_task_id: str
    source_agent_id: str
    reason: str
    confidence: int
    project_id: str = ""
    status: str = "pending"
    created_at: str = ""
    reviewed_at: str | None = None
    reject_reason: str | None = None
    test_result: dict | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "proposed_definition": self.proposed_definition,
            "source_task_id": self.source_task_id,
            "source_agent_id": self.source_agent_id,
            "reason": self.reason,
            "confidence": self.confidence,
            "status": self.status,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
            "reject_reason": self.reject_reason,
            "test_result": self.test_result,
        }
