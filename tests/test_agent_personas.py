"""Regression tests for hardcoded agent personas."""

from __future__ import annotations


def test_system_agents_have_complete_source_personas():
    from app.core.agent_identity import IDENTITY_FILES, SOURCE_PERSONAS_DIR
    from app.services.agent_service import SYSTEM_AGENTS

    missing: list[str] = []
    for agent in SYSTEM_AGENTS:
        persona_dir = SOURCE_PERSONAS_DIR / agent["id"]
        for filename in IDENTITY_FILES:
            path = persona_dir / filename
            if not path.exists() or not path.read_text(encoding="utf-8").strip():
                missing.append(f"{agent['id']}/{filename}")

    assert missing == []


def test_piper_is_hardcoded_design_lead_with_persona():
    from app.core.agent_identity import get_agent_display_name
    from app.models.agent import AgentRole
    from app.services.agent_service import SYSTEM_AGENTS

    piper = next(
        (agent for agent in SYSTEM_AGENTS if agent["id"] == "design-lead"), None
    )

    assert piper is not None
    assert piper["name"] == "Piper"
    assert piper["role"] == AgentRole.DESIGN_LEAD
    assert get_agent_display_name("design-lead") == "Piper"


def test_custom_persona_creation_repairs_incomplete_directory(tmp_path, monkeypatch):
    from app.config import settings
    from app.core.agent_identity import IDENTITY_FILES
    from app.core.self_evolution import self_evolution

    runtime_dir = tmp_path / "personas"
    agent_dir = runtime_dir / "piper-test"
    agent_dir.mkdir(parents=True)
    (agent_dir / "CORE.md").write_text("# Partial\n", encoding="utf-8")
    monkeypatch.setattr(settings, "runtime_personas_dir", str(runtime_dir))

    import asyncio

    assert asyncio.run(
        self_evolution.create_persona_for_custom_agent(
            "piper-test",
            "Piper Test",
            "Design interfaces from research evidence.",
        )
    )

    for filename in IDENTITY_FILES:
        path = agent_dir / filename
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip()
