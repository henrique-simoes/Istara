"""Regression test for the long-horizon token fix (task B0-3, acceptance A3).

The prior code counted one "token" per streamed SSE content chunk
(``long_horizon_runner.py`` old ``total_tokens += 1``). This test pins the corrected
behaviour: token accounting comes from provider-reported usage, never from a chunk count.
It FAILS against the old chunk-count implementation, as A3 requires.
"""

from __future__ import annotations

import subprocess

import pytest

pytestmark = pytest.mark.benchmark

# The runner module imports httpx at top level; skip cleanly if it is unavailable.
httpx = pytest.importorskip("httpx")

from tests.benchmarks import long_horizon_runner  # noqa: E402
from tests.benchmarks.long_horizon_runner import extract_total_tokens  # noqa: E402


def test_content_chunks_are_not_counted_as_tokens():
    # Three content chunks. Old behaviour: total_tokens == 3. Correct behaviour: None
    # (the stream carried no provider usage), so this asserts the bug is gone.
    events = [
        {"type": "chunk", "content": "Hello "},
        {"type": "chunk", "content": "world"},
        {"content": "!"},
    ]
    assert extract_total_tokens(events) is None


def test_provider_reported_usage_is_read():
    events = [
        {"type": "chunk", "content": "Hi"},
        {
            "type": "usage",
            "usage": {"input_tokens": 128, "output_tokens": 64, "total_tokens": 192},
        },
    ]
    assert extract_total_tokens(events) == 192


def test_camelcase_usage_is_read():
    events = [{"usage": {"totalTokens": 55}}]
    assert extract_total_tokens(events) == 55


def test_empty_stream_reports_no_tokens():
    assert extract_total_tokens([]) is None


def test_restart_resume_oracle_refuses_host_execution(monkeypatch):
    monkeypatch.setenv("ISTARA_LONG_HORIZON_REQUIRE_RESTART_RESUME", "1")
    monkeypatch.setenv("ISTARA_LONG_HORIZON_BACKEND_CONTAINER", "a" * 12)
    monkeypatch.delenv("ISTARA_BENCHMARK_DOCKER_RUNNER", raising=False)

    with pytest.raises(
        long_horizon_runner.BenchmarkFailure,
        match="outside the disposable Docker runner",
    ):
        long_horizon_runner._restart_disposable_backend()


def test_restart_resume_oracle_restarts_only_an_opaque_backend_id(monkeypatch):
    container_id = "a" * 12
    calls: list[list[str]] = []
    responses = iter(
        [
            subprocess.CompletedProcess([], 0, "2026-08-28T00:00:00Z\n", ""),
            subprocess.CompletedProcess([], 0, f"{container_id}\n", ""),
            subprocess.CompletedProcess([], 0, "2026-08-28T00:00:11Z\n", ""),
        ]
    )
    monkeypatch.setenv("ISTARA_LONG_HORIZON_REQUIRE_RESTART_RESUME", "1")
    monkeypatch.setenv("ISTARA_LONG_HORIZON_BACKEND_CONTAINER", container_id)
    monkeypatch.setenv("ISTARA_BENCHMARK_DOCKER_RUNNER", "1")
    monkeypatch.setattr(long_horizon_runner.Path, "is_file", lambda _: True)
    monkeypatch.setattr(long_horizon_runner.Path, "is_socket", lambda _: True)

    def fake_run(command, **_kwargs):
        calls.append(command)
        return next(responses)

    monkeypatch.setattr(long_horizon_runner.subprocess, "run", fake_run)

    assert long_horizon_runner._restart_disposable_backend() == (
        "2026-08-28T00:00:00Z",
        "2026-08-28T00:00:11Z",
    )
    assert calls == [
        ["docker", "inspect", "--format", "{{.State.StartedAt}}", container_id],
        ["docker", "restart", "--time", "10", container_id],
        ["docker", "inspect", "--format", "{{.State.StartedAt}}", container_id],
    ]


