"""Tests for browser UX research skills — loading, validation, URL flow."""

import json
import pytest
from pathlib import Path


SKILLS_DIR = Path(__file__).parent.parent / "backend" / "app" / "skills" / "definitions"


BROWSER_SKILLS = [
    "browser-ux-audit",
    "browser-competitive-benchmark",
    "browser-accessibility-check",
]


def test_browser_skill_definitions_exist():
    for name in BROWSER_SKILLS:
        path = SKILLS_DIR / f"{name}.json"
        assert path.exists(), f"Skill definition not found: {path}"


def test_browser_skill_definitions_are_valid_json():
    for name in BROWSER_SKILLS:
        path = SKILLS_DIR / f"{name}.json"
        with open(path) as f:
            data = json.load(f)
        assert data["name"] == name
        assert data["enabled"] is True
        assert data["display_name"]
        assert data["description"]
        assert data["phase"] in ("discover", "define", "develop", "deliver")
        assert data["skill_type"] in ("qualitative", "quantitative", "mixed")
        assert "plan_prompt" in data
        assert "execute_prompt" in data
        assert "output_schema" in data


def test_browser_skill_plan_prompts_reference_urls():
    for name in BROWSER_SKILLS:
        path = SKILLS_DIR / f"{name}.json"
        with open(path) as f:
            data = json.load(f)
        assert "{urls}" in data["plan_prompt"], (
            f"{name} plan_prompt missing {{urls}} placeholder"
        )


def test_browser_skill_execute_prompts_reference_urls_section():
    for name in BROWSER_SKILLS:
        path = SKILLS_DIR / f"{name}.json"
        with open(path) as f:
            data = json.load(f)
        assert (
            "{urls_section}" in data["execute_prompt"]
            or "{urls}" in data["execute_prompt"]
        ), f"{name} execute_prompt missing {{urls_section}} or {{urls}} placeholder"


def test_browser_skill_output_schemas_are_valid_json():
    for name in BROWSER_SKILLS:
        path = SKILLS_DIR / f"{name}.json"
        with open(path) as f:
            data = json.load(f)
        assert "summary" in data["output_schema"], (
            f"{name} output_schema missing 'summary' field"
        )
        assert "nuggets" in data["output_schema"], (
            f"{name} output_schema missing 'nuggets' field"
        )
        assert "recommendations" in data["output_schema"], (
            f"{name} output_schema missing 'recommendations' field"
        )


def test_browser_ux_audit_has_heuristics_and_accessibility():
    path = SKILLS_DIR / "browser-ux-audit.json"
    with open(path) as f:
        data = json.load(f)
    execute = data["execute_prompt"]
    assert "H1" in execute or "Visibility of system status" in execute
    assert "WCAG" in execute or "accessibility" in execute.lower()
    assert "severity" in execute.lower()


def test_browser_competitive_benchmark_has_feature_matrix():
    path = SKILLS_DIR / "browser-competitive-benchmark.json"
    with open(path) as f:
        data = json.load(f)
    schema = data["output_schema"]
    assert "feature_matrix" in schema or "competitors" in schema


def test_browser_accessibility_check_has_wcag_criteria():
    path = SKILLS_DIR / "browser-accessibility-check.json"
    with open(path) as f:
        data = json.load(f)
    execute = data["execute_prompt"]
    assert (
        "1.1.1" in execute or "Non-text Content" in execute or "Perceivable" in execute
    )
    assert "severity" in execute.lower() or "Critical" in execute


def test_skill_input_has_urls_field():
    from app.skills.base import SkillInput

    inp = SkillInput(project_id="test", urls=["https://example.com"])
    assert inp.urls == ["https://example.com"]


def test_skill_input_urls_default_empty():
    from app.skills.base import SkillInput

    inp = SkillInput(project_id="test")
    assert inp.urls == []


def test_scope_map_includes_browser_skills():
    from app.core.report_manager import SCOPE_MAP

    assert "browser-ux-audit" in SCOPE_MAP
    assert SCOPE_MAP["browser-ux-audit"] == "Usability Study"
    assert "browser-accessibility-check" in SCOPE_MAP
    assert SCOPE_MAP["browser-accessibility-check"] == "Usability Study"
    assert "browser-competitive-benchmark" in SCOPE_MAP
    assert SCOPE_MAP["browser-competitive-benchmark"] == "Competitive Analysis"


def test_task_router_detects_browser_skills():
    from app.core.task_router import detect_task_specialties

    specialties = detect_task_specialties(
        "UX audit of live site", "Evaluate website using browser automation"
    )
    assert "ui" in specialties or "research" in specialties


def test_skill_factory_urls_template():
    from app.skills.skill_factory import create_skill
    from app.skills.base import SkillPhase, SkillType

    SkillCls = create_skill(
        skill_name="test-browser-skill",
        display="Test Browser Skill",
        desc="Test skill with URLs",
        phase=SkillPhase.DEVELOP,
        skill_type=SkillType.MIXED,
        plan_prompt="Plan audit for {urls}. Context: {context}. User: {user_context}.",
        execute_prompt="Context: {context}\nContent: {content}\nURLs: {urls}\n{urls_section}",
        output_schema='{"summary": "string"}',
    )
    skill = SkillCls()
    assert skill.name == "test-browser-skill"
