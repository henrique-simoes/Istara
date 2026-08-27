"""Validate Istara's agentic evaluation contract manifest."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "agentic_eval_contract.json"

REQUIRED_CONTRACTS = {
    "autoresearch",
    "reasoning_bank",
    "memento_skills_and_agent_creation",
    "hyperagent_meta_tuning",
    "dgmh_archive_evolution",
    "ensemble_llm_orchestration",
    "tool_calling_react",
    "acceptance_ui_simulation",
}


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.mark.contract
@pytest.mark.agentic_eval
def test_agentic_eval_manifest_declares_all_system_contracts():
    manifest = load_manifest()
    ids = {contract["id"] for contract in manifest["contracts"]}
    assert REQUIRED_CONTRACTS <= ids
    assert manifest["schema_version"] == 1


@pytest.mark.contract
@pytest.mark.agentic_eval
def test_agentic_eval_contract_evidence_files_exist():
    manifest = load_manifest()
    for contract in manifest["contracts"]:
        evidence_paths = (
            contract.get("unit_tests", [])
            + contract.get("integration_tests", [])
            + contract.get("simulation_scenarios", [])
        )
        assert evidence_paths, f"{contract['id']} has no evidence paths"
        for relative_path in evidence_paths:
            assert (ROOT / relative_path).exists(), (
                f"{contract['id']} missing {relative_path}"
            )


@pytest.mark.contract
@pytest.mark.agentic_eval
def test_agentic_eval_simulation_scenarios_are_loaded_by_runner():
    manifest = load_manifest()
    runner = (ROOT / "tests" / "simulation" / "run.mjs").read_text(encoding="utf-8")
    registry = (ROOT / "tests" / "simulation" / "lib" / "scenario-registry.mjs").read_text(encoding="utf-8")
    match = re.search(r"export const scenarioFiles = Object\.freeze\(\[(?P<body>.*?)\]\);", registry, re.S)
    assert match, "scenario registry must export scenarioFiles"
    loaded_scenarios = set(re.findall(r'"([^"]+)"', match.group("body")))
    assert "./lib/scenario-registry.mjs" in runner
    for contract in manifest["contracts"]:
        for relative_path in contract.get("simulation_scenarios", []):
            scenario_name = Path(relative_path).stem
            assert scenario_name in loaded_scenarios, (
                f"{contract['id']} scenario {scenario_name} is not loaded by run.mjs"
            )


@pytest.mark.contract
@pytest.mark.agentic_eval
def test_agentic_eval_metrics_are_quantifiable():
    manifest = load_manifest()
    for contract in manifest["contracts"]:
        metrics = contract.get("eval_metrics", [])
        assert len(metrics) >= 3, (
            f"{contract['id']} needs at least three tracked metrics"
        )
        assert all(metric == metric.lower() for metric in metrics)
        assert all(" " not in metric for metric in metrics)


@pytest.mark.contract
@pytest.mark.agentic_eval
def test_live_orchestration_baselines_are_companion_only():
    """The historical live benchmark must not masquerade as PI acceptance evidence."""
    manifest = load_manifest()
    contracts = {
        contract["id"]: contract for contract in manifest["contracts"]
    }
    for contract_id in ("ensemble_llm_orchestration", "tool_calling_react"):
        contract = contracts[contract_id]
        assert contract["evidence_role"] == "companion"
        acceptance_tests = contract["acceptance_tests"]
        assert "tests/pi_benchmark/live_driver.py" in acceptance_tests
        assert "tests/real_user_benchmark/run.mjs" in acceptance_tests
        assert contract["does_not_claim"]
