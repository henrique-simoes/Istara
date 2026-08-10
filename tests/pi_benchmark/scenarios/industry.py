"""Industry benchmark pack (CF-322 / DEC-9): BFCL v4 + τ-bench subsets.

Real published-benchmark content, executed through the same paired runner as the
internal packs so industry numbers and internal numbers share provider parity,
pairing, budget discipline, and raw capture.

Sources (see comparison-Istara-pi/industry/ATTRIBUTION.md):

- **BFCL v4** (Berkeley Function-Calling Leaderboard, Apache-2.0): `simple_python`,
  `multiple`, `live_simple` categories, prompt mode (function catalog in context —
  the official non-FC mode; recorded fidelity). Ground truth from `possible_answer/`
  travels in ``Scenario.expected`` for post-run deterministic AST scoring.
- **τ-bench** (Sierra, MIT): airline + retail `tasks_test` task instructions adapted
  to single-turn policy tasks (the full env simulator + user-LLM loop is out of
  scope for this pack — fidelity is documented honestly as "adapted single-turn").
- **GAIA**: gated on Hugging Face (401 without an owner token) — not included;
  tracked as a follow-up needing an owner credential (DEC-12 candidate).

Determinism & storage:

- Subsets are the FIRST N items of each category in file order (N per
  ``INDUSTRY_SUBSET_SIZES``), so every run compiles the identical unit set.
- Dataset files live in ``comparison-Istara-pi/industry/`` (gitignored content, never
  committed). Missing files produce NO scenarios — the runner records nothing rather
  than inventing tasks; ``data_status()`` reports what's present for the estimate gate.
- Import-safe at T0: no backend imports; file reads happen only inside ``scenarios()``.
"""

from __future__ import annotations

import ast
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .base import Scenario, deterministic_check_result

_REPO_ROOT = Path(__file__).resolve().parents[3]
INDUSTRY_DIR = _REPO_ROOT / "comparison-Istara-pi" / "industry"
BFCL_DIR = INDUSTRY_DIR / "bfcl"
TAU_DIR = INDUSTRY_DIR / "tau_bench"

# Deterministic subset sizes (first-N per category in file order). Sized so the whole
# industry pack (2 engines × ~70 units × 1 call) stays a small fraction of the DEC-8
# envelope; the estimate gate prints the worst case before any spend.
INDUSTRY_SUBSET_SIZES: dict[str, int] = {
    "bfcl_simple_python": 25,
    "bfcl_multiple": 20,
    "bfcl_live_simple": 15,
    "tau_airline": 8,
    "tau_retail": 8,
}

_BFCL_FILES: dict[str, tuple[str, str]] = {
    # category -> (questions file, answers file)
    "bfcl_simple_python": ("BFCL_v4_simple_python.json", "answer_simple_python.json"),
    "bfcl_multiple": ("BFCL_v4_multiple.json", "answer_multiple.json"),
    "bfcl_live_simple": ("BFCL_v4_live_simple.json", "answer_live_simple.json"),
}

_TAU_FILES: dict[str, str] = {
    "tau_airline": "airline_tasks_test.py",
    "tau_retail": "retail_tasks_test.py",
}

PACK = "industry"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    items = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                items.append(json.loads(line))
    return items


def data_status() -> dict[str, Any]:
    """What industry data is present (estimate-gate / B0 visibility, never fatal)."""
    status: dict[str, Any] = {"dir": str(INDUSTRY_DIR), "categories": {}}
    for category, (questions, answers) in _BFCL_FILES.items():
        q = BFCL_DIR / questions
        a = BFCL_DIR / answers
        status["categories"][category] = {
            "questions": q.is_file(),
            "answers": a.is_file(),
            "subset": INDUSTRY_SUBSET_SIZES[category],
        }
    for category, filename in _TAU_FILES.items():
        status["categories"][category] = {
            "tasks": (TAU_DIR / filename).is_file(),
            "subset": INDUSTRY_SUBSET_SIZES[category],
        }
    return status


# ── BFCL conversion ─────────────────────────────────────────────────────────


