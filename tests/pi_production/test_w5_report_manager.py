"""W5 contract coverage — report_manager migration (master plan §8 W5).

The six LLM call sites in ``report_manager.py``
(``_generate_executive_summary``, ``_generate_mece_categories``,
``_compose_full_report`` weakest-section scoring, and the three
``_compose_section`` narrative sites) route through the AgenticDispatcher —
``completion`` → ``report.exec_summary`` / ``report.insights_narrative`` /
``report.recommendations_narrative`` / ``report.gaps_analysis``,
``structured`` → ``report.mece`` / ``report.weakest_section``. The W9
ratchet retired the ``agentic_core`` feature-flag gate and the legacy
``llm_router.chat`` fallthrough branches: the dispatcher is the only path.

Covered here (all stubbed/static — no live model activity):

* static: each migrated function carries the dispatcher path (right verb,
  right purpose slug) and no legacy branch remains;
* behavior: the dispatcher stub records the call (right verb, purpose,
  project scope) and the legacy plane is never called; downstream behavior
  (report writes, convergence break, fallback sentinels) is unchanged.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

# Importing ``app.core.agentic`` transitively imports ``app.core.ollama``,
# whose module import registers the local server on the real ``llm_router``.
# That must happen before any test stubs ``app.core.llm_router.llm_router``.
import app.core.agentic  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_MANAGER = REPO_ROOT / "backend/app/core/report_manager.py"

SPINE_PHASES = {
    "intent", "context", "plan", "tool_selection", "execution",
    "recovery", "grounding", "synthesis", "review", "governance",
}


# ── helpers ─────────────────────────────────────────────────────────────


def _function_source(function_name: str) -> str:
    text = REPORT_MANAGER.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(f"{function_name} not found in {REPORT_MANAGER}")


class _StubAgentic:
    """Recording stand-in for the ``agentic`` dispatcher singleton."""

    def __init__(self, *, text: str = "dispatcher text", value=None, status: str = "success") -> None:
        self.calls: list[tuple[str, dict]] = []
        self._text = text
        self._value = value
        self._status = status

    async def completion(self, **kwargs):
        self.calls.append(("completion", kwargs))
        return SimpleNamespace(text=self._text, status=self._status, usage={})

    async def structured(self, **kwargs):
        self.calls.append(("structured", kwargs))
        return SimpleNamespace(value=self._value, text=self._text, status=self._status)


class _StubRouter:
    """Recording stand-in for the legacy ``llm_router`` singleton."""

    def __init__(self, *, text: str = "legacy text") -> None:
        self.calls: list[dict] = []
        self._text = text

    async def chat(self, messages=None, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        return {"message": {"content": self._text}}


class _StubScalars:
    def __init__(self, items) -> None:
        self._items = items

    def all(self):
        return list(self._items)


class _StubResult:
    def __init__(self, items) -> None:
        self._items = items

    def scalars(self):
        return _StubScalars(self._items)

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None


class _StubDB:
    """Minimal async-session stand-in: queued execute() results, a single
    ``get()`` entity, and recorded commit/rollback/add calls."""

    def __init__(self, *, execute_results=None, fresh=None) -> None:
        self._execute_results = list(execute_results or [])
        self._fresh = fresh
        self.commits = 0
        self.rollbacks = 0
        self.added: list = []

    async def execute(self, stmt):
        items = self._execute_results.pop(0) if self._execute_results else []
        return _StubResult(items)

    async def rollback(self):
        self.rollbacks += 1

    async def get(self, model, key):
        return self._fresh

    async def commit(self):
        self.commits += 1

    def add(self, obj):
        self.added.append(obj)


def _manager():
    from app.core.report_manager import ReportManager

    return ReportManager()


@pytest.fixture
def _agentic_core_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", True)


def _report(**overrides):
    report = SimpleNamespace(
        id="r1",
        project_id="p1",
        title="Final Research Report",
        scope="Final Report",
        version=1,
        executive_summary=None,
        mece_categories_json="[]",
        content_json=None,
        status="draft",
        finding_ids_json=json.dumps(["f1", "f2", "f3", "f4", "f5"]),
    )
    for key, value in overrides.items():
        setattr(report, key, value)
    return report


# ── static: dispatcher path present, legacy branch retired ─────────────


def test_w5_report_manager_sites_carry_dispatcher_path_and_no_legacy_branch():
    exec_summary = _function_source("_generate_executive_summary")
    assert "agentic_core" not in exec_summary, "W9 retired the feature-flag gate"
    assert "agentic.completion" in exec_summary
    assert 'purpose="report.exec_summary"' in exec_summary
    assert "llm_router.chat" not in exec_summary, "legacy branch must be gone"

    mece = _function_source("_generate_mece_categories")
    assert "agentic_core" not in mece
    assert "agentic.structured" in mece
    assert 'purpose="report.mece"' in mece
    assert '"categories"' in mece, "structured root object wraps the category array"
    assert "llm_router.chat" not in mece

    compose_full = _function_source("_compose_full_report")
    assert "agentic_core" not in compose_full
    assert "agentic.structured" in compose_full
    assert 'purpose="report.weakest_section"' in compose_full
    assert "llm_router.chat" not in compose_full

    section = _function_source("_compose_section")
    assert section.count("settings.agentic_core") == 0, "W9 retired all three flag gates"
    assert section.count("agentic.completion") == 3
    assert 'purpose="report.insights_narrative"' in section
    assert 'purpose="report.recommendations_narrative"' in section
    assert 'purpose="report.gaps_analysis"' in section
    assert section.count("llm_router.chat") == 0, "all three legacy branches retired"


# ── behavior: _generate_executive_summary (report.exec_summary) ─────────


async def test_exec_summary_flag_on_dispatches_report_exec_summary(monkeypatch, _agentic_core_on):
    router_stub = _StubRouter()
    dispatcher_stub = _StubAgentic(text="SITUATION\nA dispatcher executive summary.")
    monkeypatch.setattr("app.core.llm_router.llm_router", router_stub)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    fresh = SimpleNamespace(executive_summary=None)
    db = _StubDB(execute_results=[[SimpleNamespace(text="finding text one")]], fresh=fresh)

    await _manager()._generate_executive_summary(_report(), db)

    assert router_stub.calls == [], "flag on must not call the legacy plane directly"
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "report.exec_summary"
    assert kwargs["project_id"] == "p1"
    assert kwargs["params"].temperature == 0.3
    assert kwargs["spine_phase"] in SPINE_PHASES
    assert "SCR" in kwargs["messages"][0]["content"]
    assert fresh.executive_summary == "SITUATION\nA dispatcher executive summary."
    assert db.commits == 1


# ── behavior: _generate_mece_categories (report.mece) ───────────────────


_MECE_CATEGORIES = [
    {"name": "Users struggle with exports", "description": "So-what.", "finding_ids": ["f1"]},
]


def _mece_report():
    return _report(finding_ids_json=json.dumps(["f1", "f2", "f3", "f4", "f5"]))


def _mece_db(fresh):
    findings = [SimpleNamespace(id=f"f{i}", text=f"finding text {i}") for i in range(3)]
    return _StubDB(execute_results=[findings], fresh=fresh)


async def test_mece_flag_on_dispatches_report_mece(monkeypatch, _agentic_core_on):
    router_stub = _StubRouter()
    dispatcher_stub = _StubAgentic(value={"categories": _MECE_CATEGORIES})
    monkeypatch.setattr("app.core.llm_router.llm_router", router_stub)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    fresh = SimpleNamespace(mece_categories_json=None)
    await _manager()._generate_mece_categories(_mece_report(), _mece_db(fresh))

    assert router_stub.calls == []
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "structured"
    assert kwargs["purpose"] == "report.mece"
    assert kwargs["project_id"] == "p1"
    assert kwargs["params"].temperature == 0.3
    schema = kwargs["schema"]
    assert schema["type"] == "object" and schema["required"] == ["categories"]
    assert json.loads(fresh.mece_categories_json) == _MECE_CATEGORIES


async def test_mece_flag_on_failed_outcome_writes_nothing(monkeypatch, _agentic_core_on):
    router_stub = _StubRouter()
    dispatcher_stub = _StubAgentic(value=None, status="failure")
    monkeypatch.setattr("app.core.llm_router.llm_router", router_stub)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    fresh = SimpleNamespace(mece_categories_json=None)
    db = _mece_db(fresh)
    await _manager()._generate_mece_categories(_mece_report(), db)

    assert router_stub.calls == []
    assert len(dispatcher_stub.calls) == 1
    assert fresh.mece_categories_json is None, "mirrors the legacy parse-failure path"
    assert db.commits == 0


async def test_compose_section_ensemble_scores_discloses_response_level_heuristic():
    """Report metrics must not mislabel response consensus as Fleiss reliability."""
    template = {
        "section": "Validation & Consensus Metrics",
        "source": "ensemble_scores",
        "format": "metrics",
    }
    report = SimpleNamespace(
        content_json=json.dumps({"consensus_scores": [0.4, 0.8], "avg_consensus": 0.6})
    )

    result = await _manager()._compose_section(
        template,
        {"insights": [], "recommendations": [], "nuggets": [], "facts": []},
        report,
        [],
    )

    assert "response-level consensus" in result
    assert "heuristic" in result
    assert "not Fleiss' Kappa" in result
    assert "coded evidence-unit matrices" in result
    assert "computed using Fleiss' Kappa + cosine similarity" not in result


# ── behavior: _compose_full_report scoring loop (report.weakest_section) ─


_SCORES_CONVERGED = {
    "scores": {t["section"]: 9 for t in [
        {"section": "I. Executive Summary (SCR)"},
        {"section": "II. Research Methodology & Rigor"},
    ]},
    "weakest": "",
    "reason": "all good",
    "suggestion": "",
}


def _compose_db(fresh):
    # 4 finding-class queries (empty) + 1 L2 methodology query (empty)
    return _StubDB(execute_results=[[], [], [], [], []], fresh=fresh)


async def test_compose_full_report_flag_on_dispatches_report_weakest_section(
    monkeypatch, _agentic_core_on
):
    router_stub = _StubRouter()
    dispatcher_stub = _StubAgentic(value=_SCORES_CONVERGED)
    monkeypatch.setattr("app.core.llm_router.llm_router", router_stub)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    fresh = SimpleNamespace(content_json=None, status="draft", version=1)
    db = _compose_db(fresh)
    await _manager()._compose_full_report(_report(), "p1", db)

    assert router_stub.calls == []
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "structured"
    assert kwargs["purpose"] == "report.weakest_section"
    assert kwargs["project_id"] == "p1"
    assert kwargs["params"].temperature == 0.2
    assert kwargs["spine_phase"] in SPINE_PHASES
    schema = kwargs["schema"]
    assert schema["type"] == "object"
    assert "weakest" in schema["required"] and "scores" in schema["required"]
    content = json.loads(fresh.content_json)
    assert "full_document" in content, "converged scores still store the document"
    assert fresh.status == "review"


# ── behavior: _compose_section narrative sites ───────────────────────────


def _section_args(source, fmt):
    template = {"section": "Section", "source": source, "format": fmt}
    findings = {
        "insights": [{"text": "insight one", "confidence": 0.9, "phase": "analysis"}],
        "recommendations": [{"text": "recommendation one"}],
        "nuggets": [],
        "facts": [],
    }
    report = SimpleNamespace(project_id="p1", executive_summary=None)
    return template, findings, report


async def test_compose_section_insights_flag_on_dispatches_report_insights_narrative(
    monkeypatch, _agentic_core_on
):
    router_stub = _StubRouter()
    dispatcher_stub = _StubAgentic(text="dispatcher detailed narrative")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    template, findings, report = _section_args("insights", "detailed_narrative")

    result = await _manager()._compose_section(
        template, findings, report, [], project_id="p1"
    )

    assert result == "dispatcher detailed narrative"
    assert router_stub.calls == []
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "report.insights_narrative"
    assert kwargs["project_id"] == "p1"
    assert kwargs["params"].temperature == 0.3
    assert kwargs["spine_phase"] in SPINE_PHASES


async def test_compose_section_recommendations_flag_on_dispatches(
    monkeypatch, _agentic_core_on
):
    router_stub = _StubRouter()
    dispatcher_stub = _StubAgentic(text="dispatcher recommendation detail")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    template, findings, report = _section_args("recommendations", "priority_table")

    result = await _manager()._compose_section(
        template, findings, report, [], project_id="p1"
    )

    assert result == "dispatcher recommendation detail"
    assert router_stub.calls == []
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "report.recommendations_narrative"
    assert kwargs["project_id"] == "p1"


async def test_compose_section_gaps_flag_on_dispatches(monkeypatch, _agentic_core_on):
    router_stub = _StubRouter()
    dispatcher_stub = _StubAgentic(text="dispatcher gaps analysis")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    template, findings, report = _section_args("gaps", "narrative")

    result = await _manager()._compose_section(
        template, findings, report, [], project_id="p1"
    )

    assert result == "dispatcher gaps analysis"
    assert router_stub.calls == []
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "report.gaps_analysis"
    assert kwargs["project_id"] == "p1"
    assert kwargs["spine_phase"] in SPINE_PHASES


async def test_compose_section_empty_dispatcher_text_falls_back_to_sentinel(
    monkeypatch, _agentic_core_on
):
    router_stub = _StubRouter()
    dispatcher_stub = _StubAgentic(text="")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    template, findings, report = _section_args("insights", "detailed_narrative")

    result = await _manager()._compose_section(
        template, findings, report, [], project_id="p1"
    )

    assert result == "Detailed narrative generation failed.", (
        "empty dispatcher text mirrors the legacy missing-content sentinel"
    )
    assert router_stub.calls == []
