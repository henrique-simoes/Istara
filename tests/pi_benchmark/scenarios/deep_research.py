"""Deep research pack (CF-SPEC-11, axes 4, 7, 8, 10): Istara-faithful workloads.

Real Istara content, not smoke prompts:

* ``deep.dag.*`` — the tests/evals dag_react live cases (plan decomposition, tool
  choice), with the evals' own deterministic checks reused verbatim (axis 4
  plan/tool_selection, axis 7).
* ``deep.corpus.*`` — grounding/contradiction tasks over the canonical CareNav
  document corpus, honoring its guardrails (preserve source context, cite spans,
  no PHI leakage, contradictions to reconciliation) — the research spine's
  grounding/synthesis/review phases (axis 4; judge-scored in pass 2).
* ``deep.skills.contract`` — skill-contract compliance with marker checks (axis 8;
  deterministic).
* ``deep.a2a.debate`` — evidence-citing debate brief designed for the self_moa lane,
  where rounds/consensus/reconciliation are measured by the MoA evidence layer
  (axis 10; MoA metrics + judge).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .base import Scenario

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CASES_PATH = _REPO_ROOT / "tests" / "evals" / "cases" / "core_eval_cases.json"
_CORPUS_BRIEF = (
    _REPO_ROOT
    / "tests"
    / "document_corpus"
    / "canonical"
    / "sources"
    / "brief"
    / "CR-144-brief-01.md"
)

PACK = "deep_research"


@lru_cache(maxsize=1)
def _cases() -> dict[str, dict]:
    data = json.loads(_CASES_PATH.read_text(encoding="utf-8"))
    return {case["id"]: case for case in data.get("live_cases", [])}


def _case_prompt(case: dict) -> str:
    return "\n\n".join(
        f"[{m['role']}] {m['content']}" for m in case.get("messages", [])
    )


def _corpus_excerpt(max_chars: int = 6000) -> str:
    text = _CORPUS_BRIEF.read_text(encoding="utf-8") if _CORPUS_BRIEF.is_file() else ""
    return text[:max_chars]


def scenarios() -> tuple[Scenario, ...]:
    built: list[Scenario] = []

    plan = _cases().get("dag_react_json_plan")
    if plan:
        built.append(
            Scenario(
                id="deep.dag.plan_json",
                title="DAG research plan decomposition (evals dag_react)",
                pack=PACK,
                min_tier="T3",
                prompt=_case_prompt(plan),
                expected={
                    "evals_checks": plan.get("checks", {}),
                    "spine_phases": ["plan"],
                },
                tags=("deep", "dag", "plan"),
            )
        )
    tool = _cases().get("tool_choice_memory_search")
    if tool:
        built.append(
            Scenario(
                id="deep.dag.tool_choice",
                title="Tool selection for memory search (evals dag_react)",
                pack=PACK,
                min_tier="T3",
                prompt=_case_prompt(tool),
                expected={
                    "evals_checks": tool.get("checks", {}),
                    "spine_phases": ["tool_selection"],
                },
                tags=("deep", "dag", "tool_choice"),
            )
        )

    excerpt = _corpus_excerpt()
    if excerpt:
        built.append(
            Scenario(
                id="deep.corpus.grounding",
                title="Evidence-unit extraction with source citations (CareNav corpus)",
                pack=PACK,
                min_tier="T3",
                prompt=(
                    "You are Istara's research spine grounding step. From the source below, "
                    "extract exactly 3 stable evidence units. For each: the claim, the exact "
                    "source span it traces to (quote), and one method limit. Follow the "
                    "source guardrails (no medical advice, no PHI details). Output compact "
                    'JSON: {"units": [{"claim": str, "span": str, "limit": str}]}.\n\n'
                    f"SOURCE:\n{excerpt}"
                ),
                expected={
                    "rubric": "grounding",
                    "spine_phases": ["grounding", "synthesis"],
                    "guardrails": ["no_medical_advice", "no_phi"],
                },
                tags=("deep", "corpus", "grounding"),
            )
        )
        built.append(
            Scenario(
                id="deep.corpus.review_gate",
                title="Report-readiness gate under guardrails (review phase)",
                pack=PACK,
                min_tier="T3",
                prompt=(
                    "You are Istara's research spine review gate. Given the source below, "
                    "decide whether ANY finding is report-ready now. Answer compact JSON: "
                    '{"report_ready": bool, "blocking_reasons": [str], '
                    '"next_step": str}. Report-ready requires: every claim traceable to a '
                    "span, contradictions reconciled, and guardrails honored.\n\n"
                    f"SOURCE:\n{excerpt}"
                ),
                expected={"rubric": "review", "spine_phases": ["review", "governance"]},
                tags=("deep", "corpus", "review"),
            )
        )

    built.append(
        Scenario(
            id="deep.skills.contract",
            title="Skill-contract compliance with markers",
            pack=PACK,
            min_tier="T3",
            prompt=(
                "You are Istara's skill executor. The `thematic-analysis` skill contract "
                "requires: (1) output begins with the marker `[SKILL:thematic-analysis]`, "
                "(2) sections in order `codes`, `themes`, `evidence_map`, (3) every theme "
                "lists at least one supporting code. Produce a compliant mini-analysis of "
                'this feedback: "the app crashes on export; export is vital; tutorials '
                'helped; crashes make me distrust the tool."'
            ),
            expected={
                "markers": ["[SKILL:thematic-analysis]"],
                "sections": ["codes", "themes", "evidence_map"],
                "spine_phases": ["execution"],
            },
            tags=("deep", "skills", "contract"),
        )
    )

    built.append(
        Scenario(
            id="deep.a2a.debate",
            title="Evidence-citing debate brief (A2A collaboration)",
            pack=PACK,
            min_tier="T3",
            prompt=(
                'Two research agents disagree. Agent A claims: "Remote moderation '
                'increases task-completion rates." Agent B claims: "Remote moderation '
                'lowers data richness." As the synthesis agent, write a balanced brief '
                "that (1) states each position with its strongest evidence type, "
                "(2) identifies what data would settle the disagreement, and (3) gives a "
                "recommendation with explicit confidence. Under 200 words."
            ),
            expected={"rubric": "a2a", "spine_phases": ["synthesis", "review"]},
            tags=("deep", "a2a", "debate"),
        )
    )
    return tuple(built)
