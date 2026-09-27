"""D-19: governed coding fits the coders that serve it, the owner's local model included.

A coding run sent every evidence unit (up to 200) to each coder in one prompt, each unit as its full
database record: about 114,000 input and 40,000-55,000 output tokens per coder on the Harbor study.
A local model's context cannot hold that, so a three-model run with the local coder failed and the
task could never pass the reliability gate. Units now go to coders in batches that fit a small
context, as the fields a coder needs, and a coder must still code every unit of the run.
"""

from __future__ import annotations

import json
import re
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

UNITS = 45
SMALL_CONTEXT_UNITS = 20  # what a small local model can take in one prompt
THEMES = ("invoice_chasing", "receipt_capture", "payroll_cash_timing")


class _SmallContextCoders:
    """Three coders; each refuses a prompt carrying more units than a small context holds."""

    def __init__(self):
        self.unit_counts: list[int] = []
        self.unit_keys: set[str] = set()

    async def structured(self, **kwargs):  # noqa: ANN003
        model = kwargs["params"].model
        units = json.loads(
            re.search(
                r"<evidence_units>\s*(\[.*?\])\s*</evidence_units>",
                kwargs["messages"][-1]["content"],
                re.DOTALL,
            ).group(1)
        )
        self.unit_counts.append(len(units))
        for unit in units:
            self.unit_keys.update(unit)
        if len(units) > SMALL_CONTEXT_UNITS:
            raise RuntimeError("context length exceeded")
        return SimpleNamespace(
            value={
                "applications": [
                    {
                        "evidence_unit_id": u["id"],
                        "stable_id": u["stable_id"],
                        "unit_index": u["unit_index"],
                        "codes": [THEMES[u["unit_index"] % 3]],
                        "primary_code": THEMES[u["unit_index"] % 3],
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


@pytest.mark.asyncio
async def test_a_large_run_is_coded_in_batches_a_small_model_can_hold(monkeypatch):
    from app.models.database import async_session, init_db
    from app.models.project import Project
    from app.models.research_validity import CodingRun, EvidenceUnit
    from app.services import research_validity_service

    class Node:
        def __init__(self, i):
            self.node_id = self.name = f"node-{i}"
            self.source = self.provider_type = "test"
            self.endpoint_id = f"endpoint-{i}"
            self.provider_account_handle = f"account-{i}"
            self.is_healthy = True
            self.loaded_models = [f"model-{i}"]
            self.model_capabilities = {}

    async def select_coders(max_coders, *, project_id=None, **_kwargs):  # noqa: ANN001
        return [
            research_validity_service.CoderSpec(
                node=n, coder_id=f"model-coder:{n.loaded_models[0]}", model_name=n.loaded_models[0]
            )
            for n in (Node(1), Node(2), Node(3))
        ]

    coders = _SmallContextCoders()
    monkeypatch.setattr(research_validity_service, "_select_pi_coders", select_coders)
    monkeypatch.setattr("app.core.agentic.agentic", coders)

    await init_db()
    project_id = f"proj-batch-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Batches"))
        ids = []
        for i in range(UNITS):
            unit_id = str(uuid.uuid4())
            ids.append(unit_id)
            db.add(
                EvidenceUnit(
                    id=unit_id,
                    project_id=project_id,
                    source_id="doc",
                    stable_id=f"doc#EU-{i:04d}",
                    unit_index=i,
                    unit_type="source_span",
                    source_type="interview_transcript",
                    source_text=f"I chase invoice {i} every morning before the shop opens.",
                    metadata_json=json.dumps({"segmenter": "x" * 400}),
                )
            )
        await db.commit()
        run = await research_validity_service.run_independent_coding_run(
            db, project_id=project_id, evidence_unit_ids=ids, limit=UNITS
        )
        stored = (await db.execute(select(CodingRun).where(CodingRun.id == run["id"]))).scalar_one()

    assert stored.rater_count == 3
    assert stored.kappa == 1.0 and stored.promotion_status == "accepted"
    assert max(coders.unit_counts) <= SMALL_CONTEXT_UNITS
    assert sum(coders.unit_counts) == 3 * UNITS
    # A coder sees what it needs to code a unit, not the database record around it.
    assert {"id", "stable_id", "unit_index", "source_text"} <= coders.unit_keys
    assert not coders.unit_keys & {"metadata", "project_id", "created_at", "task_id"}
