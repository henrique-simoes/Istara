"""Safely scaffold missing JSON skill definition files from all_skills.py.

Canonical skill definitions live in backend/app/skills/definitions/*.json.
The SkillManager, dataset generator, and agent-facing docs should treat those
JSON files as the source of truth. This script only helps bootstrap definitions
for legacy skills that exist in all_skills.py but do not yet have a JSON file.

IMPORTANT: Existing definition files are NEVER overwritten by this script.
Existing definitions often contain richer content than all_skills.py, including
academic references, detailed prompts, metadata, and hand-shaped schemas.

Before writing any new file, the script unescapes Python f-string braces in
output_schema and validates that the resulting schema is parseable JSON.

Run: python backend/app/skills/generate_definitions.py
"""

import json
import re
from pathlib import Path

DEFINITIONS_DIR = Path(__file__).parent / "definitions"
ALL_SKILLS_FILE = Path(__file__).parent / "all_skills.py"


def extract_skills_from_source() -> list[dict]:
    """Parse all_skills.py and extract create_skill() call arguments."""
    source = ALL_SKILLS_FILE.read_text()

    skills = []
    # Pattern: VarName = create_skill(\n    skill_name="...",\n    ....\n)
    pattern = r'(\w+)\s*=\s*create_skill\((.*?)\n\)'
    matches = re.findall(pattern, source, re.DOTALL)

    for var_name, args_text in matches:
        skill = {"_var": var_name}

        for key in ["skill_name", "display", "desc", "phase", "skill_type",
                     "plan_prompt", "execute_prompt", "output_schema"]:
            # Match key="""value""" or key="value" patterns
            pat = rf'{key}="""(.*?)"""'
            m = re.search(pat, args_text, re.DOTALL)
            if not m:
                pat = rf'{key}="(.*?)"'
                m = re.search(pat, args_text, re.DOTALL)
            if not m:
                pat = rf'{key}=SkillPhase\.(\w+)'
                m = re.search(pat, args_text)
                if not m:
                    pat = rf'{key}=SkillType\.(\w+)'
                    m = re.search(pat, args_text)

            if m:
                skill[key] = m.group(1)

        if "skill_name" in skill:
            # Unescape Python f-string braces in output_schema
            if "output_schema" in skill:
                skill["output_schema"] = skill["output_schema"].replace("{{", "{").replace("}}", "}")
            skills.append(skill)

    return skills


def validate_schema(schema_text: str, skill_name: str) -> bool:
    """Validate that a schema string is valid JSON."""
    if not schema_text:
        return True
    try:
        json.loads(schema_text)
        return True
    except json.JSONDecodeError as e:
        print(f"    ⚠️  WARNING: {skill_name} has invalid JSON in output_schema: {e}")
        return False


def generate_definitions():
    """Generate individual JSON definition files for NEW skills only."""
    DEFINITIONS_DIR.mkdir(parents=True, exist_ok=True)

    skills = extract_skills_from_source()
    print(f"Found {len(skills)} skills in all_skills.py")

    created = 0
    skipped = 0
    broken = 0

    for skill in skills:
        name = skill.get("skill_name", "")
        if not name:
            continue

        path = DEFINITIONS_DIR / f"{name}.json"
        if path.exists():
            print(f"  ⏭️  {name} (skipped — definition already exists)")
            skipped += 1
            continue

        phase = skill.get("phase", "discover").lower()
        skill_type = skill.get("skill_type", "mixed").lower()
        schema = skill.get("output_schema", "")

        if not validate_schema(schema, name):
            broken += 1
            continue

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
            "output_schema": schema,
            "created_at": "2026-03-14T00:00:00Z",
            "updated_at": "2026-03-14T00:00:00Z",
            "metadata": {
                "author": "Istara",
                "tags": [phase, skill_type],
            },
            "changelog": [{
                "version": "1.0.0",
                "date": "2026-03-14T00:00:00Z",
                "changes": "Initial creation from skill library",
            }],
        }

        path.write_text(json.dumps(defn, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  ✓ {name} ({phase}/{skill_type})")
        created += 1

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
        path = DEFINITIONS_DIR / f"{name}.json"
        if path.exists():
            print(f"  ⏭️  {name} (custom — skipped, definition already exists)")
            skipped += 1
            continue

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
            "metadata": {"author": "Istara", "tags": [phase, stype, "custom"]},
            "changelog": [{"version": "1.0.0", "date": "2026-03-14T00:00:00Z", "changes": "Initial creation"}],
        }
        path.write_text(json.dumps(defn, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  ✓ {name} (custom/{phase})")
        created += 1

    print(f"\n✅ Created {created} new definition files")
    print(f"⏭️  Skipped {skipped} existing definitions (preserved)")
    if broken:
        print(f"⚠️  {broken} skills had invalid schemas and were skipped")
    print(f"📁 Total definitions in {DEFINITIONS_DIR}: {len(list(DEFINITIONS_DIR.glob('*.json')))}")


if __name__ == "__main__":
    generate_definitions()
