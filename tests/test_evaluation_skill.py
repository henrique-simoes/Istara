"""Tests for research quality evaluation skill and validation metrics API."""

import json
import pytest
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "backend" / "app" / "skills" / "definitions"


def test_evaluation_skill_definition_exists():
    path = SKILLS_DIR / "research-quality-evaluation.json"
    assert path.exists(), f"Skill definition not found: {path}"


def test_evaluation_skill_definition_is_valid_json():
    path = SKILLS_DIR / "research-quality-evaluation.json"
    with open(path) as f:
        data = json.load(f)
    assert data["name"] == "research-quality-evaluation"
    assert data["phase"] == "deliver"
    assert data["skill_type"] == "mixed"
    assert data["enabled"] is True
    assert "plan_prompt" in data
    assert "execute_prompt" in data
    assert "output_schema" in data


def test_evaluation_skill_has_validation_dimensions():
    path = SKILLS_DIR / "research-quality-evaluation.json"
    with open(path) as f:
        data = json.load(f)
    execute = data["execute_prompt"]
    assert "adversarial" in execute.lower()
    assert "dual" in execute.lower()
    assert "self_moa" in execute.lower().replace("-", "_") or "Self-MoA" in execute
    assert "consensus" in execute.lower()
    assert "kappa" in execute.lower() or "0.70" in execute


def test_evaluation_skill_has_chain_integrity():
    path = SKILLS_DIR / "research-quality-evaluation.json"
    with open(path) as f:
        data = json.load(f)
    execute = data["execute_prompt"]
    assert "chain" in execute.lower()
    assert "nugget" in execute.lower()
    assert "fact" in execute.lower()
    assert "insight" in execute.lower()
    assert "recommendation" in execute.lower()


def test_evaluation_skill_scope_map_entry():
    from app.core.report_manager import SCOPE_MAP

    assert "research-quality-evaluation" in SCOPE_MAP
    assert SCOPE_MAP["research-quality-evaluation"] == "Quality Evaluation"


def test_metrics_routes_import():
    from app.api.routes.metrics import router

    routes = [r.path for r in router.routes]
    assert any("validation" in r for r in routes), (
        f"Validation route not found in {routes}"
    )


def test_task_type_has_validation_fields():
    from app.models.task import Task

    assert hasattr(Task, "validation_method"), "Task model missing validation_method"
    assert hasattr(Task, "consensus_score"), "Task model missing consensus_score"
