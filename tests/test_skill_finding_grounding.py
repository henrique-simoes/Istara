"""D-12: skill nuggets are grounded in the raw source they quote, so they can be coded and reported.

The spine's end-to-end proof hands `_store_findings` a `source_document_id` that no real skill
emits. These tests feed nuggets exactly as the interview skill returns them (a quote and the name
of the file it came from) and check that the quote becomes an exact-span evidence unit of that
document and starts a governed coding run, and that anything not verbatim in a raw source stays a
candidate.
"""

from __future__ import annotations

import json
import re
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select


TRANSCRIPT_A = (
    "Interviewer: How do you handle receipts?\n\n"
    "P01: I keep them in the apron pocket until the van,\nthen they go in a shoebox.\n\n"
    "Interviewer: And at month end?\n\n"
    "P01: Month end is a nightmare because the bank export never matches the receipts."
)
TRANSCRIPT_B = (
    "Interviewer: What about invoices?\n\n"
    "P02: Month end is a nightmare because the bank export never matches the receipts.\n\n"
    "P02: I retype every invoice into the spreadsheet by hand."
)


def _doc(name: str, text: str, kind: str = "user_upload"):
    return (SimpleNamespace(id=f"doc-{name}", file_name=name, title=name, file_path=f"/p/{name}",
                            source=kind), text)


def test_locate_quote_ignores_line_wrapping_but_nothing_else():
    from app.services.finding_grounding import locate_quote

    assert locate_quote("in the apron pocket until the van, then they go in a shoebox", TRANSCRIPT_A)
    assert locate_quote("“I keep them in the apron pocket”", TRANSCRIPT_A) is not None
    assert locate_quote("in the apron pockets until the van", TRANSCRIPT_A) is None
    assert locate_quote("shoebox", TRANSCRIPT_A) is None  # too short to attribute


def test_shared_quote_goes_to_the_named_file_or_nowhere():
    from app.services.finding_grounding import ground_quote

    docs = [_doc("p01.md", TRANSCRIPT_A), _doc("p02.md", TRANSCRIPT_B)]
    shared = "Month end is a nightmare because the bank export never matches the receipts."
    assert ground_quote(shared, "p02.md", docs).document_id == "doc-p02.md"
    assert ground_quote(shared, "", docs) is None
    unique = ground_quote("I retype every invoice into the spreadsheet by hand.", "", docs)
    assert unique is not None and unique.document_id == "doc-p02.md"
    assert TRANSCRIPT_B[unique.start:unique.end] == unique.text


class _ThreeCoders:
    """Deterministic coders: every unit gets the same code from three distinct models."""

    def __init__(self):
        self.calls = []

    async def structured(self, **kwargs):  # noqa: ANN003
        if kwargs.get("purpose") == "report.mece":
            return SimpleNamespace(status="success", value={"categories": []})
        model = kwargs["params"].model
        self.calls.append(model)
        units = json.loads(
            re.search(
                r"<evidence_units>\s*(\[.*?\])\s*</evidence_units>",
                kwargs["messages"][-1]["content"],
                re.DOTALL,
            ).group(1)
        )
        return SimpleNamespace(
            value={
                "applications": [
                    {
                        "evidence_unit_id": u["id"],
                        "stable_id": u["stable_id"],
                        "unit_index": u["unit_index"],
                        "codes": ["reconciliation_pain"],
                        "primary_code": "reconciliation_pain",
                        "quote": u["source_text"],
                        "confidence": 0.9,
                        "rationale": "grounded",
                    }
                    for u in units
                ]
            },
            endpoint_id=f"endpoint-{model.rsplit('-', 1)[-1]}",
            served_model=model,
        )

    async def completion(self, **kwargs):  # noqa: ANN003
        return SimpleNamespace(text="summary")


