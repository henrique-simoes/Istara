"""Skill registry — load, register, and retrieve skills."""

from __future__ import annotations

import logging
from typing import Type

from app.skills.base import BaseSkill, SkillPhase, SkillType

logger = logging.getLogger(__name__)


def _definition_skill_type(value: str) -> SkillType:
    """Map JSON definition taxonomy to runtime skill types."""
    try:
        return SkillType(value)
    except ValueError:
        logger.warning(
            "Skill definition uses non-runtime skill_type %r; registering as mixed",
            value,
        )
        return SkillType.MIXED


class SkillRegistry:
    """Central registry for all UXR skills."""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill_class: Type[BaseSkill]) -> None:
        """Register a skill class."""
        instance = skill_class()
        self._skills[instance.name] = instance
        logger.info(f"Registered skill: {instance.name} ({instance.phase.value})")

    def get(self, name: str) -> BaseSkill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_all(self) -> list[BaseSkill]:
        """List all registered skills."""
        return list(self._skills.values())

    def list_by_phase(self, phase: SkillPhase) -> list[BaseSkill]:
        """List skills for a specific Double Diamond phase."""
        return [s for s in self._skills.values() if s.phase == phase]

    def list_names(self) -> list[str]:
        """List all skill names."""
        return list(self._skills.keys())

    def to_dict(self) -> dict:
        """Serialize all skills metadata."""
        return {
            "skills": [s.to_dict() for s in self._skills.values()],
            "count": len(self._skills),
            "by_phase": {
                phase.value: len(self.list_by_phase(phase))
                for phase in SkillPhase
            },
        }

    def register_from_definition(self, name: str) -> bool:
        """Load a single skill JSON from definitions/ and register at runtime."""
        from app.skills.skill_factory import create_skill
        from app.skills.skill_manager import SkillDefinition, SKILLS_DIR

        path = SKILLS_DIR / f"{name}.json"
        if not path.exists():
            logger.warning(f"Skill definition not found: {path}")
            return False

        try:
            defn = SkillDefinition(path)
        except Exception as e:
            logger.error(f"Failed to load skill definition {name}: {e}")
            return False

        skill_class = create_skill(
            skill_name=defn.data["name"],
            display=defn.data["display_name"],
            desc=defn.data["description"],
            phase=SkillPhase(defn.data["phase"]),
            skill_type=_definition_skill_type(defn.data["skill_type"]),
            plan_prompt=defn.data["plan_prompt"],
            execute_prompt=defn.data["execute_prompt"],
            output_schema=defn.data["output_schema"],
        )
        self.register(skill_class)
        logger.info(f"Registered skill from definition: {name}")
        return True


# Global registry instance
registry = SkillRegistry()


def load_default_skills() -> None:
    """Load all built-in skills into the registry."""
    # Hand-crafted skills (complex logic)
    from app.skills.discover.user_interviews import UserInterviewsSkill
    from app.skills.discover.contextual_inquiry import ContextualInquirySkill
    from app.skills.discover.diary_studies import DiaryStudiesSkill
    from app.skills.discover.channel_deployment import ChannelResearchDeploymentSkill
    from app.skills.intercoder import KappaIntercoderSkill

    registry.register(UserInterviewsSkill)
    registry.register(ContextualInquirySkill)
    registry.register(DiaryStudiesSkill)
    registry.register(ChannelResearchDeploymentSkill)
    registry.register(KappaIntercoderSkill)

    # Factory-generated skills (standard pattern)
    from app.skills.all_skills import ALL_FACTORY_SKILLS

    for skill_class in ALL_FACTORY_SKILLS:
        # Skip factory kappa — replaced by hand-written KappaIntercoderSkill
        if skill_class().name == "kappa-thematic-analysis":
            continue
        registry.register(skill_class)

    logger.info(f"Loaded {len(registry.list_all())} skills total.")
    for phase in SkillPhase:
        count = len(registry.list_by_phase(phase))
        logger.info(f"  {phase.value}: {count} skills")
