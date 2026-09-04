"""W3 contract coverage — research spine + steering migration (master plan §8 W3).

Proves the eight W3 sites now enter through the AgenticDispatcher with the
planned verbs/purposes and the spine-phase ledger tagging:

* static: the migrated functions contain no direct legacy-plane calls, and the
  allowlist ratchet sits at 70 (87 − 9 W2 − 8 W3);
* plumbing: per-run dynamic tools (``run_skill``) merge into the Pi session
  catalog and honor the run allowlist; ``dispatcher.react`` forwards the
  OpenAI tool schemas to the legacy executor and ``extra_tools`` to the Pi
  engine; the dispatcher exposes the steering-binding helper used by L10;
* behavior (both engines): L6 ``verify_claim`` maps the structured outcome to
  the same ``VerificationResult`` contract and treats an unparsed legacy
  outcome exactly like the old line-format fallback (UNVERIFIED); L5
  ``_self_verify_output`` keeps its heuristic fallbacks;
* ledger: a spine-tagged dispatch persists exactly one row carrying the
  ``spine_phase`` from the §8 W3 taxonomy.

All verification here is stubbed/static: no live model activity and no
external traffic.
"""

from __future__ import annotations

import ast
import inspect
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.agentic.types import StructuredResult, TurnParams, TurnResult
from app.models.agentic_usage import AgenticUsageRow
from app.models.database import async_session, init_db

REPO_ROOT = Path(__file__).resolve().parents[2]

SPINE_PHASES = {
    "intent",
    "context",
    "plan",
    "tool_selection",
    "execution",
    "recovery",
    "grounding",
    "synthesis",
    "review",
    "governance",
}


# ── helpers ─────────────────────────────────────────────────────────────


class _StubAgentic:
    """Recording stand-in for the ``agentic`` dispatcher singleton."""

    def __init__(
        self,
        *,
        structured: StructuredResult | None = None,
        completion: TurnResult | None = None,
        raise_exc: Exception | None = None,
    ) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._structured = structured
        self._completion = completion
        self._raise = raise_exc

    async def structured(self, **kwargs):
        self.calls.append(("structured", kwargs))
        if self._raise:
            raise self._raise
        return self._structured

    async def completion(self, **kwargs):
        self.calls.append(("completion", kwargs))
        if self._raise:
            raise self._raise
        return self._completion


class _RecordingLegacyExecutor:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "text": "legacy-done",
            "status": "success",
            "stop_reason": "stop",
            "usage": {},
        }


class _StubPiService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def run_react(self, **kwargs):
        self.calls.append(("run_react", kwargs))
        return {
            "text": "pi-done",
            "status": "success",
            "stop_reason": "stop",
            "usage": {},
        }

    def steering_binding(self, *, agent_id, project_id, session_key=None):
        return SimpleNamespace(
            agent_id=agent_id, project_id=project_id, session_key=session_key
        )


@pytest.fixture
async def usage_db():
    await init_db()
    async with async_session() as session:
        await session.execute(AgenticUsageRow.__table__.delete())
        await session.commit()
    try:
        yield
    finally:
        async with async_session() as session:
            await session.execute(AgenticUsageRow.__table__.delete())
            await session.commit()


def _function_source(path: Path, function_name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        ):
            return ast.get_source_segment(path.read_text(encoding="utf-8"), node) or ""
    raise AssertionError(f"{function_name} not found in {path}")


def _direct_legacy_calls(source: str) -> list[str]:
    banned = (
        "ollama.chat",
        "ollama.chat_stream",
        "llm_router.chat",
        "compute_registry.chat",
        ".node.chat",
    )
    return [pattern for pattern in banned if pattern in source]


# ── static: the 8 sites left the legacy plane ───────────────────────────


def test_w3_ratchet_floor_is_53():
    from tests.pi_migration.test_count_to_zero import (
        EXPECTED_PRODUCT_SITES,
        check_count_to_zero,
    )

    assert EXPECTED_PRODUCT_SITES == 0, (
        "W3: 78 − 8 = 70; W8 migrated the 17 embed sites: 70 − 17 = 53; "
        "W9 retired the 53 preserved legacy branches: ratchet floor is 0"
    )
    check_count_to_zero()


