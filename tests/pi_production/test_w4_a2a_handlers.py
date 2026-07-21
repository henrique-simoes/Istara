"""W4 contract coverage — A2A handler migration (master plan §8 W4).

The three A2A LLM call sites in ``agent_lifecycle.py``
(``_handle_collaboration``, ``_initiate_debate`` synthesis, ``_handle_debate``
critique) route through the AgenticDispatcher — ``chat_turn`` →
``a2a.collaboration``, ``completion`` → ``a2a.debate_synthesis`` /
``a2a.debate_critique`` — gated on the ``agentic_core`` feature flag, with the
legacy ``ollama.chat`` branch preserved alongside for ``agentic_core=False``.

Covered here (all stubbed/static — no live model activity):

* static: each handler carries both the dispatcher path (flag on) and the
  preserved legacy branch; the count-to-zero ratchet stays green at 70 with
  the three sites still allowlisted (legacy branch preserved, not retired);
* behavior (flag off): ``_handle_debate`` uses the legacy plane exactly as
  before and never touches the dispatcher;
* behavior (flag on): each handler dispatches with the planned verb, purpose,
  project scope, and spine-phase tag, and its reply content is what gets sent
  back over A2A.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LIFECYCLE = REPO_ROOT / "backend/app/core/agent_lifecycle.py"

SPINE_PHASES = {
    "intent", "context", "plan", "tool_selection", "execution",
    "recovery", "grounding", "synthesis", "review", "governance",
}


# ── helpers ─────────────────────────────────────────────────────────────


def _function_source(function_name: str) -> str:
    text = LIFECYCLE.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(f"{function_name} not found in {LIFECYCLE}")


class _StubAgentic:
    """Recording stand-in for the ``agentic`` dispatcher singleton."""

    def __init__(self, *, text: str = "dispatcher reply") -> None:
        self.calls: list[tuple[str, dict]] = []
        self._text = text

    async def chat_turn(self, **kwargs):
        self.calls.append(("chat_turn", kwargs))
        return SimpleNamespace(text=self._text, status="success", usage={})

    async def completion(self, **kwargs):
        self.calls.append(("completion", kwargs))
        return SimpleNamespace(text=self._text, status="success", usage={})


class _StubOllama:
    def __init__(self, *, text: str = "legacy reply") -> None:
        self.calls: list[dict] = []
        self._text = text

    async def chat(self, messages=None, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        return {"message": {"content": self._text}}


class _StubDB:
    def __init__(self, task=None) -> None:
        self._task = task
        self.commits = 0

    async def get(self, model, key):
        return self._task

    async def commit(self):
        self.commits += 1


def _mixin(agent_id: str = "istara-main"):
    from app.core.agent_lifecycle import AgentLifecycleMixin

    return AgentLifecycleMixin(agent_id)


@pytest.fixture
def _agentic_core_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", True)


@pytest.fixture
def _agentic_core_off(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", False)


# ── static: both paths present, ratchet green ───────────────────────────


def test_w4_ratchet_stays_green_at_70():
    """The legacy branch is preserved, so the three sites stay allowlisted."""
    from tests.pi_migration.test_count_to_zero import EXPECTED_PRODUCT_SITES, check_count_to_zero

    assert EXPECTED_PRODUCT_SITES == 70
    check_count_to_zero()


def test_w4_handlers_carry_dispatcher_path_and_preserved_legacy_branch():
    collab = _function_source("_handle_collaboration")
    assert "agentic_core" in collab and "agentic.chat_turn" in collab
    assert "ollama.chat" in collab, "legacy branch must be preserved alongside"
    assert "a2a-collab:" in collab

    initiate = _function_source("_initiate_debate")
    assert "agentic_core" in initiate and "agentic.completion" in initiate
    assert "a2a.debate_synthesis" in initiate
    assert "ollama.chat" in initiate

    handle = _function_source("_handle_debate")
    assert "agentic_core" in handle and "agentic.completion" in handle
    assert "a2a.debate_critique" in handle
    assert "ollama.chat" in handle


# ── behavior: _handle_debate (critique) ──────────────────────────────────


def _debate_msg(**overrides):
    msg = {
        "id": "m1",
        "from_agent_id": "istara-devops",
        "content": "Please critique this analysis.",
        "project_id": "p1",
        "metadata": {"project_id": "p1", "context_id": "ctx-1"},
    }
    msg.update(overrides)
    return msg


async def test_handle_debate_flag_off_uses_legacy_plane(monkeypatch, _agentic_core_off):
    import app.services.a2a as a2a_service

    ollama_stub = _StubOllama(text="legacy critique")
    dispatcher_stub = _StubAgentic()
    sent: list[dict] = []

    async def _send(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr("app.core.agent_lifecycle.ollama", ollama_stub)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr(a2a_service, "send_message", _send)

    await _mixin()._handle_debate(_StubDB(), _debate_msg())

    assert len(ollama_stub.calls) == 1, "flag off must use the legacy plane"
    assert dispatcher_stub.calls == [], "flag off must not touch the dispatcher"
    assert sent[0]["message_type"] == "debate_response"
    assert sent[0]["content"] == "legacy critique"
    assert sent[0]["project_id"] == "p1"


async def test_handle_debate_flag_on_dispatches_a2a_debate_critique(monkeypatch, _agentic_core_on):
    import app.services.a2a as a2a_service

    ollama_stub = _StubOllama()
    dispatcher_stub = _StubAgentic(text="dispatcher critique")
    sent: list[dict] = []

    async def _send(**kwargs):
        sent.append(kwargs)

    monkeypatch.setattr("app.core.agent_lifecycle.ollama", ollama_stub)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr(a2a_service, "send_message", _send)

    await _mixin()._handle_debate(_StubDB(), _debate_msg())

    assert ollama_stub.calls == [], "flag on must not call the legacy plane directly"
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "a2a.debate_critique"
    assert kwargs["project_id"] == "p1"
    assert kwargs["spine_phase"] == "review" and kwargs["spine_phase"] in SPINE_PHASES
    assert "critical reviewer" in kwargs["system"]
    assert kwargs["messages"] == [{"role": "user", "content": "Please critique this analysis."}]
    assert sent[0]["content"] == "dispatcher critique"


# ── behavior: _initiate_debate (synthesis) ───────────────────────────────


async def test_initiate_debate_flag_on_synthesizes_via_dispatcher(monkeypatch, _agentic_core_on):
    import app.services.a2a as a2a_service

    ollama_stub = _StubOllama()
    dispatcher_stub = _StubAgentic(text="synthesized analysis")
    sent: list[dict] = []

    async def _send(**kwargs):
        sent.append(kwargs)

    async def _get_messages(*args, **kwargs):
        context_id = sent[0]["metadata"]["context_id"]
        return [{
            "metadata": {"context_id": context_id},
            "message_type": "debate_response",
            "content": "peer critique",
        }]

    async def _no_sleep(*args, **kwargs):
        return None

    monkeypatch.setattr("app.core.agent_lifecycle.ollama", ollama_stub)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr(a2a_service, "send_message", _send)
    monkeypatch.setattr(a2a_service, "get_messages", _get_messages)
    monkeypatch.setattr("asyncio.sleep", _no_sleep)

    task = SimpleNamespace(id="t1", project_id="p1", title="Analysis task")
    output = SimpleNamespace(summary="original analysis " * 20)

    result = await _mixin()._initiate_debate(_StubDB(), task, output)

    assert result == "synthesized analysis"
    assert ollama_stub.calls == []
    assert sent[0]["message_type"] == "debate_request"
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "a2a.debate_synthesis"
    assert kwargs["project_id"] == "p1"
    assert kwargs["task_id"] == "t1"
    assert kwargs["spine_phase"] == "synthesis" and kwargs["spine_phase"] in SPINE_PHASES
    user = kwargs["messages"][0]["content"]
    assert "Original analysis" in user and "peer critique" in user


# ── behavior: _handle_collaboration (chat_turn) ──────────────────────────


async def test_handle_collaboration_flag_on_dispatches_chat_turn(monkeypatch, _agentic_core_on):
    import app.services.a2a as a2a_service

    ollama_stub = _StubOllama()
    dispatcher_stub = _StubAgentic(text="collaboration analysis")
    sent: list[dict] = []

    async def _send(**kwargs):
        sent.append(kwargs)

    async def _thread(*args, **kwargs):
        return []

    async def _rag(*args, **kwargs):
        return SimpleNamespace(has_context=False, context_text="")

    monkeypatch.setattr("app.core.agent_lifecycle.ollama", ollama_stub)
    monkeypatch.setattr("app.core.agent_lifecycle.retrieve_context", _rag)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr(a2a_service, "send_message", _send)
    monkeypatch.setattr(a2a_service, "get_conversation_thread", _thread)
    monkeypatch.setattr(
        "app.core.agent_identity.get_capability_card", lambda agent_id: {"specialties": ["UX"]}
    )

    task = SimpleNamespace(
        id="t1", project_id="p1", title="Usability study", description="d",
        status="backlog", agent_notes="",
    )
    db = _StubDB(task=task)
    msg = {
        "id": "m1",
        "from_agent_id": "istara-devops",
        "content": "Can you review the onboarding findings?",
        "project_id": "p1",
        "metadata": {"task_id": "t1", "project_id": "p1", "context_id": "ctx-9"},
    }

    await _mixin()._handle_collaboration(db, msg)

    assert ollama_stub.calls == []
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "chat_turn"
    assert kwargs["project_id"] == "p1"
    assert kwargs["agent_id"] == "istara-main"
    assert kwargs["session_key"] == "a2a-collab:ctx-9"
    assert kwargs["user_text"] == "Can you review the onboarding findings?"
    assert kwargs["messages"] == [], "empty thread maps to empty history"
    assert "Usability study" in kwargs["system_prompt"]
    assert kwargs["task_id"] == "t1"
    assert kwargs["spine_phase"] == "synthesis" and kwargs["spine_phase"] in SPINE_PHASES
    assert sent[0]["message_type"] == "collaboration_response"
    assert sent[0]["content"] == "collaboration analysis"
    assert sent[0]["project_id"] == "p1"
    assert "collaboration analysis" in task.agent_notes
    assert db.commits == 1
