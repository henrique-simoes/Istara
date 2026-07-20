"""Shared harness for the production Pi scenario matrix.

Every scenario drives the *real* supervised pi-agent-core worker (a spawned Node
child) through the production ``PiExecutionService`` seams and real Istara
services against a test-owned DB. A ``faux`` provider supplies deterministic
scripted completions inside the real Agent loop — no network, no ComputeRegistry,
no orphan process. (The real provider HTTP stack is proven separately in
``test_engine_http_provider.py`` and ``test_scenario_channel.py``.)
"""

from __future__ import annotations

import shutil

import pytest

from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
from app.core.pi_runtime.engine import PiExecutionService
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor

requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="node runtime not available"
)


def faux_endpoint(responses, *, endpoint_id: str = "pi-faux") -> ResolvedPiEndpoint:
    """A test-only endpoint that scripts the worker's Agent deterministically."""
    return ResolvedPiEndpoint(
        endpoint_id=endpoint_id,
        provider_kind="faux",
        base_url="",
        model="stub-model",
        api_key="faux",
        timeout_ms=30000,
        max_retries=0,
        faux_responses=tuple(responses),
    )


class FixedResolver:
    """Resolver that always returns one endpoint (used to inject a faux/loopback
    endpoint without any Keychain/network dependency)."""

    def __init__(self, endpoint: ResolvedPiEndpoint) -> None:
        self._endpoint = endpoint

    def resolve(self, endpoint_id: str, *, model=None) -> ResolvedPiEndpoint:
        return self._endpoint


def faux_service(responses, supervisor: PiRuntimeSupervisor) -> PiExecutionService:
    return PiExecutionService(resolver=FixedResolver(faux_endpoint(responses)), supervisor=supervisor)


def tool_call(name: str, arguments: dict) -> dict:
    return {"tool_calls": [{"name": name, "arguments": arguments}], "stop_reason": "toolUse"}


def final_text(text: str) -> dict:
    return {"text": text, "stop_reason": "stop"}


def error_after_partial(text: str) -> dict:
    """A faux response that streams ``text`` then settles on a failed terminal.

    The worker emits ``assistant.delta`` frames for ``text`` and then ``run.failed``
    (``_settleRun`` sees ``stopReason == "error"``), so the collected turn has a
    non-empty ``text`` with ``status == "error"`` — the "error after partial
    output" case governed seams must fail closed on."""
    return {"text": text, "stop_reason": "error"}