def test_agent_research_migrated_functions_have_no_direct_legacy_calls():
    path = REPO_ROOT / "backend/app/core/agent_research.py"
    for fn in (
        "_execute_general_task",
        "_create_research_plan",
        "_execute_single_step",
        "_self_verify_output",
    ):
        source = _function_source(path, fn)
        assert not _direct_legacy_calls(source), (
            f"{fn} still calls the legacy plane directly: {_direct_legacy_calls(source)}"
        )
        assert "agentic" in source, f"{fn} must enter through the AgenticDispatcher"


def test_self_check_and_agent_execution_no_longer_import_the_legacy_plane():
    for rel in (
        "backend/app/core/self_check.py",
        "backend/app/core/agent_execution.py",
    ):
        source = (REPO_ROOT / rel).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module != "app.core.ollama", (
                    f"{rel} still imports the legacy plane"
                )


def test_steering_reply_migrates_but_w4_a2a_sites_stay_allowlisted():
    path = REPO_ROOT / "backend/app/core/agent_lifecycle.py"
    steering = _function_source(path, "_execute_steering_message")
    assert not _direct_legacy_calls(steering), (
        f"L10 steering reply still calls the legacy plane: {_direct_legacy_calls(steering)}"
    )
    assert "steering_binding" in steering, "L10 must wire a SteeringBinding (H-5)"
    # W4 migrated the A2A sites behind a preserved legacy branch; W9 retired
    # that branch, so they too must be dispatcher-only now.
    for fn in ("_handle_collaboration", "_initiate_debate", "_handle_debate"):
        source = _function_source(path, fn)
        assert not _direct_legacy_calls(source), (
            f"{fn} still calls the legacy plane directly after W9: {_direct_legacy_calls(source)}"
        )


# ── plumbing: dynamic tools + dispatcher forwarding ─────────────────────


def test_extra_tools_merge_into_catalog_and_honor_allowlist():
    from app.core.pi_runtime.tools import build_tool_catalog, catalog_tool_names

    dynamic = [
        {
            "name": "run_skill",
            "description": "Run a ranked research skill.",
            "parameters": {
                "type": "object",
                "properties": {"skill_name": {"type": "string"}},
            },
        }
    ]
    names = catalog_tool_names(["search_documents", "run_skill"], extra_tools=dynamic)
    assert "run_skill" in names and "search_documents" in names
    # A dynamic tool outside the run allowlist is never exported — the
    # session catalog and the Python-side allowlist stay identical.
    assert "run_skill" not in catalog_tool_names(
        ["search_documents"], extra_tools=dynamic
    )
    catalog = build_tool_catalog(["run_skill"], extra_tools=dynamic)
    assert catalog[0]["parameters"]["properties"]["skill_name"]["type"] == "string"


async def test_react_forwards_tool_schemas_to_legacy_and_extra_tools_to_pi(usage_db):
    tools = [{"type": "function", "function": {"name": "search_documents"}}]
    extra = [
        {"name": "run_skill", "description": "d", "parameters": {"type": "object"}}
    ]

    legacy = _RecordingLegacyExecutor()
    dispatcher = AgenticDispatcher(pi_service=_StubPiService(), legacy_executor=legacy)
    await dispatcher.react(
        purpose="w3.react.legacy",
        project_id="p1",
        agent_id="a1",
        session_key="task:t1",
        system="s",
        messages=[],
        user_text="go",
        tool_executor=None,
        tool_names=["search_documents", "run_skill"],
        tools=tools,
        extra_tools=extra,
        params=TurnParams(max_turns=5),
        engine="legacy",
    )
    assert legacy.calls[0]["tools"] is tools, (
        "the legacy executor needs the full OpenAI schemas"
    )

    service = _StubPiService()
    dispatcher = AgenticDispatcher(
        pi_service=service, legacy_executor=_RecordingLegacyExecutor()
    )
    await dispatcher.react(
        purpose="w3.react.pi",
        project_id="p1",
        agent_id="a1",
        session_key="task:t1",
        system="s",
        messages=[],
        user_text="go",
        tool_executor=None,
        tool_names=["search_documents", "run_skill"],
        tools=tools,
        extra_tools=extra,
        params=TurnParams(max_turns=5),
        engine="pi",
    )
    _, kwargs = service.calls[0]
    assert kwargs["extra_tools"] is extra, (
        "run_skill rides the Pi session catalog as a dynamic tool"
    )


