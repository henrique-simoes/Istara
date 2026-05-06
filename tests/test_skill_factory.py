"""Regression tests for generated skill prompt and output contracts."""

import json

import pytest

from app.skills.base import SkillInput, SkillPhase, SkillType
from app.skills.skill_factory import create_skill


@pytest.mark.asyncio
async def test_generated_skill_preserves_literal_prompt_braces(monkeypatch):
    """Literal braces in methodology text must not be treated as format fields."""

    async def fake_chat(**kwargs):
        prompt = kwargs["messages"][0]["content"]
        assert "Context: test project context" in prompt
        assert "Survey Data: [RESEARCH_DATA_BELOW]" in prompt
        assert "Tag findings with ux-law:{id}." in prompt
        return {
            "message": {
                "content": json.dumps(
                    {
                        "nuggets": [
                            {
                                "text": "Three participants abandoned onboarding.",
                                "source": "survey",
                                "tags": ["ux-law:{id}"],
                            }
                        ],
                        "facts": [{"text": "Onboarding abandonment appeared in survey data."}],
                        "insights": [
                            {
                                "text": "Onboarding friction is likely affecting activation.",
                                "confidence": "medium",
                            }
                        ],
                        "recommendations": [
                            {
                                "text": "Shorten the first onboarding step.",
                                "priority": "high",
                            }
                        ],
                        "summary": "Completed survey analysis.",
                    }
                )
            }
        }

    monkeypatch.setattr("app.skills.skill_factory.ollama.chat", fake_chat)
    skill_cls = create_skill(
        skill_name="literal-brace-skill",
        display="Literal Brace Skill",
        desc="Tests prompt formatting with literal braces.",
        phase=SkillPhase.DISCOVER,
        skill_type=SkillType.QUANTITATIVE,
        plan_prompt="Plan for {context}; keep ux-law:{id}.",
        execute_prompt=(
            "Context: {context}\n"
            "Survey Data: {content}\n"
            "Tag findings with ux-law:{id}."
        ),
        output_schema='{"nuggets": [{"text": "..."}], "summary": "..."}',
    )

    output = await skill_cls().execute(
        SkillInput(
            project_id="project-1",
            user_context="survey rows",
            project_context="test project context",
        )
    )

    assert output.success is True
    assert output.json_success is True
    assert output.nuggets[0]["tags"] == ["ux-law:{id}"]


@pytest.mark.asyncio
async def test_generated_skill_plan_falls_back_on_empty_llm_response(monkeypatch):
    async def fake_chat(**kwargs):
        return {"message": {"content": ""}}

    monkeypatch.setattr("app.skills.skill_factory.ollama.chat", fake_chat)
    skill_cls = create_skill(
        skill_name="empty-plan-skill",
        display="Empty Plan Skill",
        desc="Tests plan fallback behavior.",
        phase=SkillPhase.DEFINE,
        skill_type=SkillType.MIXED,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"summary": "..."}',
    )

    plan = await skill_cls().plan(SkillInput(project_id="project-1", user_context="Need a plan"))

    assert plan["skill"] == "empty-plan-skill"
    assert plan["fallback"] is True
    assert "Empty Plan Skill Plan" in plan["plan"]
    assert "Need a plan" in plan["plan"]


@pytest.mark.asyncio
async def test_generated_skill_plan_falls_back_on_llm_error(monkeypatch):
    async def fake_chat(**kwargs):
        raise RuntimeError("No compute nodes available for chat")

    monkeypatch.setattr("app.skills.skill_factory.ollama.chat", fake_chat)
    skill_cls = create_skill(
        skill_name="error-plan-skill",
        display="Error Plan Skill",
        desc="Tests plan fallback after provider errors.",
        phase=SkillPhase.DELIVER,
        skill_type=SkillType.QUALITATIVE,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"summary": "..."}',
    )

    plan = await skill_cls().plan(SkillInput(project_id="project-1", user_context="Provider down"))

    assert plan["skill"] == "error-plan-skill"
    assert plan["fallback"] is True
    assert "Error Plan Skill Plan" in plan["plan"]
