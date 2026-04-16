"""Tests for methodology-wrapped browser skills."""

import pytest
from unittest.mock import AsyncMock, patch
from app.skills.browser_skills import CompetitiveAnalysisSkill, AccessibilityAuditSkill, HeuristicEvaluationSkill
from app.skills.base import SkillInput

@pytest.mark.asyncio
async def test_competitive_analysis_extracts_urls():
    skill = CompetitiveAnalysisSkill()
    skill_input = SkillInput(
        project_id="test",
        urls=["https://google.com", "https://apple.com"],
        user_context="Analyze these competitors"
    )
    
    # Try patching the source module
    with patch("app.services.browser_service.browse_website", new_callable=AsyncMock) as mock_browse:
        mock_browse.return_value = {"result": "Mock data", "extracted_content": ["pattern 1"]}
        
        output = await skill.execute(skill_input)
        
        assert output.success is True
        assert mock_browse.call_count == 2
        assert "https://google.com" in output.artifacts["web_data.txt"]

@pytest.mark.asyncio
async def test_accessibility_audit_uses_url():
    skill = AccessibilityAuditSkill()
    skill_input = SkillInput(project_id="test", urls=["https://example.com"])
    
    with patch("app.services.browser_service.browse_website", new_callable=AsyncMock) as mock_browse:
        mock_browse.return_value = {"result": "Accessibility tree"}
        output = await skill.execute(skill_input)
        
        assert output.success is True
        mock_browse.assert_called_once()
        assert "Accessibility tree" in output.artifacts["accessibility_report.txt"]

@pytest.mark.asyncio
async def test_heuristic_evaluation_uses_url():
    skill = HeuristicEvaluationSkill()
    skill_input = SkillInput(project_id="test", urls=["https://test.com"])
    
    with patch("app.services.browser_service.browse_website", new_callable=AsyncMock) as mock_browse:
        mock_browse.return_value = {"result": "Heuristic findings"}
        output = await skill.execute(skill_input)
        
        assert output.success is True
        mock_browse.assert_called_once()
        assert "Heuristic findings" in output.artifacts["heuristic_report.txt"]