def test_engine_run_react_accepts_and_forwards_extra_tools():
    from app.core.pi_runtime.engine import PiExecutionService

    signature = inspect.signature(PiExecutionService.run_react)
    assert "extra_tools" in signature.parameters


async def test_engine_run_react_forwards_extra_tools_to_the_turn_driver():
    from app.core.pi_runtime.engine import PiExecutionService

    captured: list[dict] = []

    class _Capturing(PiExecutionService):
        async def _collect_turn(self, **kwargs):
            captured.append(kwargs)
            return {"text": "", "status": "success", "usage": {}}

    extra = [
        {"name": "run_skill", "description": "d", "parameters": {"type": "object"}}
    ]
    await _Capturing().run_react(
        purpose="w3.plumbing",
        project_id="p1",
        agent_id="a1",
        session_key="task:t1",
        system="s",
        messages=[],
        user_text="go",
        tool_executor=None,
        tool_names=["run_skill"],
        params=TurnParams(),
        extra_tools=extra,
    )
    assert captured[0]["extra_tools"] is extra


def test_dispatcher_exposes_steering_binding_helper_for_l10():
    dispatcher = AgenticDispatcher(
        pi_service=_StubPiService(), legacy_executor=_RecordingLegacyExecutor()
    )
    binding = dispatcher.steering_binding(agent_id="a1", project_id="p1")
    assert binding.agent_id == "a1" and binding.project_id == "p1"


# ── behavior: L6 verify_claim (both engines + fallbacks) ───────────────


def _rag_context():
    return SimpleNamespace(
        has_context=True,
        context_text="Interview transcript A: users struggle with onboarding.",
    )


async def _fake_retrieve_context(*args, **kwargs):
    return _rag_context()


async def test_verify_claim_maps_structured_outcome(monkeypatch):
    import app.core.self_check as self_check

    stub = _StubAgentic(
        structured=StructuredResult(
            text="",
            status="success",
            value={
                "confidence": "HIGH",
                "supporting": ["transcript A"],
                "contradicting": [],
                "notes": "Directly supported.",
            },
        )
    )
    monkeypatch.setattr(self_check, "retrieve_context", _fake_retrieve_context)
    monkeypatch.setattr("app.core.agentic.agentic", stub)

    result = await self_check.verify_claim("Users struggle with onboarding", "p1")
    assert result.confidence == self_check.Confidence.HIGH
    assert result.supporting_sources == ["transcript A"]
    assert result.notes == "Directly supported."

    method, kwargs = stub.calls[0]
    assert method == "structured"
    assert kwargs["purpose"] == "spine.self_check"
    assert kwargs["spine_phase"] == "grounding"
    assert kwargs["spine_phase"] in SPINE_PHASES
    assert kwargs["params"].temperature == 0.1
    assert kwargs["schema"]["properties"]["confidence"]["enum"] == [
        "HIGH",
        "MEDIUM",
        "LOW",
        "UNVERIFIED",
    ]


async def test_verify_claim_unparsed_legacy_outcome_is_unverified(monkeypatch):
    """Legacy unparsed structured output (status=error, no value) degrades to
    UNVERIFIED — exactly what garbage line-format text produced before W3."""
    import app.core.self_check as self_check

    stub = _StubAgentic(
        structured=StructuredResult(text="garbage", status="error", value={})
    )
    monkeypatch.setattr(self_check, "retrieve_context", _fake_retrieve_context)
    monkeypatch.setattr("app.core.agentic.agentic", stub)

    result = await self_check.verify_claim("Some claim", "p1")
    assert result.confidence == self_check.Confidence.UNVERIFIED
    assert result.supporting_sources == [] and result.contradicting_sources == []


