"""Export skill definitions from all_skills.py to individual JSON files.

Run this once to generate the individual skill definition files:
    python -m app.skills.export_definitions

After running, skills load from definitions/ JSON files via SkillManager.
"""

import json
import re
from pathlib import Path

DEFINITIONS_DIR = Path(__file__).parent / "definitions"


def export_all():
    """Parse all_skills.py and export each create_skill() call as a JSON file."""
    DEFINITIONS_DIR.mkdir(parents=True, exist_ok=True)

    from app.skills.all_skills import ALL_FACTORY_SKILLS
    from app.skills.base import SkillPhase, SkillType

    for skill_class in ALL_FACTORY_SKILLS:
        instance = skill_class()
        defn = {
            "name": instance.name,
            "display_name": instance.display_name,
            "description": instance.description,
            "phase": instance.phase.value,
            "skill_type": instance.skill_type.value,
            "version": "1.0.0",
            "enabled": True,
            "plan_prompt": "",
            "execute_prompt": "",
            "output_schema": "",
            "created_at": "2026-03-14T00:00:00Z",
            "updated_at": "2026-03-14T00:00:00Z",
            "changelog": [{"version": "1.0.0", "date": "2026-03-14T00:00:00Z", "changes": "Initial creation"}],
        }

        # Try to get prompts from the class
        # The factory sets these as closure variables — we need to extract from the source
        path = DEFINITIONS_DIR / f"{instance.name}.json"
        path.write_text(json.dumps(defn, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Exported: {instance.name} → {path.name}")

    # Also export hand-written skills as definitions
    hand_written = [
        {
            "name": "user-interviews",
            "display_name": "User Interviews",
            "description": "Plan, conduct, and analyze user interviews. Generate interview guides, process transcripts, extract nuggets and themes, and synthesize findings across multiple interviews.",
            "phase": "discover",
            "skill_type": "qualitative",
            "implementation": "custom",
            "module": "app.skills.discover.user_interviews.UserInterviewsSkill",
        },
        {
            "name": "contextual-inquiry",
            "display_name": "Contextual Inquiry",
            "description": "Structure and analyze contextual inquiry observations — studying users in their natural work environment.",
            "phase": "discover",
            "skill_type": "qualitative",
            "implementation": "custom",
            "module": "app.skills.discover.contextual_inquiry.ContextualInquirySkill",
        },
        {
            "name": "diary-studies",
            "display_name": "Diary Studies",
            "description": "Design diary study prompts, analyze entries over time, identify behavioral patterns and emotional arcs across longitudinal self-reported data.",
            "phase": "discover",
            "skill_type": "qualitative",
            "implementation": "custom",
            "module": "app.skills.discover.diary_studies.DiaryStudiesSkill",
        },
    ]

    for defn in hand_written:
        defn.update({
            "version": "1.0.0",
            "enabled": True,
            "created_at": "2026-03-14T00:00:00Z",
            "updated_at": "2026-03-14T00:00:00Z",
            "changelog": [{"version": "1.0.0", "date": "2026-03-14T00:00:00Z", "changes": "Initial creation"}],
        })
        path = DEFINITIONS_DIR / f"{defn['name']}.json"
        path.write_text(json.dumps(defn, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Exported (custom): {defn['name']} → {path.name}")

    print(f"\nDone! Exported {len(ALL_FACTORY_SKILLS) + len(hand_written)} skills to {DEFINITIONS_DIR}")


if __name__ == "__main__":
    export_all()
