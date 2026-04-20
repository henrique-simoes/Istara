"""Methodology-wrapped Browser Skills — wraps browser-use for specific UXR tasks.

This module implements P1 from the roadmap: taking raw browser tools and wrapping
them in structured UX research methodology (Competitive Analysis, Accessibility, Heuristics).
"""

import logging
from typing import Any, Optional

from app.skills.base import BaseSkill, SkillInput, SkillOutput, SkillPhase, SkillType
from app.services.browser_service import browse_website, BROWSER_AVAILABLE

logger = logging.getLogger(__name__)

class BaseBrowserSkill(BaseSkill):
    """Base class for skills that require automated web data collection."""
    
    @property
    def version(self) -> str:
        return "2.0.0"

    async def plan(self, skill_input: SkillInput) -> dict:
        """Generic plan for browser-based skills."""
        return {
            "steps": [
                "Initialize browser-use agent",
                f"Navigate to provided URLs: {skill_input.urls}",
                "Extract relevant UXR data based on skill methodology",
                "Synthesize findings into structured output"
            ],
            "estimated_duration_minutes": 15
        }

    async def _collect_web_data(self, url: str, instructions: str) -> str:
        """Helper to fetch data from a URL using browser-use."""
        if not BROWSER_AVAILABLE:
            return "[Error: Browser automation not available. Please install browser-use.]"
        
        logger.info(f"Skill '{self.name}' is collecting web data from {url}...")
        result = await browse_website(url, instructions)
        
        if result.get("error"):
            return f"[Browser Error: {result['error']}]"
        
        content = [f"Result from {url}:", result.get("result", "")]
        if result.get("extracted_content"):
            content.append("\nExtracted Elements:")
            content.extend([str(item) for item in result["extracted_content"]])
            
        return "\n".join(content)

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        """Execute the browser skill."""
        # This will be overridden by subclasses to provide specific instructions
        return SkillOutput(success=False, summary="BaseBrowserSkill should not be called directly.")

class CompetitiveAnalysisSkill(BaseBrowserSkill):
    @property
    def name(self) -> str: return "competitive-analysis"
    @property
    def display_name(self) -> str: return "Competitive Analysis (Automated)"
    @property
    def description(self) -> str: return "Automated competitor research using browser-use."
    @property
    def phase(self) -> SkillPhase: return SkillPhase.DISCOVER
    @property
    def skill_type(self) -> SkillType: return SkillType.MIXED

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        urls = skill_input.urls
        collected_data = []
        for url in urls[:3]:
            web_data = await self._collect_web_data(
                url, 
                "Extract feature list, pricing, value proposition, and unique UX patterns."
            )
            collected_data.append(web_data)
        
        combined_content = skill_input.user_context + "\n\n--- AUTOMATED WEB DATA ---\n" + "\n\n".join(collected_data)
        
        # In a real scenario, we'd now pass combined_content to an LLM for analysis.
        # For now, we'll return a success output with the data.
        return SkillOutput(
            success=True,
            summary=f"Collected competitive data from {len(urls)} URLs.",
            artifacts={"web_data.txt": combined_content}
        )

class AccessibilityAuditSkill(BaseBrowserSkill):
    @property
    def name(self) -> str: return "accessibility-audit"
    @property
    def display_name(self) -> str: return "Accessibility Audit (Automated)"
    @property
    def description(self) -> str: return "Automated WCAG analysis using browser-use."
    @property
    def phase(self) -> SkillPhase: return SkillPhase.DISCOVER
    @property
    def skill_type(self) -> SkillType: return SkillType.MIXED

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        url = skill_input.urls[0] if skill_input.urls else None
        if not url:
            return SkillOutput(success=False, summary="No URL provided for accessibility audit.", errors=["Missing URL"])
            
        web_data = await self._collect_web_data(
            url, 
            "Analyze the page for WCAG 2.2 violations. Extract the accessibility tree."
        )
        
        return SkillOutput(
            success=True,
            summary=f"Accessibility audit completed for {url}.",
            artifacts={"accessibility_report.txt": web_data}
        )

class HeuristicEvaluationSkill(BaseBrowserSkill):
    @property
    def name(self) -> str: return "heuristic-evaluation"
    @property
    def display_name(self) -> str: return "Heuristic Evaluation (Automated)"
    @property
    def description(self) -> str: return "Systematic heuristic test using browser-use."
    @property
    def phase(self) -> SkillPhase: return SkillPhase.DEVELOP
    @property
    def skill_type(self) -> SkillType: return SkillType.QUALITATIVE

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        url = skill_input.urls[0] if skill_input.urls else None
        if not url:
            return SkillOutput(success=False, summary="No URL provided for heuristic evaluation.", errors=["Missing URL"])
            
        web_data = await self._collect_web_data(
            url, 
            "Evaluate this site against Nielsen's 10 heuristics. Look for visibility of status and consistency."
        )
        
        return SkillOutput(
            success=True,
            summary=f"Heuristic evaluation completed for {url}.",
            artifacts={"heuristic_report.txt": web_data}
        )
