"""Regression coverage for bounded Python-to-worker protocol frames (H-1/H-2)."""

from __future__ import annotations

import pytest

from app.core.pi_runtime.supervisor import PiRuntimeSupervisor

from .harness import faux_endpoint, final_text, requires_node, tool_call


@requires_node
@pytest.mark.asyncio
async def test_megabyte_tool_result_round_trips_without_poisoning_the_worker():
    """A large authority result is chunked, reassembled, and leaves no dead worker."""
    supervisor = PiRuntimeSupervisor()
    payload = "x" * (1024 * 1024)

    async def authority(name: str, arguments: dict):
        assert name == "read_large_evidence"
        return {"ok": True, "result": {"evidence": payload}}

    try:
        await supervisor.ensure_started()
        await supervisor.open_session(
            "frame-limit", system_prompt="test", history=[], revision="r1",
            catalog=[{"name": "read_large_evidence", "description": "test", "parameters": {}}],
        )
        endpoint = faux_endpoint([tool_call("read_large_evidence", {}), final_text("complete")])
        await supervisor.bind_provider(
            "frame-limit",
            {
                "endpoint_id": endpoint.endpoint_id,
                "provider_kind": endpoint.provider_kind,
                "base_url": endpoint.base_url,
                "model": endpoint.model,
                "api_key": endpoint.api_key,
                "timeout_ms": endpoint.timeout_ms,
                "max_retries": endpoint.max_retries,
                "faux_responses": list(endpoint.faux_responses or ()),
            },
        )
        frames = [frame async for frame in supervisor.run_turn("frame-limit", "go", authority)]
        assert any(frame["type"] == "tool.call" for frame in frames)
        assert any(frame["type"] == "run.completed" for frame in frames)
    finally:
        await supervisor.shutdown()