def test_restart_resume_oracle_rejects_non_container_targets(monkeypatch):
    monkeypatch.setenv("ISTARA_LONG_HORIZON_REQUIRE_RESTART_RESUME", "1")
    monkeypatch.setenv("ISTARA_LONG_HORIZON_BACKEND_CONTAINER", "backend; rm -rf /")

    with pytest.raises(
        long_horizon_runner.BenchmarkFailure, match="opaque Docker backend container id"
    ):
        long_horizon_runner._restart_disposable_backend()


def test_tool_call_oracle_counts_canonical_events_only():
    events = [
        {"type": "tool_call", "tool": "create_task"},
        {"type": "chunk", "content": "[Tool: create_task]"},
        {"type": "tool_call", "tool": "create_task"},
    ]
    assert long_horizon_runner._tool_call_count(events) == 2


def test_done_oracle_requires_executed_tools_to_be_reported():
    events = [
        {"type": "tool_call", "tool": "create_task", "tool_call_id": "call-1"},
        {
            "type": "tool_result",
            "tool": "create_task",
            "tool_call_id": "call-1",
            "ok": True,
        },
        {"type": "chunk", "content": "The task was created."},
        {"type": "done", "message_id": "msg-1", "tools_used": ["create_task"]},
    ]
    done = long_horizon_runner._require_done_tool_contract(
        events, "first turn", require_tool_result=True
    )
    assert done["message_id"] == "msg-1"


def test_done_oracle_rejects_tool_calls_missing_from_terminal_event():
    events = [
        {"type": "tool_call", "tool": "create_task", "tool_call_id": "call-1"},
        {
            "type": "tool_result",
            "tool": "create_task",
            "tool_call_id": "call-1",
            "ok": True,
        },
        {"type": "chunk", "content": "The task was created."},
        {"type": "done", "message_id": "msg-1", "tools_used": []},
    ]
    with pytest.raises(
        long_horizon_runner.BenchmarkFailure, match="does not report executed tool"
    ):
        long_horizon_runner._require_done_tool_contract(
            events, "first turn", require_tool_result=True
        )


def test_done_oracle_rejects_missing_tool_execution_receipt():
    events = [
        {"type": "tool_call", "tool": "create_task", "tool_call_id": "call-1"},
        {"type": "chunk", "content": "The task was created."},
        {"type": "done", "message_id": "msg-1", "tools_used": ["create_task"]},
    ]
    with pytest.raises(
        long_horizon_runner.BenchmarkFailure, match="no matching tool-result receipt"
    ):
        long_horizon_runner._require_done_tool_contract(
            events, "first turn", require_tool_result=True
        )


def test_done_oracle_rejects_tool_receipt_without_a_later_model_response():
    events = [
        {"type": "tool_call", "tool": "create_task", "tool_call_id": "call-1"},
        {
            "type": "tool_result",
            "tool": "create_task",
            "tool_call_id": "call-1",
            "ok": True,
        },
        {"type": "done", "message_id": "msg-1", "tools_used": ["create_task"]},
    ]
    with pytest.raises(
        long_horizon_runner.BenchmarkFailure,
        match="no model response after tool-result",
    ):
        long_horizon_runner._require_done_tool_contract(
            events, "first turn", require_tool_result=True
        )


def test_task_queue_oracle_requires_project_scoped_persisted_task():
    payload = [
        {"id": "task-1", "project_id": "project-1", "title": "Thematic Analysis"}
    ]
    tasks = long_horizon_runner._require_persisted_tasks(payload, "project-1")
    assert tasks[0]["id"] == "task-1"


def test_task_queue_oracle_rejects_empty_queue():
    with pytest.raises(
        long_horizon_runner.BenchmarkFailure, match="no persisted tasks"
    ):
        long_horizon_runner._require_persisted_tasks([], "project-1")


