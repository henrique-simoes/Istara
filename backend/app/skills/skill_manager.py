"""Skill Manager — self-improving skill lifecycle management.

Handles:
1. Loading skills from individual YAML/JSON definition files
2. Versioning each skill independently (git-tracked)
3. Proposing improvements based on usage patterns
4. User approval workflow for skill updates
5. Skill creation, editing, enabling/disabling
6. Skill health monitoring and quality scoring
7. Autonomous skill creation proposals
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone

from app.config import settings
from app.core.checkpoint import atomic_write
from app.skills.skill_creation import SkillCreationMixin
from app.skills.skill_models import (
    SKILLS_DIR,
    SOURCE_SKILLS_DIR,
    SkillCreationProposal,
    SkillDefinition,
    SkillUpdateProposal,
    runtime_skills_dir,
    skill_definition_dirs,
    writeable_skill_path,
)
from app.skills.skill_proposals import SkillProposalMixin
from app.skills.skill_usage import SkillUsageMixin

logger = logging.getLogger(__name__)


class SkillManager(SkillUsageMixin, SkillProposalMixin, SkillCreationMixin):
    """Manages the skill lifecycle — loading, versioning, improving, and monitoring."""

    def __init__(self) -> None:
        self._definitions: dict[str, SkillDefinition] = {}
        self._proposals: list[SkillUpdateProposal] = []
        self._creation_proposals: list[SkillCreationProposal] = []
        self._usage_stats: dict[str, dict] = {}  # skill_name → {executions, successes, failures, avg_quality}
        runtime_meta_dir = runtime_skills_dir()
        self._proposals_file = runtime_meta_dir / "_proposals.json"
        self._creation_proposals_file = runtime_meta_dir / "_creation_proposals.json"
        self._stats_file = runtime_meta_dir / "_usage_stats.json"

    def ensure_definitions_dir(self) -> None:
        """Create the definitions directory if it doesn't exist."""
        SOURCE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        runtime_skills_dir().mkdir(parents=True, exist_ok=True)

    def load_all(self) -> dict[str, SkillDefinition]:
        """Load all skill definitions from individual JSON files."""
        self.ensure_definitions_dir()
        self._definitions = {}

        for directory in skill_definition_dirs():
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.json")):
                if path.name.startswith("_"):
                    continue  # Skip meta files
                try:
                    defn = SkillDefinition(path)
                    self._definitions[defn.name] = defn
                    logger.info(f"Loaded skill definition: {defn.name} v{defn.version}")
                except Exception as e:
                    logger.error(f"Failed to load skill {path}: {e}")

        # Load usage stats
        if self._stats_file.exists():
            try:
                self._usage_stats = json.loads(self._stats_file.read_text())
            except Exception:
                self._usage_stats = {}

        # Load pending proposals
        if self._proposals_file.exists():
            try:
                data = json.loads(self._proposals_file.read_text())
                self._proposals = []
                for p in data:
                    prop = SkillUpdateProposal(p["skill_name"], p["field"], p.get("current_value", ""),
                                                p.get("proposed_value", ""), p["reason"], p.get("confidence", 0.5),
                                                project_id=p.get("project_id", ""))
                    prop.id = p["id"]
                    prop.status = p["status"]
                    prop.created_at = p["created_at"]
                    prop.reviewed_at = p.get("reviewed_at")
                    self._proposals.append(prop)
            except Exception:
                self._proposals = []

        # Load creation proposals
        if self._creation_proposals_file.exists():
            try:
                data = json.loads(self._creation_proposals_file.read_text())
                self._creation_proposals = []
                for p in data:
                    cp = SkillCreationProposal(
                        id=p["id"],
                        proposed_definition=p["proposed_definition"],
                        source_task_id=p["source_task_id"],
                        source_agent_id=p["source_agent_id"],
                        reason=p["reason"],
                        confidence=p["confidence"],
                        project_id=p.get("project_id", ""),
                        status=p.get("status", "pending"),
                        created_at=p.get("created_at", ""),
                        reviewed_at=p.get("reviewed_at"),
                        reject_reason=p.get("reject_reason"),
                        test_result=p.get("test_result"),
                    )
                    self._creation_proposals.append(cp)
            except Exception:
                self._creation_proposals = []

        logger.info(f"Loaded {len(self._definitions)} skill definitions.")
        return self._definitions

    def get(self, name: str) -> SkillDefinition | None:
        return self._definitions.get(name)

    def list_all(self) -> list[SkillDefinition]:
        return list(self._definitions.values())

    def list_by_phase(self, phase: str) -> list[SkillDefinition]:
        return [d for d in self._definitions.values() if d.phase == phase]

    # --- CRUD Operations ---

    def create_skill(self, data: dict) -> SkillDefinition:
        """Create a new skill definition file."""
        self.ensure_definitions_dir()
        name = data["name"]
        data.setdefault("version", "1.0.0")
        data.setdefault("enabled", True)
        data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        data.setdefault("changelog", [{"version": "1.0.0", "date": data["created_at"], "changes": "Initial creation"}])

        source_write = bool(data.pop("_source", False))
        path = writeable_skill_path(name, source=source_write)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False))

        defn = SkillDefinition(path)
        self._definitions[name] = defn
        logger.info(f"Created skill: {name}")
        return defn

    def update_skill(self, name: str, updates: dict, changelog_entry: str = "") -> SkillDefinition:
        """Update a skill definition — increments version automatically."""
        defn = self._definitions.get(name)
        if not defn:
            raise ValueError(f"Skill not found: {name}")
        source_write = bool(updates.pop("_source", False))

        # Increment patch version
        parts = defn.version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        new_version = ".".join(parts)

        # Update data
        defn.data.update(updates)
        defn.data["version"] = new_version
        defn.data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Add changelog
        changelog = defn.data.setdefault("changelog", [])
        changelog.append({
            "version": new_version,
            "date": defn.data["updated_at"],
            "changes": changelog_entry or f"Updated fields: {', '.join(updates.keys())}",
        })

        path = defn.path
        if not source_write and defn.path.is_relative_to(SOURCE_SKILLS_DIR):
            path = writeable_skill_path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            defn.path = path
        elif source_write:
            path = writeable_skill_path(name, source=True)
        atomic_write(path, json.dumps(defn.data, indent=2, ensure_ascii=False))
        logger.info(f"Updated skill: {name} → v{new_version}")
        return defn

    def delete_skill(self, name: str) -> bool:
        """Delete a skill definition file."""
        defn = self._definitions.get(name)
        if not defn:
            return False

        if defn.path.is_relative_to(SOURCE_SKILLS_DIR) and not settings.allow_source_skill_mutation:
            disabled = {**defn.data, "enabled": False, "lifecycle": "local_deleted"}
            path = writeable_skill_path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(path, json.dumps(disabled, indent=2, ensure_ascii=False))
        else:
            # Move to a backup instead of hard delete
            backup_dir = defn.path.parent / "_deleted"
            backup_dir.mkdir(exist_ok=True)
            shutil.move(str(defn.path), str(backup_dir / defn.path.name))

        del self._definitions[name]
        logger.info(f"Deleted skill: {name} (backed up)")
        return True

    def toggle_skill(self, name: str, enabled: bool) -> SkillDefinition:
        """Enable or disable a skill."""
        return self.update_skill(name, {"enabled": enabled},
                                  f"{'Enabled' if enabled else 'Disabled'} skill")

# Singleton
skill_manager = SkillManager()