async def _run_skill_output(monkeypatch, nuggets):
    from app.core.agent import AgentOrchestrator
    from app.models.database import async_session, init_db
    from app.models.document import Document, DocumentSource, DocumentStatus
    from app.models.project import Project
    from app.models.research_validity import CodingRun, EvidenceUnit
    from app.models.task import Task, TaskStatus
    from app.services import research_validity_service
    from app.skills.base import SkillOutput

    class Node:
        def __init__(self, i):
            self.node_id = f"node-{i}"
            self.name = self.node_id
            self.source = "test"
            self.provider_type = "test"
            self.endpoint_id = f"endpoint-{i}"
            self.provider_account_handle = f"account-{i}"
            self.is_healthy = True
            self.loaded_models = [f"model-{i}"]
            self.model_capabilities = {}

    async def select_coders(max_coders, *, project_id=None):  # noqa: ANN001
        return [
            research_validity_service.CoderSpec(
                node=n, coder_id=f"model-coder:{n.loaded_models[0]}", model_name=n.loaded_models[0]
            )
            for n in (Node(1), Node(2), Node(3))
        ]

    dispatcher = _ThreeCoders()
    monkeypatch.setattr(research_validity_service, "_select_pi_coders", select_coders)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher)

    await init_db()
    suffix = uuid.uuid4().hex[:8]
    project_id, task_id = f"proj-ground-{suffix}", f"task-ground-{suffix}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Grounding"))
        db.add(Task(id=task_id, project_id=project_id, title="Analyse interviews",
                    skill_name="user-interviews", status=TaskStatus.IN_PROGRESS))
        for name, text in (("p01.md", TRANSCRIPT_A), ("p02.md", TRANSCRIPT_B)):
            db.add(Document(id=f"doc-{name}-{suffix}", project_id=project_id, title=name,
                            file_name=name, status=DocumentStatus.READY,
                            source=DocumentSource.USER_UPLOAD, content_text=text))
        # A model-written artifact containing the same words must never be a grounding target.
        db.add(Document(id=f"doc-artifact-{suffix}", project_id=project_id, title="summary.md",
                        file_name="summary.md", status=DocumentStatus.READY,
                        source=DocumentSource.AGENT_OUTPUT,
                        content_text="Participants said: I invented this sentence for the summary."))
        await db.commit()
        task = await db.get(Task, task_id)
        output = SkillOutput(success=True, summary="s", nuggets=nuggets)
        await AgentOrchestrator()._store_findings(db, project_id, output, task)
        await db.refresh(task)
        units = (
            (await db.execute(select(EvidenceUnit).where(EvidenceUnit.task_id == task_id)))
            .scalars()
            .all()
        )
        runs = (
            (await db.execute(select(CodingRun).where(CodingRun.task_id == task_id)))
            .scalars()
            .all()
        )
    return units, runs, suffix


@pytest.mark.asyncio
async def test_interview_skill_nuggets_become_exact_span_units_and_are_coded(monkeypatch):
    units, runs, suffix = await _run_skill_output(
        monkeypatch,
        [
            {"text": "I keep them in the apron pocket until the van, then they go in a shoebox.",
             "source": "p01.md", "source_location": "", "tags": ["receipts"]},
            {"text": "Month end is a nightmare because the bank export never matches the receipts.",
             "source": "p02.md", "source_location": "", "tags": ["reconciliation"]},
        ],
    )
    spans = [u for u in units if u.unit_type == "source_span"]
    assert len(spans) == 2
    assert {u.source_document_id for u in spans} == {f"doc-p01.md-{suffix}", f"doc-p02.md-{suffix}"}
    assert all("#chars=" in u.source_location for u in spans)
    assert len(runs) == 1


@pytest.mark.asyncio
async def test_paraphrase_and_artifact_quotes_stay_candidates(monkeypatch):
    units, runs, _ = await _run_skill_output(
        monkeypatch,
        [
            {"text": "Receipts live in an apron pocket and then a shoebox.", "source": "p01.md"},
            {"text": "I invented this sentence for the summary.", "source": "summary.md"},
        ],
    )
    assert units and all(u.unit_type == "candidate_atom" for u in units)
    assert all(u.source_document_id is None for u in units)
    assert runs == []