async def test_verify_claim_engine_failure_propagates_like_before(monkeypatch):
    """A raising engine surfaces to the caller exactly as an ollama failure did
    (callers like agent_research:994 wrap it); nothing is fabricated."""
    import app.core.self_check as self_check

    stub = _StubAgentic(raise_exc=RuntimeError("engine down"))
    monkeypatch.setattr(self_check, "retrieve_context", _fake_retrieve_context)
    monkeypatch.setattr("app.core.agentic.agentic", stub)

    with pytest.raises(RuntimeError, match="engine down"):
        await self_check.verify_claim("Some claim", "p1")


# ── behavior: L5 _self_verify_output fallbacks ──────────────────────────


def _task():
    return SimpleNamespace(
        id="t1", project_id="p1", title="Task", description="d", instructions=None
    )


def _output():
    return SimpleNamespace(
        success=True,
        errors=[],
        summary="A long enough summary of the produced research output.",
        nuggets=[{"text": "n"}],
        facts=[],
        insights=[],
        recommendations=[],
    )


async def test_self_verify_uses_structured_value(monkeypatch):
    from app.core.agent_research import AgentResearchMixin

    stub = _StubAgentic(
        structured=StructuredResult(
            text="",
            status="success",
            value={
                "verified": False,
                "confidence": 0.4,
                "reason": "Unsupported claim found.",
            },
        )
    )
    monkeypatch.setattr("app.core.agentic.agentic", stub)

    mixin = AgentResearchMixin.__new__(AgentResearchMixin)
    verified, reason = await mixin._self_verify_output(_task(), _output())
    assert verified is False and reason == "Unsupported claim found."
    _, kwargs = stub.calls[0]
    assert kwargs["purpose"] == "spine.verify" and kwargs["spine_phase"] == "review"


async def test_self_verify_error_status_falls_back_to_heuristic(monkeypatch):
    from app.core.agent_research import AgentResearchMixin

    stub = _StubAgentic(
        structured=StructuredResult(text="not json", status="error", value={})
    )
    monkeypatch.setattr("app.core.agentic.agentic", stub)

    mixin = AgentResearchMixin.__new__(AgentResearchMixin)
    verified, reason = await mixin._self_verify_output(_task(), _output())
    assert verified is True and "heuristic" in reason.lower()


async def test_self_verify_engine_failure_falls_back_to_heuristic(monkeypatch):
    from app.core.agent_research import AgentResearchMixin

    stub = _StubAgentic(raise_exc=RuntimeError("engine down"))
    monkeypatch.setattr("app.core.agentic.agentic", stub)

    mixin = AgentResearchMixin.__new__(AgentResearchMixin)
    verified, reason = await mixin._self_verify_output(_task(), _output())
    assert verified is True and "heuristic" in reason.lower()


# ── ledger: spine-phase tagging persists ────────────────────────────────


async def test_spine_phase_tag_lands_in_the_usage_ledger(usage_db):
    purpose = f"w3.spine.{uuid.uuid4().hex[:8]}"
    dispatcher = AgenticDispatcher(
        pi_service=_StubPiService(), legacy_executor=_RecordingLegacyExecutor()
    )
    await dispatcher.completion(
        purpose=purpose,
        project_id="p1",
        system=None,
        messages=[{"role": "user", "content": "hi"}],
        params=TurnParams(temperature=0.3),
        engine="legacy",
        task_id="t1",
        spine_phase="plan",
    )
    async with async_session() as session:
        rows = list(
            (
                await session.execute(
                    select(AgenticUsageRow).where(AgenticUsageRow.purpose == purpose)
                )
            ).scalars()
        )
    assert len(rows) == 1
    assert rows[0].spine_phase == "plan"
    assert rows[0].task_id == "t1"
