"""Shared harness for the production Pi scenario matrix.

Every scenario drives the *real* supervised pi-agent-core worker (a spawned Node
child) through the production ``PiExecutionService`` seams and real Istara
services against a test-owned DB. A ``faux`` provider supplies deterministic
scripted completions inside the real Agent loop — no network, no ComputeRegistry,
no orphan process. (The real provider HTTP stack is proven separately in
``test_engine_http_provider.py`` and ``test_scenario_channel.py``.)
"""

from __future__ import annotations

import os
import shutil

import pytest

from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
from app.core.pi_runtime.engine import PiExecutionService
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor

_NODE_AVAILABLE = shutil.which("node") is not None

if not _NODE_AVAILABLE and os.environ.get("PI_REQUIRE_NODE") == "1":
    # CI sets PI_REQUIRE_NODE=1 to guarantee the real node worker is exercised.
    # A missing runtime then is a harness misconfiguration, not an optional
    # skip — fail loudly at collection instead of silently green-washing.
    pytest.fail(
        "PI_REQUIRE_NODE=1 is set but the node runtime was not found on PATH; "
        "tests/pi_production scenario tests must run the real node worker.",
        pytrace=False,
    )

requires_node = pytest.mark.skipif(
    not _NODE_AVAILABLE, reason="node runtime not available"
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
        faux_responses=tuple(response for response in responses if "faux_forced_tool_calls" not in response),
        faux_forced_tool_calls=tuple(
            call for response in responses for call in response.get("faux_forced_tool_calls", [])
        ),
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


def compromised_tool_call(name: str, arguments: dict) -> dict:
    """Inject a faux-worker raw call to exercise Python authority rejection."""
    return {"faux_forced_tool_calls": [{"name": name, "arguments": arguments}]}


def final_text(text: str) -> dict:
    return {"text": text, "stop_reason": "stop"}


def error_after_partial(text: str) -> dict:
    """A faux response that streams ``text`` then settles on a failed terminal.

    The worker emits ``assistant.delta`` frames for ``text`` and then ``run.failed``
    (``_settleRun`` sees ``stopReason == "error"``), so the collected turn has a
    non-empty ``text`` with ``status == "error"`` — the "error after partial
    output" case governed seams must fail closed on."""
    return {"text": text, "stop_reason": "error"}
