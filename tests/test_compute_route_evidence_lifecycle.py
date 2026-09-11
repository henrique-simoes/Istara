"""Regression coverage for owned async donor telemetry."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.core import compute_route_evidence


@pytest.mark.asyncio
async def test_drain_compute_telemetry_waits_for_scheduled_write(monkeypatch):
    started = asyncio.Event()
    release = asyncio.Event()

    class Recorder:
        async def record_research_validity_event(self, **_kwargs):
            started.set()
            await release.wait()

    monkeypatch.setattr(
        compute_route_evidence.importlib,
        "import_module",
        lambda _name: SimpleNamespace(telemetry_recorder=Recorder()),
    )
    node = SimpleNamespace(node_id="donor", selected_request_count=1)
    compute_route_evidence.schedule_compute_telemetry_event(
        node, operation="donor.selected", project_id="project", model="shared-model"
    )
    await started.wait()
    draining = asyncio.create_task(compute_route_evidence.drain_compute_telemetry())
    await asyncio.sleep(0)
    assert not draining.done()
    release.set()
    await draining
    assert not compute_route_evidence._telemetry_tasks
