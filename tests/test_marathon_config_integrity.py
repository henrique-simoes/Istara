"""Static integrity checks for the marathon/simulation contract."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def marathon_config() -> dict:
    return json.loads(read("scripts/marathon/config.json"))


def simulation_runner_scenarios() -> set[str]:
    runner = read("tests/simulation/lib/scenario-registry.mjs")
    match = re.search(r"export const scenarioFiles = Object\.freeze\(\[(?P<body>.*?)\]\);", runner, re.S)
    assert match, "tests/simulation/lib/scenario-registry.mjs must define scenarioFiles"
    assert "scenarioFiles" in read("tests/simulation/run.mjs")
    return set(re.findall(r'"([^"]+)"', match.group("body")))


def custom_check_names() -> set[str]:
    source = read("scripts/marathon/custom-checks.mjs")
    match = re.search(r"export const CUSTOM_CHECKS = Object\.freeze\(\{(?P<body>.*?)\n\}\);", source, re.S)
    assert match, "scripts/marathon/custom-checks.mjs must export CUSTOM_CHECKS"
    return set(re.findall(r"^\s{2}([a-zA-Z0-9_]+):", match.group("body"), re.M))


def documented_cycle_requirements() -> set[str]:
    source = read("scripts/marathon/custom-checks.mjs")
    match = re.search(
        r"export const DOCUMENTED_CYCLE_REQUIREMENTS = Object\.freeze\(\[(?P<body>.*?)\]\);",
        source,
        re.S,
    )
    assert match, "scripts/marathon/custom-checks.mjs must document cycle requirements"
    return set(re.findall(r'"([^"]+)"', match.group("body")))


def test_marathon_scenario_refs_resolve_to_registered_simulation_scenarios() -> None:
    scenario_files = simulation_runner_scenarios()
    scenario_stems = {path.stem for path in (ROOT / "tests/simulation/scenarios").glob("*.mjs")}
    config = marathon_config()

    unresolved: list[str] = []
    unregistered: list[str] = []
    for cycle in config["cycles"]:
        for ref in cycle.get("scenarios", []):
            matches = {stem for stem in scenario_stems if stem == ref or stem.startswith(f"{ref}-")}
            registered_matches = {stem for stem in scenario_files if stem == ref or stem.startswith(f"{ref}-")}
            if not matches:
                unresolved.append(f"{cycle['id']}:{ref}")
            if not registered_matches:
                unregistered.append(f"{cycle['id']}:{ref}")

    assert unresolved == []
    assert unregistered == []


def test_marathon_custom_checks_resolve_to_registered_implementations() -> None:
    config_checks = {
        check
        for cycle in marathon_config()["cycles"]
        for check in cycle.get("custom_checks", [])
    }
    implemented_checks = custom_check_names()

    assert config_checks - implemented_checks == set()
    assert implemented_checks - config_checks == set()
    assert "Placeholder" not in read("scripts/marathon/run-cycle.mjs")
    assert "Placeholder" not in read("scripts/marathon/custom-checks.mjs")


def test_marathon_cycle_requirements_are_documented_and_bounded() -> None:
    config = marathon_config()
    documented = documented_cycle_requirements()
    used = {
        requirement
        for cycle in config["cycles"]
        for requirement in cycle.get("requires", [])
    }

    assert used - documented == set()
    assert config["settings"]["cycle_interval_minutes"] >= 1
    assert config["settings"]["max_scenario_timeout_seconds"] <= 7200
    assert config["settings"]["log_dir"] == "data/test-marathon"
