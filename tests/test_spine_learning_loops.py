"""Governed learning: nothing strong is learned from raw success, and nothing leaks across projects.

Self-improvement governance contract (AGENTS.md; docs/architecture/
self-improvement-governance-contract.md): no system may "learn strong positive skill/model
signals from raw tool success" or "mutate global process state from project-scoped evidence";
ReasoningBank "may provide weak routing priors". Feedback loops in recommenders amplify
early popularity (Chaney, Stewart & Engelhardt, RecSys 2018), and a routing boost that can
lift an irrelevant item over the relevance floor is exactly that loop.

F10: ``rank_skill_candidates`` added up to +0.18 from usage statistics against a 0.12 floor, so
a skill with a good history cleared the floor for ANY query.
F16: ReasoningBank ``retrieve`` committed ``usage_count`` on every read; the API retrieved twice;
only the 200 newest memories were ever scored; the vector-health read wrote profile manifests.
F9: a self-evolution promotion from one project wrote the agent's global persona overlay,
which every project's Prompt-RAG reads; the skill-description embedding cache was never
invalidated and truncated mismatched dimensions with ``zip``.
Measurement 6: a planted successful-but-wrong skill run (the model's own self-check passes) must
teach ReasoningBank, skill routing and self-evolution nothing strong.
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest

from app.config import settings

# ── F10: learned boosts cannot qualify an irrelevant skill ────────────────


@pytest.fixture
def usage_stats(monkeypatch, tmp_path):
    from app.skills.registry import load_default_skills
    from app.skills.skill_manager import skill_manager

    load_default_skills()
    stats: dict[str, dict] = {}
    monkeypatch.setattr(
        skill_manager,
        "get_usage_stats",
        lambda name, project_id=None: stats.get(name, {"executions": 0}),
    )
    return stats


async def test_perfect_history_never_lifts_an_irrelevant_skill_over_the_floor(
    usage_stats, monkeypatch
):
    from app.core.agent_skill_tools import rank_skill_candidates

    async def _no_boost(*args, **kwargs):
        return {}

    monkeypatch.setattr("app.core.agent_skill_tools._telemetry_quality_boost", _no_boost)
    monkeypatch.setattr("app.core.agent_skill_tools._reasoning_memory_boosts", _no_boost)
    usage_stats["tree-testing"] = {
        "executions": 500,
        "successes": 500,
        "success_rate": 1.0,
        "avg_quality": 1.0,
        "utility_score": 1.0,
    }
    task = SimpleNamespace(
        title="Summarize participant quotes about invoice reminders",
        description="",
        project_id="p1",
        agent_id="",
        skill_name="",
    )
    candidates = await rank_skill_candidates(task=task)
    assert "tree-testing" not in [c.name for c in candidates]


async def test_learned_boost_reorders_relevant_skills_but_stays_a_weak_prior(
    usage_stats, monkeypatch
):
    from app.core.agent_skill_tools import rank_skill_candidates

    async def _no_boost(*args, **kwargs):
        return {}

    monkeypatch.setattr("app.core.agent_skill_tools._telemetry_quality_boost", _no_boost)
    monkeypatch.setattr("app.core.agent_skill_tools._reasoning_memory_boosts", _no_boost)
    task = SimpleNamespace(
        title="Run a heuristic evaluation of the checkout",
        description="",
        project_id="p1",
        agent_id="",
        skill_name="",
    )
    before = {c.name: c.score for c in await rank_skill_candidates(task=task, limit=10)}
    usage_stats["heuristic-evaluation"] = {
        "executions": 50,
        "successes": 50,
        "success_rate": 1.0,
        "avg_quality": 1.0,
        "utility_score": 1.0,
    }
    after = {c.name: c.score for c in await rank_skill_candidates(task=task, limit=10)}
    lift = after["heuristic-evaluation"] - before["heuristic-evaluation"]
    assert 0 < lift <= 0.5 * before["heuristic-evaluation"]


# ── F16: reads without side effects; old lessons stay reachable ──────────


async def _memory(service, project_id: str, title: str, content: str, **kwargs):
    return await service.record_memory(
        project_id=project_id,
        title=title,
        content=content,
        source_kind="skill",
        outcome="success",
        **kwargs,
    )


async def test_retrieve_is_a_query_and_context_use_is_counted_once():
    from app.core.reasoning_bank import ReasoningMemoryService
    from app.models.database import async_session, init_db
    from app.models.reasoning_memory import ReasoningMemoryItem

    await init_db()
    service = ReasoningMemoryService()
    project_id = f"rb-{uuid.uuid4().hex[:8]}"
    item = await _memory(
        service,
        project_id,
        "Affinity clustering first",
        "Cluster interview quotes before coding them.",
    )
    await service.retrieve(project_id=project_id, query="cluster interview quotes")
    await service.retrieve(project_id=project_id, query="cluster interview quotes")
    async with async_session() as db:
        assert (await db.get(ReasoningMemoryItem, item.id)).usage_count == 0

    await service.context_for_query(project_id=project_id, query="cluster interview quotes")
    async with async_session() as db:
        assert (await db.get(ReasoningMemoryItem, item.id)).usage_count == 1


async def test_reasoning_bank_api_retrieves_once_and_counts_nothing(admin_token):
    from httpx import ASGITransport, AsyncClient

    from app.core import reasoning_bank as rb_module
    from app.main import app
    from app.models.database import async_session, init_db
    from app.models.project import Project
    from app.models.reasoning_memory import ReasoningMemoryItem

    await init_db()
    project_id = f"rbapi-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="RB API"))
        await db.commit()
    item = await _memory(
        rb_module.reasoning_bank,
        project_id,
        "Probe for workarounds",
        "Ask participants to demonstrate the workaround.",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/reasoning-bank/retrieve",
            json={"project_id": project_id, "query": "demonstrate the workaround", "limit": 5},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert response.status_code == 200, response.text
    assert response.json()["memories"] and "Probe for workarounds" in response.json()["context"]
    async with async_session() as db:
        assert (await db.get(ReasoningMemoryItem, item.id)).usage_count == 0


async def test_an_old_relevant_lesson_is_not_hidden_by_200_newer_ones():
    from app.core.reasoning_bank import ReasoningMemoryService
    from app.models.database import init_db

    await init_db()
    service = ReasoningMemoryService()
    project_id = f"rbold-{uuid.uuid4().hex[:8]}"
    await _memory(
        service,
        project_id,
        "Spanish consent wording",
        "Validate Spanish consent wording with a native speaker before launch.",
    )
    for i in range(210):
        await _memory(service, project_id, f"Unrelated lesson {i}", f"Payroll timing note {i}.")
    found = await service.retrieve(project_id=project_id, query="spanish consent wording")
    assert found and found[0]["title"] == "Spanish consent wording"


async def test_vector_health_read_writes_nothing(tmp_path, monkeypatch):
    from app.core import rag
    from app.core.embeddings import EmbeddedChunk, TextChunk
    from app.core.vector_health import check_embedding_dimensions

    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    project_id = "health-read"
    store = rag.VectorStore(project_id)
    await store.add_chunks([EmbeddedChunk(TextChunk(text="x", source="/u/x.md"), [0.1, 0.2])])
    store._profile_manifest.unlink()  # an index bound before manifests existed

    async def _embed(text):
        return [0.3, 0.4]

    monkeypatch.setattr("app.core.embeddings.embed_text", _embed)
    await check_embedding_dimensions(project_id)
    assert not store._profile_manifest.exists(), "a health read created a manifest"


# ── F9: project evidence stays in its project ─────────────────────────────


async def test_a_promotion_in_one_project_does_not_change_another_projects_prompt(
    tmp_path, monkeypatch
):
    from app.core import agent_identity, prompt_rag
    from app.core.agent_learning import AgentLearning
    from app.core.self_evolution import SelfEvolutionEngine
    from app.models.database import async_session, init_db
    from app.models.project import Project

    monkeypatch.setattr(settings, "runtime_personas_dir", str(tmp_path / "personas"))
    await init_db()
    project_a, project_b = f"pa-{uuid.uuid4().hex[:6]}", f"pb-{uuid.uuid4().hex[:6]}"
    async with async_session() as db:
        db.add_all([Project(id=project_a, name="A"), Project(id=project_b, name="B")])
        learning = AgentLearning(
            agent_id="istara-main",
            project_id=project_a,
            category="workflow_pattern",
            trigger="quarterly close",
            learning="Zorblax the reconciliation export nightly.",
            confidence=90,
            times_applied=5,
            times_successful=5,
        )
        db.add(learning)
        await db.commit()
        learning_id = learning.id

    result = await SelfEvolutionEngine().promote_learning(
        "istara-main", learning_id, project_id=project_a
    )
    assert result.get("success"), result

    query = "zorblax reconciliation export"
    prompt_a = await prompt_rag.compose_dynamic_prompt(
        "istara-main", query, max_tokens=3000, use_embeddings=False, project_id=project_a
    )
    prompt_b = await prompt_rag.compose_dynamic_prompt(
        "istara-main", query, max_tokens=3000, use_embeddings=False, project_id=project_b
    )
    assert "Zorblax" in prompt_a
    assert "Zorblax" not in prompt_b
    full = 100_000  # no compression: this checks what is merged, not what fits
    assert "Zorblax" not in agent_identity.load_agent_identity("istara-main", max_tokens=full)
    assert "Zorblax" not in agent_identity.load_agent_identity(
        "istara-main", max_tokens=full, project_id=project_b
    )
    assert "Zorblax" in agent_identity.load_agent_identity(
        "istara-main", max_tokens=full, project_id=project_a
    )


async def test_skill_description_cache_follows_descriptions_and_the_embedding_space(monkeypatch):
    from app.core.agent import AgentOrchestrator
    from app.skills.registry import load_default_skills, registry

    load_default_skills()
    embedded: list[str] = []
    dims = {"n": 3}

    async def _embed(text, **_kwargs):
        embedded.append(text)
        return [1.0] * dims["n"]

    monkeypatch.setattr("app.core.embeddings.embed_text", _embed)

    async def _no_memory(**kwargs):
        return ""

    monkeypatch.setattr("app.core.reasoning_bank.reasoning_bank.context_for_query", _no_memory)
    orchestrator = AgentOrchestrator()
    AgentOrchestrator._skill_desc_cache.clear()
    task = SimpleNamespace(
        title="Do the thing", description="for the project", project_id="p", agent_id=None
    )
    await orchestrator._semantic_skill_match(task)
    first = len(embedded)

    skill = registry.get("tree-testing")
    monkeypatch.setattr(type(skill), "description", property(lambda self: "A new description."))
    embedded.clear()
    await orchestrator._semantic_skill_match(task)
    assert any("A new description." in text for text in embedded), "stale description served"
    assert len(embedded) < first, "unchanged descriptions stay cached"

    dims["n"] = 5  # the embedder now returns another dimension for the task vector only
    embedded.clear()
    match = await orchestrator._semantic_skill_match(task)
    assert match is None or len(embedded) > 1, "no zip-truncated cosine across two spaces"


# ── Measurement 6: a planted successful-but-wrong run teaches nothing strong ─


class _PlantedWrongSkill:
    """Succeeds, looks well-formed, and is wrong (it contradicts the source it was given)."""

    name = "planted-wrong-skill"
    display_name = "Planted Wrong Skill"
    description = "Deliberately wrong synthesis used by the learning-loop safety harness."

    @property
    def phase(self):
        from app.skills.base import SkillPhase

        return SkillPhase.DEFINE

    @property
    def skill_type(self):
        from app.skills.base import SkillType

        return SkillType.QUALITATIVE

    async def plan(self, skill_input):
        return "plan"

    async def execute(self, skill_input):
        from app.skills.base import SkillOutput

        return SkillOutput(
            success=True,
            summary="Owners love the invoice screen and never chase payments.",
            insights=[{"text": "Invoice chasing is not a problem for owners."}],
            recommendations=[{"text": "Remove invoice reminders."}],
        )

    async def validate_output(self, output):
        return True


async def test_planted_successful_but_wrong_run_teaches_nothing_strong(monkeypatch, tmp_path):
    from sqlalchemy import select

    from app.core.agent import AgentOrchestrator
    from app.core.agent_learning import AgentLearning
    from app.core.agent_skill_tools import rank_skill_candidates
    from app.core.reasoning_bank import FAILURE_OUTCOMES, SUCCESS_OUTCOMES, reasoning_bank
    from app.core.self_evolution import SelfEvolutionEngine
    from app.models.database import async_session, init_db
    from app.models.project import Project
    from app.models.task import Task, TaskStatus
    from app.skills.registry import load_default_skills, registry
    from app.skills.skill_manager import skill_manager

    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    load_default_skills()
    planted = _PlantedWrongSkill()
    monkeypatch.setitem(registry._skills, planted.name, planted)

    async def _structured(**kwargs):
        # The model's own reflection is fooled: it "verifies" the wrong output.
        return SimpleNamespace(
            status="success",
            value={"verified": True, "confidence": 0.95, "reason": "Looks complete."},
        )

    async def _completion(**kwargs):
        return SimpleNamespace(status="success", text="ok")

    monkeypatch.setattr(
        "app.core.agentic.agentic", SimpleNamespace(structured=_structured, completion=_completion)
    )

    async def _no_rag(*args, **kwargs):
        from app.core.rag import RAGContext

        return RAGContext(query="", retrieved=[], context_text="")

    monkeypatch.setattr("app.core.agent_execution.retrieve_context", _no_rag)

    await init_db()
    project_id = f"m6-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Learning-loop safety"))
        task = Task(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title="Synthesize invoices",
            description="Invoice chasing interviews",
            skill_name=planted.name,
            status=TaskStatus.BACKLOG,
            agent_id="istara-main",
        )
        db.add(task)
        await db.commit()
        orchestrator = AgentOrchestrator()
        await orchestrator._execute_task(
            db, await db.get(Task, task.id), await db.get(Project, project_id)
        )

    # ReasoningBank: nothing stored as a success, nothing at strong confidence.
    memories = await reasoning_bank.list_memories(project_id=project_id)
    assert memories, "the run is still recorded as process memory"
    assert not [m for m in memories if m["outcome"] in SUCCESS_OUTCOMES]
    assert all(m["confidence"] < 0.7 for m in memories), memories

    # Memento usage statistics: no success counted from the agent's own check.
    stats = skill_manager.get_usage_stats(planted.name, project_id=project_id)
    assert int(stats.get("successes", 0)) == 0, stats

    # Skill routing: no learned lift for an unrelated query.
    unrelated = SimpleNamespace(
        title="Plan a card sort for navigation labels",
        description="",
        project_id=project_id,
        agent_id="",
        skill_name="",
    )
    assert planted.name not in [c.name for c in await rank_skill_candidates(task=unrelated)]

    # Self-evolution: no promotable learning.
    async with async_session() as db:
        learnings = (
            (await db.execute(select(AgentLearning).where(AgentLearning.project_id == project_id)))
            .scalars()
            .all()
        )
    candidates = await SelfEvolutionEngine().scan_for_promotions(
        "istara-main", project_id=project_id
    )
    assert not candidates, [c["learning"] for c in candidates]
    assert all((learning.times_successful or 0) == 0 for learning in learnings)
    report = {
        "reasoning_bank": [(m["outcome"], m["confidence"]) for m in memories],
        "skill_stats": stats,
        "self_evolution_candidates": len(candidates),
        "failure_memories": sum(1 for m in memories if m["outcome"] in FAILURE_OUTCOMES),
    }
    print("LEARNING-LOOP-SAFETY", json.dumps(report, default=str))
