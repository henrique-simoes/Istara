"""Tests for Formal Evaluation Skill (LLM-as-Judge)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.skills.evaluation_skill import EvaluationSkill
from app.skills.base import SkillInput

@pytest.mark.asyncio
async def test_evaluation_skill_triggers_multi_model_validation():
    skill = EvaluationSkill()
    skill_input = SkillInput(
        project_id="test",
        user_context="Some research output to evaluate"
    )
    
    # Mock validation methods
    with patch("app.core.validation.adversarial_review", new_callable=AsyncMock) as mock_adv:
        with patch("app.core.validation.full_ensemble", new_callable=AsyncMock) as mock_ens:
            
            # Setup mock returns
            mock_adv.return_value = MagicMock(metadata={"review_text": "Critical feedback"})
            
            ens_res = MagicMock()
            ens_res.consensus.agreement_score = 0.85
            ens_res.consensus.kappa = 0.72
            ens_res.responses = ["Resp 1", "Resp 2"]
            ens_res.best_response = "Best synthesis"
            mock_ens.return_value = ens_res
            
            output = await skill.execute(skill_input)
            
            # Should have called both validation strategies
            assert output.success is True
            mock_adv.assert_called_once()
            mock_ens.assert_called_once()
            
            # Artifact should contain the combined report
            report = output.artifacts["evaluation_report.md"]
            assert "## Quality Audit Report" in report
            assert "0.85" in report
            assert "Critical feedback" in report