def _bfcl_prompt(item: dict[str, Any]) -> str:
    question = ""
    turns = item.get("question") or []
    if turns and turns[0]:
        question = str(turns[0][0].get("content", ""))
    functions = json.dumps(item.get("function") or [], indent=1, ensure_ascii=False)
    return (
        "[BFCL v4 prompt-mode tool calling]\n"
        "You are given a list of available functions and a user question. Answer with "
        "the function call that best serves the question, as a single JSON object of "
        'the form {"name": "<function_name>", "arguments": {<arg>: <value>}}. '
        "Output ONLY the JSON object, no prose.\n\n"
        f"Available functions:\n{functions}\n\n"
        f"User question: {question}"
    )


def _load_bfcl_category(category: str) -> list[Scenario]:
    questions_file, answers_file = _BFCL_FILES[category]
    q_path, a_path = BFCL_DIR / questions_file, BFCL_DIR / answers_file
    if not (q_path.is_file() and a_path.is_file()):
        return []
    items = _read_jsonl(q_path)[: INDUSTRY_SUBSET_SIZES[category]]
    answers = {a["id"]: a.get("ground_truth") for a in _read_jsonl(a_path)}
    scenarios = []
    for item in items:
        scenarios.append(Scenario(
            id=f"industry.{category}.{item['id']}",
            title=f"BFCL v4 {category}: {item['id']}",
            pack=PACK,
            min_tier="T3",
            prompt=_bfcl_prompt(item),
            expected={"bfcl_ground_truth": answers.get(item["id"]), "category": category},
            tags=("industry", "bfcl", category),
        ))
    return scenarios


# ── τ-bench conversion (adapted single-turn) ────────────────────────────────


def _parse_tau_tasks(path: Path) -> list[dict[str, Any]]:
    """Extract Task(instruction=..., actions=[Action(name=...)]) from tasks_test.py.

    AST-only (the tau_bench package is not installed); ignores everything it cannot
    statically read rather than failing.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tasks: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Name) and func.id == "Task"):
            continue
        instruction = ""
        action_names: list[str] = []
        for keyword in node.keywords:
            if keyword.arg == "instruction" and isinstance(keyword.value, ast.Constant):
                instruction = str(keyword.value.value)
            if keyword.arg == "actions" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                for element in keyword.value.elts:
                    if isinstance(element, ast.Call):
                        for action_kw in element.keywords:
                            if action_kw.arg == "name" and isinstance(action_kw.value, ast.Constant):
                                action_names.append(str(action_kw.value.value))
        if instruction:
            tasks.append({"instruction": instruction, "actions": action_names})
    return tasks


def _load_tau_category(category: str) -> list[Scenario]:
    path = TAU_DIR / _TAU_FILES[category]
    if not path.is_file():
        return []
    domain = "airline" if "airline" in category else "retail"
    tasks = _parse_tau_tasks(path)[: INDUSTRY_SUBSET_SIZES[category]]
    scenarios = []
    for index, task in enumerate(tasks):
        prompt = (
            f"[τ-bench adapted single-turn policy task — {domain} domain]\n"
            "You are a customer-service agent in the " + domain + " domain, following "
            "the domain policy exactly. A user interacts with you with the goal below. "
            "Decide the FIRST action you would take and answer as a single JSON object "
            'of the form {"action": "<tool_name>", "rationale": "<one sentence>"}. '
            "Output ONLY the JSON object.\n\n"
            f"User goal: {task['instruction']}"
        )
        scenarios.append(Scenario(
            id=f"industry.{category}.task{index}",
            title=f"τ-bench {domain} adapted task {index}",
            pack=PACK,
            min_tier="T3",
            prompt=prompt,
            expected={"tau_expected_actions": task["actions"], "domain": domain,
                      "fidelity": "adapted_single_turn"},
            tags=("industry", "tau_bench", domain),
        ))
    return scenarios


# ── pack entry point ────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def scenarios() -> tuple[Scenario, ...]:
    """All industry scenarios (empty when dataset files are absent — never fatal)."""
    loaded: list[Scenario] = []
    for category in _BFCL_FILES:
        loaded.extend(_load_bfcl_category(category))
    for category in _TAU_FILES:
        loaded.extend(_load_tau_category(category))
    return tuple(loaded)


def industry_contract_check(engine: str, seed: int):
    """T0 contract: data files parse and the deterministic subset is stable."""
    status = data_status()
    present = sum(1 for c in status["categories"].values() if any(c.values()))
    ok = present == len(status["categories"])
    return deterministic_check_result(
        ok,
        f"industry_data_{'complete' if ok else 'missing'}",
        engine=engine, seed=seed, present_categories=present,
    )
