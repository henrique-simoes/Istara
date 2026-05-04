"""Regression tests for source-code versus local-runtime write boundaries."""

from __future__ import annotations

import json

import pytest


def test_persona_memory_writes_to_runtime_overlay(tmp_path, monkeypatch):
    from app.config import settings
    from app.core import agent_identity

    runtime_dir = tmp_path / "runtime_personas"
    monkeypatch.setattr(settings, "runtime_personas_dir", str(runtime_dir))
    monkeypatch.setattr(settings, "allow_source_persona_mutation", False)

    assert agent_identity.save_agent_memory("istara-main", "# Local Memory\n") is True

    runtime_file = runtime_dir / "istara-main" / "MEMORY.md"
    source_file = agent_identity.SOURCE_PERSONAS_DIR / "istara-main" / "MEMORY.md"
    assert runtime_file.exists()
    assert runtime_file.read_text(encoding="utf-8") == "# Local Memory\n"
    assert source_file.exists()
    assert source_file.read_text(encoding="utf-8") != "# Local Memory\n"


def test_source_persona_write_is_blocked_by_default(tmp_path, monkeypatch):
    from app.config import settings
    from app.core.agent_identity import writeable_persona_path

    monkeypatch.setattr(settings, "runtime_personas_dir", str(tmp_path / "personas"))
    monkeypatch.setattr(settings, "allow_source_persona_mutation", False)

    with pytest.raises(PermissionError):
        writeable_persona_path("istara-main", "CORE.md", source=True)


def test_skill_creation_writes_to_runtime_overlay(tmp_path, monkeypatch):
    from app.config import settings
    from app.skills.skill_manager import SkillManager

    runtime_dir = tmp_path / "runtime_skills"
    monkeypatch.setattr(settings, "runtime_skills_dir", str(runtime_dir))
    monkeypatch.setattr(settings, "allow_source_skill_mutation", False)

    manager = SkillManager()
    definition = {
        "name": "local-test-skill",
        "display_name": "Local Test Skill",
        "description": "A local runtime-only test skill.",
        "phase": "discover",
        "skill_type": "mixed",
        "plan_prompt": "Plan.",
        "execute_prompt": "Execute.",
        "output_schema": "{}",
    }

    created = manager.create_skill(definition)

    runtime_file = runtime_dir / "local-test-skill.json"
    assert created.path == runtime_file
    assert runtime_file.exists()
    assert json.loads(runtime_file.read_text(encoding="utf-8"))["name"] == "local-test-skill"


def test_source_skill_write_is_blocked_by_default(tmp_path, monkeypatch):
    from app.config import settings
    from app.skills.skill_manager import writeable_skill_path

    monkeypatch.setattr(settings, "runtime_skills_dir", str(tmp_path / "skills"))
    monkeypatch.setattr(settings, "allow_source_skill_mutation", False)

    with pytest.raises(PermissionError):
        writeable_skill_path("user-interviews", source=True)
