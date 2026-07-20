"""Production scenario 14 (benchmarks.evals.real_user.contract) — the auditable
coverage contract.

Plan C §4 requires every one of the 15 canonical lab scenario ids to resolve to
a real ``tests/pi_production`` result (never the lab facade or a telemetry-only
hook). This meta-scenario is that contract: it maps each canonical id to the
concrete production test function that proves it and asserts the function exists
in this package. If a scenario is ever dropped or silently downgraded to a lab
proof, this test fails.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

# canonical lab scenario id -> (module in tests/pi_production, test function)
COVERAGE: dict[str, tuple[str, str]] = {
    "chat.tool_loop.task_and_finding": (
        "test_worker_tool_loop", "test_pi_worker_owns_tool_loop_and_persists_task"),
    "task.plan_execute.lifecycle": (
        "test_scenario_task_lifecycle", "test_scenario2_multi_turn_session_persists_plan_then_execute"),
    "documents.tools.slice": (
        "test_scenario_task_lifecycle", "test_scenario3_canonical_tools_enforce_project_scope_cross_project_denied"),
    "structured_outputs.core_eval": (
        "test_scenario_structured_output", "test_scenario4_openai_compat_structured_output_valid_and_invalid"),
    "memory.rag.slice": (
        "test_scenario_memory", "test_scenario5_search_memory_and_reasoning_store_are_project_scoped"),
    "skills.three_skill_slice": (
        "test_scenario_skills", "test_scenario6_three_skills_run_in_order_with_protected_blocks_intact"),
    "a2a.debate_report.slice": (
        "test_scenario_delegation", "test_scenario7_pi_delegation_runs_through_orchestrator_dispatch"),
    "channel.lifecycle.simulated_slice": (
        "test_scenario_channel", "test_scenario8_pi_local_channel_reply_is_real_loop_and_persists"),
    "research.spine.step_tracker": (
        "test_scenario_research_spine", "test_scenario9_provisional_evidence_stays_candidate_and_cannot_be_reported_or_done"),
    "autoresearch.governed_experiment.slice": (
        "test_scenario_autoresearch", "test_scenario10_governed_autoresearch_candidate_only_no_loop"),
    "memory.reasoningbank.memento.slice": (
        "test_scenario_reasoning_memory", "test_scenario11_reasoningbank_memento_and_skillstats_are_governed_and_scoped"),
    "channels.webhook.telegram.lifecycle": (
        "test_scenario_webhook", "test_scenario12_telegram_inbound_uses_real_loop_with_zero_external_traffic"),
    "steering.system_prompt.loop.slice": (
        "test_scenario_steering", "test_scenario13_queued_steer_delivered_once_mid_turn"),
    "benchmarks.evals.real_user.contract": (
        "test_scenario_coverage_map", "test_scenario14_every_canonical_scenario_resolves_to_a_production_test"),
    "model.routing.telemetry.slice": (
        "test_same_model_donor_isolation", "test_same_model_pi_endpoint_and_donor_prove_bidirectional_isolation"),
}


def _catalog_ids() -> set[str]:
    """Read the canonical lab catalog rather than maintaining a second id list."""
    catalog = Path(__file__).resolve().parents[2] / "labs/pi-replacement/src/scenario-catalog.mjs"
    return set(re.findall(r"^    id\s*:\s*['\"]([^'\"]+)['\"]", catalog.read_text(), re.MULTILINE))


def test_scenario14_every_canonical_scenario_resolves_to_a_production_test():
    # The full catalog is covered — no gaps, no lab-facade fallback.
    assert set(COVERAGE) == _catalog_ids()

    missing: list[str] = []
    for scenario_id, (module_name, func_name) in COVERAGE.items():
        # Every mapped module lives in this production package — never labs/.
        module = importlib.import_module(f".{module_name}", __package__)
        assert __package__.endswith("pi_production")
        if not hasattr(module, func_name):
            missing.append(f"{scenario_id} -> {module_name}.{func_name}")

    assert not missing, "canonical scenarios without a production test: " + "; ".join(missing)

    # Every scenario id is distinct and maps to a distinct production function.
    targets = {f"{m}.{fn}" for (m, fn) in COVERAGE.values()}
    assert len(targets) == 15