def test_usage_oracle_requires_two_recorded_turns_and_engine():
    session_id = "session-1"
    payload = {
        "row_count": 2,
        "turns": 2,
        "total_tokens": 200,
        "estimated": False,
        "rows": [
            {
                "id": "row-1",
                "session_id": session_id,
                "purpose": "chat_turn",
                "engine": "pi",
            },
            {
                "id": "row-2",
                "session_id": session_id,
                "purpose": "chat_turn",
                "engine": "pi",
            },
        ],
        "latest": {"engine": "pi", "total_tokens": 100},
    }
    usage = long_horizon_runner._require_usage_ledger(
        payload, expected_engine="pi", expected_session_id=session_id
    )
    assert usage["row_count"] == 2


def test_usage_oracle_can_require_successful_task_linked_route_receipts():
    session_id = "session-1"
    task_id = "task-1"
    payload = {
        "row_count": 2,
        "turns": 2,
        "total_tokens": 200,
        "rows": [
            {
                "id": "row-1",
                "session_id": session_id,
                "purpose": "chat_turn",
                "engine": "pi",
                "model": "model-a",
                "endpoint_id": "endpoint-a",
                "outcome": "success",
                "task_id": task_id,
            },
            {
                "id": "row-2",
                "session_id": session_id,
                "purpose": "chat_turn",
                "engine": "pi",
                "model": "model-a",
                "endpoint_id": "endpoint-a",
                "outcome": "success",
                "task_id": task_id,
            },
        ],
        "latest": {"engine": "pi"},
    }
    usage = long_horizon_runner._require_usage_ledger(
        payload,
        expected_engine="pi",
        expected_session_id=session_id,
        expected_task_id=task_id,
        require_route_provenance=True,
    )
    assert usage["row_count"] == 2


def test_usage_oracle_rejects_duplicate_or_unprovenanced_receipts():
    session_id = "session-1"
    payload = {
        "row_count": 2,
        "turns": 2,
        "total_tokens": 200,
        "rows": [
            {
                "id": "same-row",
                "session_id": session_id,
                "purpose": "chat_turn",
                "engine": "pi",
                "model": "model-a",
                "endpoint_id": "endpoint-a",
                "outcome": "success",
                "task_id": "task-1",
            },
            {
                "id": "same-row",
                "session_id": session_id,
                "purpose": "chat_turn",
                "engine": "pi",
                "model": "model-b",
                "endpoint_id": "endpoint-b",
                "outcome": "success",
                "task_id": "task-1",
            },
        ],
        "latest": {"engine": "pi"},
    }
    with pytest.raises(long_horizon_runner.BenchmarkFailure, match="unique receipt"):
        long_horizon_runner._require_usage_ledger(
            payload,
            expected_engine="pi",
            expected_session_id=session_id,
            expected_task_id="task-1",
            require_route_provenance=True,
        )


def test_usage_oracle_rejects_task_mismatch_and_failed_turn():
    session_id = "session-1"
    payload = {
        "row_count": 2,
        "turns": 2,
        "total_tokens": 200,
        "rows": [
            {
                "id": "row-1",
                "session_id": session_id,
                "purpose": "chat_turn",
                "engine": "pi",
                "model": "model-a",
                "endpoint_id": "endpoint-a",
                "outcome": "success",
                "task_id": "task-1",
            },
            {
                "id": "row-2",
                "session_id": session_id,
                "purpose": "chat_turn",
                "engine": "pi",
                "model": "model-a",
                "endpoint_id": "endpoint-a",
                "outcome": "error",
                "task_id": "task-2",
            },
        ],
        "latest": {"engine": "pi"},
    }
    with pytest.raises(
        long_horizon_runner.BenchmarkFailure, match="task id|successful"
    ):
        long_horizon_runner._require_usage_ledger(
            payload,
            expected_engine="pi",
            expected_session_id=session_id,
            expected_task_id="task-1",
            require_route_provenance=True,
        )


def test_usage_oracle_rejects_missing_rows():
    with pytest.raises(long_horizon_runner.BenchmarkFailure, match="fewer than 2"):
        long_horizon_runner._require_usage_ledger(
            {"row_count": 1, "turns": 1, "latest": {"engine": "pi"}},
            expected_engine="pi",
            expected_session_id="session-1",
        )


