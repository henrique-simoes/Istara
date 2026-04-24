"""Regression tests for canonical JSON skill definitions."""

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_skills.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_skills", VALIDATOR_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_skill_definitions_have_valid_json_and_output_schemas():
    validator = _load_validator()
    result = validator.validate_skill_definitions()
    assert result.ok, "\n".join(result.failures)
    assert result.checked > 0
