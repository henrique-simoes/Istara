"""Canonical pack — the 15 production-contract scenarios (task B0-5).

The canonical pack re-hosts, at benchmark level, the exact 15 scenario ids that
``tests/pi_production/test_scenario_coverage_map.py`` maps to real production tests. We
read that mapping by an **AST literal read** of the source file (never an import), so the
pack stays import-safe at T0 and cannot drag in backend dependencies.

The deterministic contract check for each scenario is offline and meaningful: it asserts
the scenario id still resolves to a production test module that exists and defines the
mapped test function (winning plan §2.2 principle 4). This is the T0/T1 smoke gate that
the B0 assets and the production coverage contract agree, before any owner-gated spend.
"""

from __future__ import annotations

import ast
import re
from functools import lru_cache
from pathlib import Path

from .base import Scenario, deterministic_check_result

# tests/pi_benchmark/scenarios/canonical.py -> parents[3] is the repository root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_COVERAGE_SRC = _REPO_ROOT / "tests" / "pi_production" / "test_scenario_coverage_map.py"
_CATALOG_SRC = _REPO_ROOT / "labs" / "pi-replacement" / "src" / "scenario-catalog.mjs"
_PRODUCTION_PKG = _REPO_ROOT / "tests" / "pi_production"


@lru_cache(maxsize=1)
def _coverage_map() -> dict[str, tuple[str, str]]:
    """Read the ``COVERAGE`` literal from the production coverage test without importing it.

    ``ast.literal_eval`` evaluates only the literal, so no production/backend module is
    executed. Raises if the assignment is missing — a hard failure, since the whole
    canonical pack is defined by this contract.
    """
    tree = ast.parse(_COVERAGE_SRC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        target_ids: list[str] = []
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_ids = [node.target.id]
            value = node.value
        elif isinstance(node, ast.Assign):
            target_ids = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        else:
            continue
        if "COVERAGE" in target_ids and value is not None:
            return dict(ast.literal_eval(value))
    raise RuntimeError(f"COVERAGE mapping not found in {_COVERAGE_SRC}")


@lru_cache(maxsize=1)
def _catalog_ids() -> tuple[str, ...]:
    """The canonical lab scenario ids, read from the catalog the same way the map does."""
    text = _CATALOG_SRC.read_text(encoding="utf-8")
    return tuple(re.findall(r"^    id\s*:\s*['\"]([^'\"]+)['\"]", text, re.MULTILINE))


def _production_test_exists(module_name: str, func_name: str) -> bool:
    """True iff ``tests/pi_production/<module_name>.py`` defines ``def <func_name>``.

    An offline AST scan — never an import — so the check is T0-safe and cannot fail for
    reasons unrelated to the contract (e.g. a backend import error in the module).
    """
    path = _PRODUCTION_PKG / f"{module_name}.py"
    if not path.is_file():
        return False
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    return any(
        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == func_name
        for n in ast.walk(tree)
    )


def _make_check(scenario_id: str, module_name: str, func_name: str):
    def check(engine: str, seed: int):
        resolves = _production_test_exists(module_name, func_name)
        return deterministic_check_result(
            passed=resolves,
            outcome_class="resolves" if resolves else "unresolved",
            production_test=f"{module_name}.{func_name}",
        )

    return check


@lru_cache(maxsize=1)
def scenarios() -> tuple[Scenario, ...]:
    """Build the 15 canonical scenarios from the production coverage contract.

    Guards the invariant the production suite also asserts: the coverage map keys are
    exactly the catalog ids. If they ever diverge this raises here, so the benchmark can
    never silently run a stale or partial canonical set.
    """
    coverage = _coverage_map()
    catalog = set(_catalog_ids())
    if set(coverage) != catalog:
        missing = catalog - set(coverage)
        extra = set(coverage) - catalog
        raise RuntimeError(
            f"canonical pack drift: catalog vs coverage differ (missing={sorted(missing)}, "
            f"extra={sorted(extra)})"
        )
    built: list[Scenario] = []
    for scenario_id in sorted(coverage):
        module_name, func_name = coverage[scenario_id]
        built.append(
            Scenario(
                id=scenario_id,
                title=scenario_id.replace(".", " ").replace("_", " ").title(),
                pack="canonical",
                min_tier="T0",
                contract_check=_make_check(scenario_id, module_name, func_name),
                tags=("production-contract",),
            )
        )
    return tuple(built)
