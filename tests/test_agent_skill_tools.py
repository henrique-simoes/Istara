from types import SimpleNamespace

import pytest

import app.core.agent_skill_tools as agent_skill_tools
from app.skills.base import BaseSkill, SkillInput, SkillOutput, SkillPhase, SkillType
from app.skills.registry import registry
from app.skills.skill_manager import skill_manager


class DummySkill(BaseSkill):
    def __init__(self, name: str, description: str) -> None:
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_name(self) -> str:
        return self._name.replace("-", " ").title()

    @property
    def description(self) -> str:
        return self._description

    @property
    def phase(self) -> SkillPhase:
        return SkillPhase.DISCOVER

    @property
    def skill_type(self) -> SkillType:
        return SkillType.MIXED

    async def plan(self, skill_input: SkillInput) -> dict:
        return {"plan": skill_input.user_context}

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        return SkillOutput(success=True, summary=f"ran {self.name}")


@pytest.mark.asyncio
async def test_rank_skill_candidates_uses_reasoning_bank_and_memento(monkeypatch):
    original_skills = registry._skills
    original_stats = skill_manager._usage_stats
    registry._skills = {
        "journey-mapping": DummySkill("journey-mapping", "Map customer journeys."),
        "nps-analysis": DummySkill("nps-analysis", "Analyze NPS and survey sentiment."),
    }
    skill_manager._usage_stats = {
        "nps-analysis": {
            "executions": 8,
            "successes": 8,
            "failures": 0,
            "total_quality": 7.2,
            "utility_score": 0.9,
        }
    }

    async def fake_retrieve(**_kwargs):
        return [
            {
                "domain": "nps-analysis",
                "tags": ["nps-analysis", "memento"],
                "title": "Successful nps-analysis strategy",
                "description": "",
                "content": "Use nps-analysis for detractor survey interpretation.",
                "outcome": "success",
                "retrieval_score": 0.8,
            }
        ]

    class FakeReasoningBank:
        retrieve = staticmethod(fake_retrieve)

    async def fake_telemetry_quality_boost(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(agent_skill_tools, "_telemetry_quality_boost", fake_telemetry_quality_boost)
    monkeypatch.setattr("app.core.reasoning_bank.reasoning_bank", FakeReasoningBank())

    try:
        candidates = await agent_skill_tools.rank_skill_candidates(
            task=SimpleNamespace(
                title="Analyze NPS detractors",
                description="Find reasons behind low recommendation scores.",
                project_id="project-1",
                agent_id="agent-1",
            ),
            include_semantic=False,
        )
    finally:
        registry._skills = original_skills
        skill_manager._usage_stats = original_stats

    assert candidates[0].name == "nps-analysis"
    assert any("memento_usage" in reason for reason in candidates[0].reasons)
    assert any("reasoning_bank" in reason for reason in candidates[0].reasons)


def test_build_run_skill_tool_constrains_skill_enum():
    candidates = [
        agent_skill_tools.SkillCandidate(
            name="user-interviews",
            display_name="User Interviews",
            description="Analyze interview transcripts.",
            phase="discover",
            score=1.0,
        )
    ]

    tool = agent_skill_tools.build_run_skill_tool(candidates)[0]

    skill_prop = tool["function"]["parameters"]["properties"]["skill_name"]
    assert skill_prop["enum"] == ["user-interviews"]
    assert tool["function"]["parameters"]["additionalProperties"] is False