def test_usage_oracle_rejects_mixed_chat_engines():
    session_id = "session-1"
    payload = {
        "row_count": 2,
        "turns": 2,
        "total_tokens": 200,
        "rows": [
            {
                "id": "row-1",
                "session_id": session_id,
                "purpose": "chat_turn",
                "engine": "pi",
            },
            {
                "id": "row-2",
                "session_id": session_id,
                "purpose": "chat_turn",
                "engine": "legacy",
            },
        ],
        "latest": {"engine": "legacy"},
    }
    with pytest.raises(long_horizon_runner.BenchmarkFailure, match="do not all match"):
        long_horizon_runner._require_usage_ledger(
            payload, expected_engine="pi", expected_session_id=session_id
        )


def test_usage_oracle_rejects_cross_session_chat_rows():
    payload = {
        "row_count": 2,
        "turns": 2,
        "total_tokens": 200,
        "rows": [
            {
                "id": "row-1",
                "session_id": "session-1",
                "purpose": "chat_turn",
                "engine": "pi",
            },
            {
                "id": "row-2",
                "session_id": "session-2",
                "purpose": "chat_turn",
                "engine": "pi",
            },
        ],
        "latest": {"engine": "pi"},
    }
    with pytest.raises(long_horizon_runner.BenchmarkFailure, match="session id"):
        long_horizon_runner._require_usage_ledger(
            payload, expected_engine="pi", expected_session_id="session-1"
        )


def test_usage_oracle_requires_explicit_session_id():
    payload = {
        "row_count": 2,
        "turns": 2,
        "total_tokens": 200,
        "rows": [
            {
                "id": "row-1",
                "session_id": "session-1",
                "purpose": "chat_turn",
                "engine": "pi",
            },
            {
                "id": "row-2",
                "session_id": "session-1",
                "purpose": "chat_turn",
                "engine": "pi",
            },
        ],
        "latest": {"engine": "pi"},
    }
    with pytest.raises(long_horizon_runner.BenchmarkFailure, match="session id"):
        long_horizon_runner._require_usage_ledger(payload, expected_engine="pi")


def test_engine_oracle_rejects_unset_or_unsupported(monkeypatch):
    monkeypatch.setattr(long_horizon_runner, "ENGINE", None)
    with pytest.raises(
        long_horizon_runner.BenchmarkFailure,
        match="requires ISTARA_LONG_HORIZON_ENGINE",
    ):
        long_horizon_runner._require_explicit_engine()
    monkeypatch.setattr(long_horizon_runner, "ENGINE", "unknown")
    with pytest.raises(long_horizon_runner.BenchmarkFailure, match="legacy or pi"):
        long_horizon_runner._require_explicit_engine()


def test_history_oracle_requires_two_complete_turns():
    first = "first prompt"
    second = "second prompt"
    history = [
        {"role": "user", "content": first},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": second},
        {"role": "assistant", "content": "second answer"},
    ]
    long_horizon_runner._require_history_continuity(history, first, second)


def test_history_oracle_rejects_missing_assistant_output():
    with pytest.raises(
        long_horizon_runner.BenchmarkFailure, match="no assistant content"
    ):
        long_horizon_runner._require_history_continuity(
            [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": ""},
                {"role": "user", "content": "second"},
                {"role": "assistant", "content": "answer"},
            ],
            "first",
            "second",
        )


@pytest.mark.asyncio
async def test_sse_oracle_requires_terminal_done_message_id():
    response = httpx.Response(
        200,
        content=b'data: {"type":"chunk","content":"partial"}' + b"\n\n",
    )
    with pytest.raises(
        long_horizon_runner.BenchmarkFailure,
        match="without a persisted assistant message",
    ):
        await long_horizon_runner._consume_chat_stream(response, "test turn")


@pytest.mark.asyncio
async def test_main_returns_nonzero_for_benchmark_failure(monkeypatch):
    async def fail():
        raise long_horizon_runner.BenchmarkFailure("synthetic failure")

    monkeypatch.setattr(long_horizon_runner, "_run_benchmark", fail)
    assert await long_horizon_runner.main() == 1
