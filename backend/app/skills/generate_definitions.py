"""Generate individual JSON skill definition files from all_skills.py data.

This reads the skill configurations and writes them as individual JSON files
that the SkillManager can load, version, and self-improve independently.

Run: python backend/app/skills/generate_definitions.py
"""

import json
import re
import sys
from pathlib import Path

DEFINITIONS_DIR = Path(__file__).parent / "definitions"
ALL_SKILLS_FILE = Path(__file__).parent / "all_skills.py"


def extract_skills_from_source() -> list[dict]:
    """Parse all_skills.py and extract create_skill() call arguments."""
    source = ALL_SKILLS_FILE.read_text()

    # Find all create_skill() calls
    skills = []
    # Pattern: VarName = create_skill(\n    skill_name="...",\n    ....\n)
    pattern = r'(\w+)\s*=\s*create_skill\((.*?)\n\)'
    matches = re.findall(pattern, source, re.DOTALL)

    for var_name, args_text in matches:
        skill = {"_var": var_name}

        # Extract each keyword argument
        for key in ["skill_name", "display", "desc", "phase", "skill_type",
                     "plan_prompt", "execute_prompt", "output_schema"]:
            # Match key="value" or key="""value""" patterns
            pat = rf'{key}="""(.*?)"""'
            m = re.search(pat, args_text, re.DOTALL)
            if not m:
                pat = rf'{key}="(.*?)"'
                m = re.search(pat, args_text, re.DOTALL)
            if not m:
                # Try SkillPhase.X or SkillType.X
                pat = rf'{key}=SkillPhase\.(\w+)'
                m = re.search(pat, args_text)
                if not m:
                    pat = rf'{key}=SkillType\.(\w+)'
                    m = re.search(pat, args_text)

            if m:
                skill[key] = m.group(1)

        if "skill_name" in skill:
            skills.append(skill)

    return skills


def generate_definitions():
    """Generate individual JSON definition files."""
    DEFINITIONS_DIR.mkdir(parents=True, exist_ok=True)

    skills = extract_skills_from_source()
    print(f"Found {len(skills)} skills in all_skills.py")

    for skill in skills:
        name = skill.get("skill_name", "")
        if not name:
            continue

        phase = skill.get("phase", "discover").lower()
        skill_type = skill.get("skill_type", "mixed").lower()

        defn = {
            "name": name,
            "display_name": skill.get("display", name.replace("-", " ").title()),
            "description": skill.get("desc", ""),
            "phase": phase,
            "skill_type": skill_type,
            "version": "1.0.0",
            "enabled": True,
            "plan_prompt": skill.get("plan_prompt", ""),
            "execute_prompt": skill.get("execute_prompt", ""),
            "output_schema": skill.get("output_schema", ""),
            "created_at": "2026-03-14T00:00:00Z",
            "updated_at": "2026-03-14T00:00:00Z",
            "metadata": {
                "author": "ReClaw",
                "tags": [phase, skill_type],
            },
            "changelog": [{
                "version": "1.0.0",
                "date": "2026-03-14T00:00:00Z",
                "changes": "Initial creation from skill library",
            }],
        }

        path = DEFINITIONS_DIR / f"{name}.json"
        path.write_text(json.dumps(defn, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  ✓ {name} ({phase}/{skill_type})")

    # Hand-written skills (reference only — they have custom Python implementations)
    custom_skills = [
        ("user-interviews", "User Interviews", "discover", "qualitative",
         "Plan, conduct, and analyze user interviews. Generate interview guides, process transcripts, extract nuggets and themes, synthesize findings.",
         "app.skills.discover.user_interviews.UserInterviewsSkill"),
        ("contextual-inquiry", "Contextual Inquiry", "discover", "qualitative",
         "Structure and analyze contextual inquiry observations — studying users in their natural work environment.",
         "app.skills.discover.contextual_inquiry.ContextualInquirySkill"),
        ("diary-studies", "Diary Studies", "discover", "qualitative",
         "Design diary study prompts, analyze entries over time, identify behavioral patterns and emotional arcs.",
         "app.skills.discover.diary_studies.DiaryStudiesSkill"),
    ]

    for name, display, phase, stype, desc, module in custom_skills:
        defn = {
            "name": name,
            "display_name": display,
            "description": desc,
            "phase": phase,
            "skill_type": stype,
            "version": "1.0.0",
            "enabled": True,
            "implementation": "custom",
            "module": module,
            "created_at": "2026-03-14T00:00:00Z",
            "updated_at": "2026-03-14T00:00:00Z",
            "metadata": {"author": "ReClaw", "tags": [phase, stype, "custom"]},
            "changelog": [{"version": "1.0.0", "date": "2026-03-14T00:00:00Z", "changes": "Initial creation"}],
        }
        path = DEFINITIONS_DIR / f"{name}.json"
        path.write_text(json.dumps(defn, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  ✓ {name} (custom/{phase})")

    total = len(skills) + len(custom_skills)
    print(f"\n✅ Generated {total} skill definition files in {DEFINITIONS_DIR}")


if __name__ == "__main__":
    generate_definitions()
