"""Regression tests for source-code versus local-runtime write boundaries."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


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


def test_skill_discovery_ignores_macos_appledouble_metadata(tmp_path, monkeypatch, caplog):
    from app.skills import skill_manager as skill_manager_module
    from app.skills.skill_manager import SkillManager

    definition = {
        "name": "portable-skill",
        "display_name": "Portable Skill",
        "description": "A portable skill definition.",
        "phase": "discover",
        "skill_type": "mixed",
        "plan_prompt": "Plan.",
        "execute_prompt": "Execute.",
        "output_schema": "{}",
    }
    (tmp_path / "portable-skill.json").write_text(json.dumps(definition), encoding="utf-8")
    (tmp_path / "._portable-skill.json").write_bytes(b"\x00\x05\x16\x07appledouble")
    monkeypatch.setattr(skill_manager_module, "skill_definition_dirs", lambda: [tmp_path])

    loaded = SkillManager().load_all()

    assert list(loaded) == ["portable-skill"]
    assert "._portable-skill.json" not in caplog.text


def test_default_skill_registry_ignores_macos_appledouble_metadata(tmp_path, monkeypatch):
    from app.skills import registry as registry_module
    from app.skills import skill_manager as skill_manager_module

    (tmp_path / "portable-skill.json").write_text("{}", encoding="utf-8")
    (tmp_path / "._portable-skill.json").write_bytes(b"\x00\x05\x16\x07appledouble")
    monkeypatch.setattr(skill_manager_module, "skill_definition_dirs", lambda: [tmp_path])

    registered_definitions: list[str] = []

    class FakeRegistry:
        def register(self, _skill_class):
            return None

        def register_from_definition(self, name: str):
            registered_definitions.append(name)
            return True

        def list_all(self):
            return []

        def list_by_phase(self, _phase):
            return []

    monkeypatch.setattr(registry_module, "registry", FakeRegistry())

    registry_module.load_default_skills()

    assert registered_definitions == ["portable-skill"]


def test_runtime_freshness_flags_frontend_source_newer_than_build(tmp_path):
    from app.core.runtime_freshness import detect_runtime_freshness

    build_id = tmp_path / "frontend" / ".next" / "BUILD_ID"
    source = tmp_path / "frontend" / "src" / "components" / "integrations" / "IntegrationsOverview.tsx"
    build_id.parent.mkdir(parents=True)
    source.parent.mkdir(parents=True)
    build_id.write_text("test-build\n", encoding="utf-8")
    source.write_text("export default function IntegrationsOverview() { return null; }\n", encoding="utf-8")

    old_time = 1_700_000_000
    new_time = old_time + 60
    os.utime(build_id, (old_time, old_time))
    os.utime(source, (new_time, new_time))

    result = detect_runtime_freshness(tmp_path, ttl_seconds=0)

    assert result["frontend"]["stale"] is True
    assert result["frontend"]["status"] == "stale"
    assert result["frontend"]["source_newer_than_build_count"] == 1
    assert result["frontend"]["source_newer_than_build"] == [
        "frontend/src/components/integrations/IntegrationsOverview.tsx"
    ]


def test_runtime_freshness_reports_fresh_frontend_build(tmp_path):
    from app.core.runtime_freshness import detect_runtime_freshness

    build_id = tmp_path / "frontend" / ".next" / "BUILD_ID"
    source = tmp_path / "frontend" / "src" / "components" / "interfaces" / "InterfacesView.tsx"
    build_id.parent.mkdir(parents=True)
    source.parent.mkdir(parents=True)
    build_id.write_text("test-build\n", encoding="utf-8")
    source.write_text("export default function InterfacesView() { return null; }\n", encoding="utf-8")

    build_time = 1_700_000_060
    old_time = build_time - 60
    os.utime(build_id, (build_time, build_time))
    os.utime(source, (old_time, old_time))

    result = detect_runtime_freshness(tmp_path, ttl_seconds=0)

    assert result["frontend"]["stale"] is False
    assert result["frontend"]["status"] == "fresh"
    assert result["frontend"]["source_newer_than_build_count"] == 0


def test_status_bar_surfaces_stale_runtime_bundle_diagnostics() -> None:
    status_bar = read_repo("frontend/src/components/layout/StatusBar.tsx")
    route = read_repo("backend/app/api/routes/settings.py")
    freshness = read_repo("backend/app/core/runtime_freshness.py")

    assert "const [runtimeFreshness, setRuntimeFreshness]" in status_bar
    assert "setRuntimeFreshness(data.runtime?.frontend || null)" in status_bar
    assert "runtimeFreshness?.stale" in status_bar
    assert "Runtime bundle stale" in status_bar

    assert "from app.core.runtime_freshness import detect_runtime_freshness" in route
    assert '"runtime": detect_runtime_freshness()' in route
    assert "source_newer_than_build_count" in freshness
    assert "The production frontend build predates frontend source changes" in freshness
